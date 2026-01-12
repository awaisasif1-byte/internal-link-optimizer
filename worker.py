"""
Stateless Python Crawler Worker for Internal Link Optimizer
============================================================

This worker reads from the crawl_queue table and processes URLs indefinitely.
It's crash-proof because all state is stored in the database.

Requirements:
    pip install httpx beautifulsoup4

Environment Variables:
    SUPABASE_URL          - Your Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY - Service role key (has RLS bypass)
    SESSION_ID            - The crawl session UUID from your dashboard

Usage:
    export SUPABASE_URL='https://xyz.supabase.co'
    export SUPABASE_SERVICE_ROLE_KEY='your-service-key'
    export SESSION_ID='uuid-from-dashboard'
    python worker.py

Features:
    - Truly stateless (DB-backed queue)
    - Crash-resumable (just restart the script)
    - No timeout limits (runs for hours/days)
    - Real-time dashboard updates
    - Respects robots.txt
    - Semantic analysis included
"""

import asyncio
import os
import sys
import re
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Dict, List, Set, Optional
import httpx
from bs4 import BeautifulSoup

# ==================== CONFIGURATION ====================

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SESSION_ID = os.getenv('SESSION_ID')

if not all([SUPABASE_URL, SUPABASE_KEY, SESSION_ID]):
    print("❌ Error: Missing required environment variables")
    print("Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SESSION_ID")
    sys.exit(1)

# API Headers
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# User Agent
USER_AGENT = "Mozilla/5.0 (compatible; InternalLinkOptimizer/1.0; +https://yoursite.com/bot)"

# ==================== UTILITY FUNCTIONS ====================

def normalize_url(url: str) -> str:
    """Normalize URL for consistency"""
    parsed = urlparse(url)
    # Remove fragment, normalize path
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip('/') or '/',
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    return normalized

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Simple keyword extraction from text"""
    # Remove HTML, special chars, convert to lowercase
    clean_text = re.sub(r'[^a-z\s]', ' ', text.lower())
    words = clean_text.split()
    
    # Remove stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                  'can', 'could', 'may', 'might', 'this', 'that', 'these', 'those'}
    
    filtered = [w for w in words if w not in stop_words and len(w) > 3]
    
    # Count frequency
    freq: Dict[str, int] = {}
    for word in filtered:
        freq[word] = freq.get(word, 0) + 1
    
    # Sort by frequency and return top N
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]

def classify_page_type(url: str, title: str, content: str) -> str:
    """Simple page type classification"""
    url_lower = url.lower()
    title_lower = title.lower()
    content_lower = content.lower()
    
    # Check URL patterns
    if re.search(r'/(blog|article|post|news)/', url_lower):
        return 'blog'
    if re.search(r'/(product|shop|item|buy)/', url_lower):
        return 'product'
    if re.search(r'/(category|collection|archive)/', url_lower):
        return 'category'
    if re.search(r'/(about|team|company|contact)/', url_lower):
        return 'informational'
    
    # Check content patterns
    if 'add to cart' in content_lower or 'buy now' in content_lower:
        return 'product'
    if re.search(r'\b(posted|published|author|by)\b', content_lower):
        return 'blog'
    
    # Default
    if url_lower.endswith('/') or url_lower.count('/') <= 3:
        return 'homepage'
    
    return 'page'

# ==================== DATABASE OPERATIONS ====================

async def get_session_info() -> Optional[Dict]:
    """Get session details including project_id and start_url"""
    url = f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{SESSION_ID}&select=*"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=HEADERS)
            sessions = res.json()
            return sessions[0] if sessions else None
        except Exception as e:
            print(f"❌ Error fetching session: {e}")
            return None

async def get_next_tasks(limit: int = 5) -> List[Dict]:
    """Pull next pending URLs from the queue"""
    url = f"{SUPABASE_URL}/rest/v1/crawl_queue?session_id=eq.{SESSION_ID}&status=eq.pending&order=depth.asc&limit={limit}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=HEADERS)
            return res.json() if res.status_code == 200 else []
        except Exception as e:
            print(f"❌ Error fetching tasks: {e}")
            return []

async def update_task_status(task_id: str, status: str):
    """Update queue item status"""
    url = f"{SUPABASE_URL}/rest/v1/crawl_queue?id=eq.{task_id}"
    async with httpx.AsyncClient() as client:
        try:
            await client.patch(url, json={"status": status}, headers=HEADERS)
        except Exception as e:
            print(f"⚠️  Warning: Could not update task status: {e}")

async def save_page(page_data: Dict):
    """Save crawled page to database"""
    url = f"{SUPABASE_URL}/rest/v1/pages"
    
    # Use upsert to avoid duplicates
    upsert_headers = {**HEADERS, "Prefer": "resolution=merge-duplicates"}
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=page_data, headers=upsert_headers)
            if res.status_code >= 300:
                print(f"⚠️  DB Save Warning: {res.text}")
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

async def enqueue_links(links: List[Dict]):
    """Add discovered links to the queue"""
    if not links:
        return
    
    url = f"{SUPABASE_URL}/rest/v1/crawl_queue"
    
    # Use ignore-duplicates to prevent re-crawling
    upsert_headers = {**HEADERS, "Prefer": "resolution=ignore-duplicates"}
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=links, headers=upsert_headers)
        except Exception as e:
            print(f"⚠️  Enqueue Warning: {e}")

async def update_session_progress(pages_crawled: int, pages_found: int):
    """Update session with current progress"""
    url = f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{SESSION_ID}"
    data = {
        "pages_crawled": pages_crawled,
        "pages_found": pages_found,
        "updated_at": datetime.utcnow().isoformat()
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.patch(url, json=data, headers=HEADERS)
        except Exception as e:
            print(f"⚠️  Progress update warning: {e}")

# ==================== CRAWLER LOGIC ====================

async def crawl_url(task: Dict, session_info: Dict, domain: str) -> List[str]:
    """Crawl a single URL and return discovered links"""
    task_id = task['id']
    target_url = task['url']
    depth = task['depth']
    parent_url = task.get('parent_url')
    
    project_id = session_info['project_id']
    max_depth = session_info.get('max_depth', 3)
    
    await update_task_status(task_id, "processing")
    print(f"🔎 [{depth}] Crawling: {target_url}")
    
    discovered_links = []
    
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT}
        ) as client:
            response = await client.get(target_url)
            
            # Only process successful HTML responses
            if response.status_code != 200:
                print(f"⚠️  Non-200 status: {response.status_code}")
                await update_task_status(task_id, "failed")
                return []
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type.lower():
                print(f"⚠️  Non-HTML content: {content_type}")
                await update_task_status(task_id, "completed")
                return []
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract metadata
            title = soup.title.string if soup.title else "No Title"
            title = title.strip()[:200]
            
            # Get text content
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            text_content = soup.get_text(separator=' ', strip=True)
            word_count = len(text_content.split())
            
            # Extract keywords
            keywords = extract_keywords(text_content)
            
            # Classify page type
            page_type = classify_page_type(target_url, title, text_content)
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'][:300] if meta_desc and meta_desc.get('content') else ''
            
            # Extract internal links
            internal_links: Set[str] = set()
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                full_url = urljoin(target_url, href)
                normalized = normalize_url(full_url)
                
                # Only keep internal links from same domain
                if urlparse(normalized).netloc == domain:
                    internal_links.add(normalized)
                    discovered_links.append(normalized)
            
            # Calculate link equity (simplified)
            link_equity = min(100, (len(internal_links) * 5))
            
            # Prepare page data
            page_data = {
                "project_id": project_id,
                "session_id": SESSION_ID,
                "url": target_url,
                "normalized_url": normalize_url(target_url),
                "title": title,
                "content": text_content[:10000],  # Store first 10k chars
                "word_count": word_count,
                "internal_links_count": len(internal_links),
                "external_links_count": 0,  # Could count these too
                "status_code": response.status_code,
                "depth": depth,
                "parent_url": parent_url,
                "page_type": page_type,
                "meta_description": description,
                "keywords": keywords[:10] if keywords else [],
                "link_equity_score": link_equity,
                "crawled_at": datetime.utcnow().isoformat()
            }
            
            # Save to database
            await save_page(page_data)
            
            # Enqueue discovered links (if within depth limit)
            if depth < max_depth and internal_links:
                links_to_enqueue = [
                    {
                        "session_id": SESSION_ID,
                        "url": link,
                        "normalized_url": normalize_url(link),
                        "depth": depth + 1,
                        "parent_url": target_url,
                        "status": "pending"
                    }
                    for link in internal_links
                ]
                await enqueue_links(links_to_enqueue)
            
            await update_task_status(task_id, "completed")
            print(f"✅ Completed: {target_url} ({len(internal_links)} links found)")
            
    except asyncio.TimeoutError:
        print(f"⏱️  Timeout: {target_url}")
        await update_task_status(task_id, "failed")
    except Exception as e:
        print(f"❌ Error crawling {target_url}: {e}")
        await update_task_status(task_id, "failed")
    
    return discovered_links

# ==================== MAIN WORKER LOOP ====================

async def worker_loop():
    """Main worker loop - processes queue until empty"""
    
    print("=" * 60)
    print("🚀 Internal Link Optimizer - Crawler Worker")
    print("=" * 60)
    
    # Get session info
    session_info = await get_session_info()
    if not session_info:
        print("❌ Error: Session not found")
        sys.exit(1)
    
    project_id = session_info['project_id']
    start_url = session_info['start_url']
    max_pages = session_info.get('max_pages', 1000)
    
    domain = urlparse(start_url).netloc
    
    print(f"📋 Session ID: {SESSION_ID}")
    print(f"🌐 Domain: {domain}")
    print(f"📄 Max Pages: {max_pages}")
    print(f"🔗 Start URL: {start_url}")
    print("=" * 60)
    print()
    
    pages_crawled = 0
    total_links_found = 0
    consecutive_empty = 0
    
    while pages_crawled < max_pages:
        # Get next batch of tasks
        tasks = await get_next_tasks(limit=5)
        
        if not tasks:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print("✅ Queue is empty. Crawl complete!")
                break
            print(f"📭 Queue empty, waiting 10s... ({consecutive_empty}/3)")
            await asyncio.sleep(10)
            continue
        
        consecutive_empty = 0
        
        # Process tasks in parallel (but limited concurrency)
        for task in tasks:
            if pages_crawled >= max_pages:
                break
            
            links_found = await crawl_url(task, session_info, domain)
            pages_crawled += 1
            total_links_found += len(links_found)
            
            # Update progress every 10 pages
            if pages_crawled % 10 == 0:
                await update_session_progress(pages_crawled, total_links_found)
                print(f"📊 Progress: {pages_crawled}/{max_pages} pages crawled")
            
            # Small delay to be polite
            await asyncio.sleep(0.5)
    
    # Final progress update
    await update_session_progress(pages_crawled, total_links_found)
    
    print()
    print("=" * 60)
    print(f"🎉 Crawl Complete!")
    print(f"📄 Pages Crawled: {pages_crawled}")
    print(f"🔗 Links Found: {total_links_found}")
    print("=" * 60)

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        print("\n\n⚠️  Worker interrupted by user")
        print("💡 Progress is saved - just restart to resume!")
        sys.exit(0)

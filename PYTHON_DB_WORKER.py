#!/usr/bin/env python3
"""
Database-First Queue Worker for Internal Link Analyzer
=====================================================

This Python worker:
1. Initializes a crawl session (sends homepage to backend)
2. Requests next pending URL from backend
3. Crawls that URL
4. Sends page data and discovered links back to backend
5. Backend handles all queuing logic

Usage:
    python PYTHON_DB_WORKER.py <project_id> <start_url> [options]

Example:
    python PYTHON_DB_WORKER.py my-proj-123 https://example.com --max-pages 1000 --max-depth 5

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import requests
import sys
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

# Your Supabase Edge Function URL
# Replace with your actual Supabase project URL
BACKEND_URL = "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca"

# Supabase Anon Key (public key, safe to use)
ANON_KEY = "YOUR_SUPABASE_ANON_KEY"

# ============================================================================
# HTTP CLIENT
# ============================================================================

class BackendClient:
    """Handles all communication with the Supabase backend"""
    
    def __init__(self, backend_url, anon_key):
        self.backend_url = backend_url
        self.headers = {
            'Authorization': f'Bearer {anon_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_crawl(self, project_id, start_url, max_pages=1000, max_depth=5):
        """Initialize crawl session and queue homepage"""
        url = f"{self.backend_url}/projects/{project_id}/crawl/db-init"
        payload = {
            'startUrl': start_url,
            'maxPages': max_pages,
            'maxDepth': max_depth
        }
        
        print(f"🔧 Initializing crawl session...")
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Init failed: {data.get('error')}")
        
        session_id = data['data']['sessionId']
        print(f"✅ Session created: {session_id}")
        return session_id
    
    def get_next_url(self, session_id):
        """Request next pending URL to crawl"""
        url = f"{self.backend_url}/crawl/sessions/{session_id}/next"
        
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Get next failed: {data.get('error')}")
        
        return data.get('data')  # None if no URLs left
    
    def submit_results(self, session_id, task_id, url, title, content, links, status=200, error=None, max_depth=5):
        """Submit crawled page data and discovered links"""
        url_endpoint = f"{self.backend_url}/crawl/sessions/{session_id}/submit"
        payload = {
            'taskId': task_id,
            'url': url,
            'title': title,
            'content': content,
            'links': links,
            'status': status,
            'error': error,
            'maxDepth': max_depth
        }
        
        response = requests.post(url_endpoint, json=payload, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('success'):
            raise Exception(f"Submit failed: {data.get('error')}")
        
        return data.get('data', {})
    
    def get_stats(self, session_id):
        """Get crawl statistics"""
        url = f"{self.backend_url}/crawl/sessions/{session_id}/stats"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get('data', {})

# ============================================================================
# WEB CRAWLER
# ============================================================================

class WebCrawler:
    """Crawls a single page and extracts links"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
    
    def normalize_url(self, url):
        """Normalize URL for consistent comparison"""
        try:
            parsed = urlparse(url)
            # Remove trailing slashes from path
            path = parsed.path.rstrip('/')
            # Reconstruct URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            return normalized
        except:
            return url
    
    def is_internal_link(self, url):
        """Check if URL is internal (same domain)"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == ''
        except:
            return False
    
    def extract_links(self, html, current_url):
        """Extract all internal links from HTML"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip anchors, javascript, mailto, tel, etc.
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            
            # Only keep internal links
            if self.is_internal_link(absolute_url):
                normalized = self.normalize_url(absolute_url)
                if normalized not in links:
                    links.append(normalized)
        
        return links
    
    def crawl_page(self, url):
        """
        Crawl a single page and extract data
        Returns: (title, content, links, status_code, error)
        """
        try:
            print(f"  🌐 Fetching: {url}")
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Internal-Link-Analyzer-Bot/1.0'
            })
            
            status_code = response.status_code
            
            if status_code != 200:
                return None, None, [], status_code, f"HTTP {status_code}"
            
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else 'Untitled'
            
            # Extract text content (simple version)
            # Remove script and style tags
            for script in soup(['script', 'style']):
                script.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            # Limit content to 10000 characters
            content = text[:10000]
            
            # Extract internal links
            links = self.extract_links(html, url)
            
            print(f"  ✅ Title: {title}")
            print(f"  📋 Found {len(links)} internal links")
            
            return title, content, links, status_code, None
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return None, None, [], 0, str(e)

# ============================================================================
# MAIN WORKER LOOP
# ============================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python PYTHON_DB_WORKER.py <project_id> <start_url> [--max-pages N] [--max-depth D]")
        print("Example: python PYTHON_DB_WORKER.py my-proj https://example.com --max-pages 1000 --max-depth 5")
        sys.exit(1)
    
    project_id = sys.argv[1]
    start_url = sys.argv[2]
    
    # Parse optional arguments
    max_pages = 1000
    max_depth = 5
    
    for i, arg in enumerate(sys.argv):
        if arg == '--max-pages' and i + 1 < len(sys.argv):
            max_pages = int(sys.argv[i + 1])
        if arg == '--max-depth' and i + 1 < len(sys.argv):
            max_depth = int(sys.argv[i + 1])
    
    print("=" * 70)
    print("DATABASE-FIRST QUEUE WORKER")
    print("=" * 70)
    print(f"Project ID:  {project_id}")
    print(f"Start URL:   {start_url}")
    print(f"Max Pages:   {max_pages}")
    print(f"Max Depth:   {max_depth}")
    print("=" * 70)
    print()
    
    # Initialize clients
    backend = BackendClient(BACKEND_URL, ANON_KEY)
    crawler = WebCrawler(start_url)
    
    # Initialize session
    try:
        session_id = backend.initialize_crawl(project_id, start_url, max_pages, max_depth)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    print()
    print("🚀 Starting crawl loop...")
    print()
    
    pages_crawled = 0
    
    # Main crawl loop
    while True:
        # Get next URL to crawl
        try:
            task = backend.get_next_url(session_id)
        except Exception as e:
            print(f"❌ Error getting next URL: {e}")
            time.sleep(2)
            continue
        
        # No more URLs? Done!
        if not task:
            print()
            print("🏁 No more URLs to crawl. Queue is empty!")
            break
        
        task_id = task['taskId']
        url = task['url']
        depth = task['depth']
        
        print(f"📄 [{pages_crawled + 1}] Depth {depth}: {url}")
        
        # Crawl the page
        title, content, links, status, error = crawler.crawl_page(url)
        
        # Submit results to backend
        try:
            result = backend.submit_results(
                session_id=session_id,
                task_id=task_id,
                url=url,
                title=title,
                content=content,
                links=links,
                status=status,
                error=error,
                max_depth=max_depth
            )
            
            pages_crawled += 1
            
            if result:
                print(f"  💾 Saved to DB ({result.get('pagesProcessed', 0)}/{result.get('maxPages', 0)} pages)")
                print(f"  📋 Enqueued {result.get('linksEnqueued', 0)} new links")
            
        except Exception as e:
            print(f"  ❌ Error submitting results: {e}")
        
        print()
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Every 10 pages, show stats
        if pages_crawled % 10 == 0:
            try:
                stats = backend.get_stats(session_id)
                print("-" * 70)
                print(f"📊 STATS: Pending: {stats.get('pending', 0)} | "
                      f"Completed: {stats.get('completed', 0)} | "
                      f"Failed: {stats.get('failed', 0)} | "
                      f"Total: {stats.get('total', 0)}")
                print("-" * 70)
                print()
            except:
                pass
    
    # Final stats
    print()
    print("=" * 70)
    print("✅ CRAWL COMPLETED!")
    print("=" * 70)
    
    try:
        stats = backend.get_stats(session_id)
        print(f"Pages Crawled:  {stats.get('completed', 0)}")
        print(f"Failed:         {stats.get('failed', 0)}")
        print(f"Total in Queue: {stats.get('total', 0)}")
    except:
        print(f"Pages Crawled:  {pages_crawled}")
    
    print("=" * 70)

if __name__ == '__main__':
    main()

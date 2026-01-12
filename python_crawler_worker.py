"""
HYBRID CRAWLER WORKER - PRODUCTION GRADE
Architecture: Database-driven polling system

This worker:
1. Polls crawl_queue table for pending URLs
2. Crawls pages one-by-one and saves immediately
3. Adds discovered URLs back to queue
4. Runs indefinitely without timeout constraints
5. Can be stopped/resumed anytime

Usage:
    python python_crawler_worker.py <supabase_url> <supabase_service_role_key>
"""

import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
from supabase import create_client, Client

# Configuration
POLL_INTERVAL = 2  # seconds between queue checks
BATCH_SIZE = 1  # Process 1 URL at a time for immediate feedback
REQUEST_TIMEOUT = 30  # seconds
USER_AGENT = 'Mozilla/5.0 (compatible; InternalLinkAnalyzer/2.0; +https://example.com/bot)'


class CrawlerWorker:
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize the crawler worker"""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print(f"✅ Connected to Supabase: {supabase_url}")
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        try:
            parsed = urlparse(url)
            # Remove fragment
            url_without_fragment = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                url_without_fragment += f"?{parsed.query}"
            # Remove trailing slash except for root
            if url_without_fragment.endswith('/') and parsed.path != '/':
                url_without_fragment = url_without_fragment[:-1]
            return url_without_fragment.lower()
        except:
            return url.lower()
    
    def get_next_queue_item(self):
        """Get next pending URL from queue"""
        result = self.supabase.table('crawl_queue') \
            .select('*') \
            .eq('status', 'pending') \
            .order('priority', desc=True) \
            .order('created_at', desc=False) \
            .limit(1) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    def mark_processing(self, queue_id: str):
        """Mark queue item as processing"""
        self.supabase.table('crawl_queue') \
            .update({'status': 'processing', 'updated_at': datetime.utcnow().isoformat()}) \
            .eq('id', queue_id) \
            .execute()
    
    def mark_completed(self, queue_id: str):
        """Mark queue item as completed"""
        self.supabase.table('crawl_queue') \
            .update({'status': 'completed', 'updated_at': datetime.utcnow().isoformat()}) \
            .eq('id', queue_id) \
            .execute()
    
    def mark_failed(self, queue_id: str, error_message: str):
        """Mark queue item as failed"""
        self.supabase.table('crawl_queue') \
            .update({
                'status': 'failed',
                'error_message': error_message,
                'updated_at': datetime.utcnow().isoformat()
            }) \
            .eq('id', queue_id) \
            .execute()
    
    def fetch_page(self, url: str) -> tuple:
        """Fetch a page and return (html, status_code, response_time)"""
        start_time = time.time()
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response_time = int((time.time() - start_time) * 1000)
        
        return response.text, response.status_code, response_time
    
    def extract_seo_data(self, html: str, url: str, depth: int, status_code: int, response_time: int) -> dict:
        """Extract SEO data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Title
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else 'No Title'
        
        # Meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        meta_description = meta_desc.get('content', '').strip() if meta_desc else None
        
        # H1
        h1_tag = soup.find('h1')
        h1_text = h1_tag.get_text().strip() if h1_tag else None
        has_h1 = h1_tag is not None
        
        # Word count
        text_content = soup.get_text()
        words = re.findall(r'\w+', text_content)
        word_count = len(words)
        
        # Headers
        headers = []
        for i, level in enumerate([1, 2, 3, 4, 5, 6]):
            for idx, tag in enumerate(soup.find_all(f'h{level}')):
                headers.append({
                    'level': level,
                    'text': tag.get_text().strip()[:500],
                    'position': idx
                })
        
        # Paragraphs
        paragraphs = []
        for idx, p in enumerate(soup.find_all('p')):
            text = p.get_text().strip()
            if len(text) > 20:
                p_words = re.findall(r'\w+', text)
                paragraphs.append({
                    'text': text[:2000],
                    'word_count': len(p_words),
                    'position': idx
                })
        
        # Links
        links = []
        internal_count = 0
        external_count = 0
        content_count = 0
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            absolute_url = urljoin(url, href)
            anchor_text = a.get_text().strip()[:500]
            is_nofollow = 'nofollow' in a.get('rel', [])
            
            # Check if internal
            is_internal = urlparse(absolute_url).netloc == urlparse(url).netloc
            
            if is_internal:
                internal_count += 1
                # Simple heuristic: links in main content vs navigation
                parent_tags = [p.name for p in a.parents]
                if 'article' in parent_tags or 'main' in parent_tags:
                    content_count += 1
                    link_type = 'content'
                else:
                    link_type = 'internal'
            else:
                external_count += 1
                link_type = 'external'
            
            links.append({
                'href': absolute_url,
                'anchor_text': anchor_text,
                'link_type': link_type,
                'is_nofollow': is_nofollow,
            })
        
        # Page type classification
        path = urlparse(url).path.lower()
        if path == '/' or path == '':
            page_type = 'homepage'
        elif any(x in path for x in ['/category/', '/tag/', '/archive/', '/blog/']):
            page_type = 'category'
        elif any(x in path for x in ['/product/', '/item/', '/shop/']):
            page_type = 'product'
        elif word_count >= 300 and len(headers) >= 2:
            page_type = 'content'
        else:
            page_type = 'other'
        
        # Health score
        health_score = 100
        if status_code != 200:
            health_score -= 50
        if not title or title == 'No Title':
            health_score -= 15
        if not meta_description:
            health_score -= 10
        if not has_h1:
            health_score -= 15
        if word_count < 300:
            health_score -= 10
        if internal_count == 0:
            health_score -= 20
        health_score = max(0, health_score)
        
        return {
            'url': url,
            'title': title,
            'meta_description': meta_description,
            'depth': depth,
            'status': status_code,
            'word_count': word_count,
            'has_h1': has_h1,
            'h1_text': h1_text,
            'page_type': page_type,
            'health_score': health_score,
            'content_internal_links_count': content_count,
            'external_links_count': external_count,
            'internal_links_count': internal_count,
            'html': html[:100000],  # Truncate
            'content': ' '.join([p['text'] for p in paragraphs])[:50000],
            'headers': headers,
            'paragraphs': paragraphs[:30],
            'links': links,
        }
    
    def save_page(self, session_id: str, project_id: str, seo_data: dict):
        """Save page and related data to database"""
        # 1. Save page
        page_result = self.supabase.table('pages').insert([{
            'project_id': project_id,
            'crawl_session_id': session_id,
            'url': seo_data['url'],
            'title': seo_data['title'],
            'meta_description': seo_data['meta_description'],
            'depth': seo_data['depth'],
            'status': seo_data['status'],
            'content': seo_data['content'],
            'html': seo_data['html'],
            'word_count': seo_data['word_count'],
            'has_h1': seo_data['has_h1'],
            'content_internal_links_count': seo_data['content_internal_links_count'],
            'external_links_count': seo_data['external_links_count'],
            'page_type': seo_data['page_type'],
            'health_score': seo_data['health_score'],
        }]).execute()
        
        if not page_result.data:
            raise Exception("Failed to save page")
        
        page_id = page_result.data[0]['id']
        
        # 2. Save headers
        if seo_data['headers']:
            header_records = [{
                'page_id': page_id,
                'project_id': project_id,
                'level': h['level'],
                'text': h['text'],
                'position': h['position'],
            } for h in seo_data['headers']]
            self.supabase.table('page_headers').insert(header_records).execute()
        
        # 3. Save paragraphs
        if seo_data['paragraphs']:
            paragraph_records = [{
                'page_id': page_id,
                'project_id': project_id,
                'text': p['text'],
                'word_count': p['word_count'],
                'position': p['position'],
            } for p in seo_data['paragraphs']]
            self.supabase.table('page_paragraphs').insert(paragraph_records).execute()
        
        # 4. Save links
        if seo_data['links']:
            link_records = [{
                'page_id': page_id,
                'project_id': project_id,
                'source_url': seo_data['url'],
                'target_url': link['href'],
                'anchor_text': link['anchor_text'],
                'link_type': link['link_type'],
                'is_nofollow': link['is_nofollow'],
            } for link in seo_data['links']]
            self.supabase.table('page_links').insert(link_records).execute()
        
        return page_id
    
    def enqueue_new_urls(self, session_id: str, base_url: str, links: list, current_depth: int, max_pages: int):
        """Add newly discovered URLs to the queue"""
        # Get current queue + completed count
        queue_result = self.supabase.table('crawl_queue') \
            .select('normalized_url', count='exact') \
            .eq('session_id', session_id) \
            .execute()
        
        existing_urls = {item['normalized_url'] for item in queue_result.data}
        total_in_queue = len(existing_urls)
        
        # Filter internal links only
        base_netloc = urlparse(base_url).netloc
        internal_links = [
            link for link in links
            if link['link_type'] in ['content', 'internal'] and urlparse(link['href']).netloc == base_netloc
        ]
        
        # Add new URLs to queue
        new_urls = []
        for link in internal_links:
            normalized = self.normalize_url(link['href'])
            if normalized not in existing_urls and len(new_urls) + total_in_queue < max_pages:
                existing_urls.add(normalized)
                new_urls.append({
                    'session_id': session_id,
                    'url': link['href'],
                    'normalized_url': normalized,
                    'depth': current_depth + 1,
                    'priority': 50,  # Normal priority
                    'status': 'pending',
                })
        
        if new_urls:
            self.supabase.table('crawl_queue').insert(new_urls).execute()
            print(f"    ➕ Added {len(new_urls)} new URLs to queue")
    
    def update_session_progress(self, session_id: str):
        """Update session statistics"""
        # Count pages
        pages_result = self.supabase.table('pages') \
            .select('id', count='exact') \
            .eq('crawl_session_id', session_id) \
            .execute()
        
        pages_crawled = pages_result.count or 0
        
        # Update session
        self.supabase.table('crawl_sessions') \
            .update({
                'pages_crawled': pages_crawled,
                'updated_at': datetime.utcnow().isoformat(),
            }) \
            .eq('id', session_id) \
            .execute()
    
    def check_if_complete(self, session_id: str, max_pages: int) -> bool:
        """Check if crawl is complete"""
        # Count pending items
        pending_result = self.supabase.table('crawl_queue') \
            .select('id', count='exact') \
            .eq('session_id', session_id) \
            .eq('status', 'pending') \
            .execute()
        
        pending_count = pending_result.count or 0
        
        # Count pages crawled
        pages_result = self.supabase.table('pages') \
            .select('id', count='exact') \
            .eq('crawl_session_id', session_id) \
            .execute()
        
        pages_crawled = pages_result.count or 0
        
        # Complete if no pending items OR reached max pages
        if pending_count == 0 or pages_crawled >= max_pages:
            self.supabase.table('crawl_sessions') \
                .update({
                    'status': 'completed',
                    'pages_crawled': pages_crawled,
                    'completed_at': datetime.utcnow().isoformat(),
                }) \
                .eq('id', session_id) \
                .execute()
            return True
        
        return False
    
    def process_queue_item(self, queue_item: dict):
        """Process a single queue item"""
        queue_id = queue_item['id']
        url = queue_item['url']
        session_id = queue_item['session_id']
        depth = queue_item['depth']
        
        print(f"  🌐 Crawling: {url}")
        
        try:
            # Mark as processing
            self.mark_processing(queue_id)
            
            # Get session info
            session_result = self.supabase.table('crawl_sessions') \
                .select('*') \
                .eq('id', session_id) \
                .single() \
                .execute()
            
            if not session_result.data:
                raise Exception(f"Session {session_id} not found")
            
            session = session_result.data
            project_id = session['project_id']
            max_pages = session.get('max_pages', 1000)
            
            # Get base URL from project
            project_result = self.supabase.table('projects') \
                .select('base_url') \
                .eq('id', project_id) \
                .single() \
                .execute()
            
            base_url = project_result.data['base_url']
            
            # Fetch page
            html, status_code, response_time = self.fetch_page(url)
            print(f"    📡 {status_code} ({response_time}ms)")
            
            # Extract SEO data
            seo_data = self.extract_seo_data(html, url, depth, status_code, response_time)
            
            # Save page (IMMEDIATELY - streams to database)
            page_id = self.save_page(session_id, project_id, seo_data)
            print(f"    ✅ Saved page {page_id}")
            
            # Enqueue new URLs
            self.enqueue_new_urls(session_id, base_url, seo_data['links'], depth, max_pages)
            
            # Mark completed
            self.mark_completed(queue_id)
            
            # Update session progress
            self.update_session_progress(session_id)
            
            # Check if crawl is complete
            if self.check_if_complete(session_id, max_pages):
                print(f"✅ Crawl session {session_id} completed!")
            
        except Exception as e:
            print(f"    ❌ Failed: {str(e)}")
            self.mark_failed(queue_id, str(e))
    
    def run(self):
        """Main worker loop"""
        print("🚀 Crawler Worker started")
        print(f"⏱️  Polling every {POLL_INTERVAL}s")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                # Get next queue item
                queue_item = self.get_next_queue_item()
                
                if queue_item:
                    self.process_queue_item(queue_item)
                else:
                    # No items in queue, wait
                    print("⏸️  Queue empty, waiting...")
                    time.sleep(POLL_INTERVAL)
                    
            except KeyboardInterrupt:
                print("\n⏹️  Worker stopped by user")
                break
            except Exception as e:
                print(f"❌ Worker error: {str(e)}")
                time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python python_crawler_worker.py <supabase_url> <supabase_service_role_key>")
        sys.exit(1)
    
    supabase_url = sys.argv[1]
    supabase_key = sys.argv[2]
    
    worker = CrawlerWorker(supabase_url, supabase_key)
    worker.run()

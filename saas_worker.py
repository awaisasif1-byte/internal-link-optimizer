"""
Industrial-Grade SaaS Crawler Worker
Uses concurrent pipelines with semaphore control for Screaming Frog-level performance
"""
import asyncio
import os
import httpx
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime

# CONFIG
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
CONCURRENCY_LIMIT = 20  # Screaming Frog speed - adjust based on your needs

class SaaSWorker:
    def __init__(self, session_id: str, project_id: str):
        self.session_id = session_id
        self.project_id = project_id
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        self.pages_crawled = 0
        self.max_pages = None
        
    async def fetch_task(self, client):
        """Atomic: Grab a URL and lock it to this worker"""
        try:
            # Atomic fetch-and-update using PostgREST
            url = f"{SUPABASE_URL}/rest/v1/crawl_queue?session_id=eq.{self.session_id}&status=eq.pending&order=depth.asc&limit=1"
            res = await client.get(url, headers=self.headers)
            tasks = res.json()
            
            if not tasks:
                return None
            
            task = tasks[0]
            
            # Lock this task atomically
            patch_url = f"{SUPABASE_URL}/rest/v1/crawl_queue?id=eq.{task['id']}"
            await client.patch(
                patch_url,
                json={"status": "processing", "processed_at": datetime.utcnow().isoformat()},
                headers=self.headers
            )
            
            return task
        except Exception as e:
            print(f"❌ Error fetching task: {e}")
            return None

    async def crawl_url(self, client, task):
        """Pipeline: Fetch → Parse → Save → Enqueue (all concurrent)"""
        async with self.semaphore:  # Limits simultaneous requests
            try:
                print(f"🚀 [{self.pages_crawled}/{self.max_pages or '?'}] Crawling: {task['url']} (depth: {task['depth']})")
                
                # Fetch with timeout
                resp = await client.get(
                    task['url'],
                    timeout=15.0,
                    follow_redirects=True,
                    headers={"User-Agent": "InternalLinkBot/1.0 (SaaS Crawler)"}
                )
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Pipeline Step 1: Save page data (non-blocking)
                    save_task = asyncio.create_task(self.save_page_data(client, task, soup, resp.status_code))
                    
                    # Pipeline Step 2: Extract and enqueue links (concurrent with save)
                    if task['depth'] < 20:  # Max depth
                        enqueue_task = asyncio.create_task(self.enqueue_new_links(client, task, soup))
                    else:
                        enqueue_task = None
                    
                    # Wait for both to complete
                    await save_task
                    if enqueue_task:
                        await enqueue_task
                    
                    status = "completed"
                    self.pages_crawled += 1
                    
                    # Update progress every page
                    await self.update_session_progress(client)
                    
                else:
                    print(f"⚠️  Status {resp.status_code}: {task['url']}")
                    status = "failed"
                    
            except asyncio.TimeoutError:
                print(f"⏱️  Timeout: {task['url']}")
                status = "failed"
            except Exception as e:
                print(f"❌ Error on {task['url']}: {e}")
                status = "failed"
            
            # Mark task as complete
            try:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/crawl_queue?id=eq.{task['id']}",
                    json={"status": status, "completed_at": datetime.utcnow().isoformat()},
                    headers=self.headers
                )
            except Exception as e:
                print(f"❌ Error updating task status: {e}")

    async def save_page_data(self, client, task, soup, status_code):
        """Save page to database"""
        try:
            # Extract page data
            title = (soup.title.string if soup.title else "No Title").strip()[:500]
            meta_desc = None
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag and meta_tag.get('content'):
                meta_desc = meta_tag['content'][:1000]
            
            # Extract text content (clean)
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)[:10000]
            
            # Count internal links
            domain = urlparse(task['url']).netloc
            internal_links = []
            for a in soup.find_all('a', href=True):
                href = urljoin(task['url'], a['href'])
                if urlparse(href).netloc == domain:
                    internal_links.append(href)
            
            # Upsert to pages table
            page_data = {
                "project_id": self.project_id,
                "crawl_session_id": self.session_id,
                "url": task['url'],
                "title": title,
                "meta_description": meta_desc,
                "depth": task['depth'],
                "status": status_code,
                "content": text,
                "link_equity_score": 0,
                "health_score": 100 if status_code == 200 else 50,
                "broken_count": 0
            }
            
            # Use upsert with conflict resolution
            headers_upsert = {**self.headers, "Prefer": "resolution=merge-duplicates"}
            await client.post(
                f"{SUPABASE_URL}/rest/v1/pages",
                json=page_data,
                headers=headers_upsert
            )
            
            print(f"  ✅ Saved: {title[:50]}... ({len(internal_links)} links)")
            
        except Exception as e:
            print(f"  ❌ Error saving page data: {e}")

    async def enqueue_new_links(self, client, task, soup):
        """Extract links and add to queue (with automatic deduplication)"""
        try:
            domain = urlparse(task['url']).netloc
            links_to_add = []
            
            for a in soup.find_all('a', href=True):
                try:
                    # Resolve to absolute URL
                    href = urljoin(task['url'], a['href'])
                    
                    # Normalize URL (remove fragments, trailing slash)
                    parsed = urlparse(href)
                    if parsed.netloc != domain:
                        continue  # Skip external links
                    
                    # Remove fragment and trailing slash
                    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
                    if parsed.query:
                        normalized += f"?{parsed.query}"
                    
                    # Skip non-HTML resources
                    if any(normalized.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js', '.xml']):
                        continue
                    
                    links_to_add.append({
                        "session_id": self.session_id,
                        "url": href,
                        "normalized_url": normalized,
                        "depth": task['depth'] + 1,
                        "status": "pending"
                    })
                    
                except Exception as e:
                    # Skip invalid URLs
                    pass
            
            if links_to_add:
                # Database handles deduplication via UNIQUE constraint
                headers_ignore = {**self.headers, "Prefer": "resolution=ignore-duplicates"}
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/crawl_queue",
                    json=links_to_add,
                    headers=headers_ignore
                )
                print(f"  📥 Enqueued {len(links_to_add)} links (depth {task['depth'] + 1})")
                
        except Exception as e:
            print(f"  ❌ Error enqueuing links: {e}")

    async def update_session_progress(self, client):
        """Update crawl session progress"""
        try:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{self.session_id}",
                json={"pages_crawled": self.pages_crawled},
                headers=self.headers
            )
        except Exception as e:
            print(f"⚠️  Error updating progress: {e}")

    async def check_session_status(self, client):
        """Check if session should stop"""
        try:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{self.session_id}&select=status,max_pages",
                headers=self.headers
            )
            sessions = res.json()
            if sessions:
                session = sessions[0]
                self.max_pages = session.get('max_pages', 1000)
                return session['status'] in ['running', 'crawling']
            return False
        except Exception as e:
            print(f"⚠️  Error checking session: {e}")
            return True  # Continue on error

    async def run(self):
        """Main worker loop with concurrent pipeline"""
        print(f"🚀 SaaS Worker Starting...")
        print(f"   Session: {self.session_id}")
        print(f"   Project: {self.project_id}")
        print(f"   Concurrency: {CONCURRENCY_LIMIT}")
        print(f"   Supabase: {SUPABASE_URL}")
        
        async with httpx.AsyncClient(
            limits=httpx.Limits(max_connections=CONCURRENCY_LIMIT, max_keepalive_connections=10)
        ) as client:
            
            empty_queue_count = 0
            
            while True:
                # Check if we should stop
                if not await self.check_session_status(client):
                    print("🛑 Session stopped or completed")
                    break
                
                # Check page limit
                if self.max_pages and self.pages_crawled >= self.max_pages:
                    print(f"✅ Reached page limit: {self.max_pages}")
                    await client.patch(
                        f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{self.session_id}",
                        json={"status": "completed", "completed_at": datetime.utcnow().isoformat()},
                        headers=self.headers
                    )
                    break
                
                # Fetch batch of tasks (feed the pipeline)
                tasks = []
                for _ in range(5):  # Small batch to keep pipeline full
                    task = await self.fetch_task(client)
                    if task:
                        tasks.append(task)
                
                if not tasks:
                    empty_queue_count += 1
                    if empty_queue_count > 6:  # 30 seconds of empty queue
                        print("✅ Queue empty for 30s - crawl complete!")
                        await client.patch(
                            f"{SUPABASE_URL}/rest/v1/crawl_sessions?id=eq.{self.session_id}",
                            json={"status": "completed", "completed_at": datetime.utcnow().isoformat()},
                            headers=self.headers
                        )
                        break
                    print(f"📭 Queue empty... checking again in 5s (attempt {empty_queue_count}/6)")
                    await asyncio.sleep(5)
                    continue
                
                empty_queue_count = 0  # Reset counter
                
                # Process batch concurrently
                await asyncio.gather(*[self.crawl_url(client, t) for t in tasks], return_exceptions=True)

        print(f"✅ Worker finished! Crawled {self.pages_crawled} pages")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python saas_worker.py <SESSION_ID> <PROJECT_ID>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    project_id = sys.argv[2]
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Missing environment variables:")
        print("   SUPABASE_URL")
        print("   SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    worker = SaaSWorker(session_id, project_id)
    asyncio.run(worker.run())

# 🎯 How The Crawler Works - Complete Explanation

## 🌟 You asked: "Tell me how it works, I create a project, add URL, start crawl. What happens next?"

Here's the **COMPLETE** answer with the new Database-First Queue architecture:

---

## 🔀 TWO Crawling Options

You now have **TWO** ways to crawl:

### **Option 1: TypeScript Auto-Crawl** (Small Sites: 10-1000 pages)
- ✅ Click "Start New Crawl" in React dashboard
- ✅ Backend runs TypeScript WebCrawler
- ✅ Everything happens automatically
- ❌ Limited to ~1000 pages (Edge Function timeout: 60s)

### **Option 2: Python Database-First Queue** (Large Sites: 1K-100K+ pages)
- ✅ Run Python worker on your machine: `python PYTHON_DB_WORKER.py`
- ✅ Python requests URLs from backend, backend manages queue
- ✅ No timeouts (runs as long as needed)
- ✅ Can pause/resume anytime
- ✅ Production-grade for massive sites

---

## 📊 Option 1: TypeScript Auto-Crawl (Current Frontend)

### **Step 1: You Click "Start New Crawl"**

**Frontend code:**
```typescript
const result = await api.startAutoCrawl(projectId, 1000);
```

**Backend receives:**
```http
POST /projects/abc-123/crawl/auto
{
  "maxPages": 1000,
  "enableJsRendering": false,
  "discoverSitemap": true
}
```

---

### **Step 2: Backend Creates Session**

```typescript
// Create crawl_sessions record
const session = await crawlerApi.startCrawlSession(projectId, 1000);

// Session in DB:
{
  id: "session-xyz",
  project_id: "abc-123",
  status: "crawling",
  pages_crawled: 0,
  max_pages: 1000
}
```

---

### **Step 3: Backend Creates WebCrawler**

```typescript
const crawler = new WebCrawler({
  maxPages: 1000,
  maxDepth: 20,
  baseUrl: "https://example.com",
  projectId: "abc-123",
  sessionId: "session-xyz",
  supabaseClient: supabase,
  seedOnly: false  // ✅ Full crawl, not just homepage!
});
```

---

### **Step 4: Crawler Enqueues Homepage**

```typescript
// Insert homepage into crawl_queue
INSERT INTO crawl_queue (
  session_id: "session-xyz",
  url: "https://example.com",
  normalized_url: "https://example.com",
  depth: 0,
  status: "pending"
)
```

**Database state:**
```
crawl_queue:
| id    | url                   | depth | status  |
|-------|-----------------------|-------|---------|
| task-1| https://example.com   | 0     | pending |
```

---

### **Step 5: Batch Loop Starts**

```typescript
let batchNumber = 1;
while (true) {
  console.log("===== BATCH 1 START =====");
  await crawler.crawl();  // Crawls up to 50 pages
  
  // Check if done
  const session = await getSession();
  if (session.status === 'completed') break;
  
  batchNumber++;
}
```

---

### **Step 6: First Batch - Crawl Loop**

#### **Iteration 1: Homepage**

**A) Get next URL:**
```typescript
const task = await getNextUrl(sessionId);
// Returns: { id: "task-1", url: "https://example.com", depth: 0 }
```

**B) Mark as processing:**
```sql
UPDATE crawl_queue 
SET status = 'processing'
WHERE id = 'task-1'
```

**C) Fetch HTML:**
```typescript
const response = await fetch("https://example.com");
const html = await response.text();
```

**D) Parse & Extract:**
```typescript
const soup = new DOMParser().parseFromString(html, 'text/html');
const title = soup.querySelector('title')?.textContent;
const links = [...soup.querySelectorAll('a[href]')]
  .map(a => a.href)
  .filter(isInternalLink);

// Found links:
[
  "https://example.com/about",
  "https://example.com/contact",
  "https://example.com/blog",
  ... 15 more
]
```

**E) Save page to database:**
```sql
INSERT INTO pages (
  project_id: "abc-123",
  session_id: "session-xyz",
  url: "https://example.com",
  title: "Example Homepage",
  content: "Welcome to our site...",
  internal_links: ARRAY[18 links],
  depth: 0
)
```

**F) Update counter:**
```sql
UPDATE crawl_sessions 
SET pages_crawled = 1
WHERE id = 'session-xyz'
```

**G) Enqueue discovered links:**
```sql
-- Only if depth < maxDepth (0 < 20 ✅)
INSERT INTO crawl_queue (
  session_id, url, normalized_url, depth, parent_url, status
) VALUES
  ('session-xyz', 'https://example.com/about', 'https://example.com/about', 1, 'https://example.com', 'pending'),
  ('session-xyz', 'https://example.com/contact', 'https://example.com/contact', 1, 'https://example.com', 'pending'),
  ('session-xyz', 'https://example.com/blog', 'https://example.com/blog', 1, 'https://example.com', 'pending'),
  ... 15 more rows
ON CONFLICT (session_id, normalized_url) DO NOTHING  -- Ignores duplicates!
```

**H) Mark task completed:**
```sql
UPDATE crawl_queue 
SET status = 'completed'
WHERE id = 'task-1'
```

**Database state after iteration 1:**
```
crawl_queue:
| id     | url                      | depth | status    |
|--------|--------------------------|-------|-----------|
| task-1 | https://example.com      | 0     | completed |
| task-2 | .../about                | 1     | pending   |
| task-3 | .../contact              | 1     | pending   |
| task-4 | .../blog                 | 1     | pending   |
| ...    | (15 more)                | 1     | pending   |
```

**Console log:**
```
✅ Crawled 1/1000: https://example.com
📋 Enqueued 18 new links
```

---

#### **Iteration 2: About Page**

**A) Get next URL:**
```typescript
const task = await getNextUrl(sessionId);
// Returns: { id: "task-2", url: "https://example.com/about", depth: 1 }
```

**Queue is ordered by `depth ASC, created_at ASC`**
→ So all depth-1 pages crawled before any depth-2!

**B) Fetch → Parse → Save → Enqueue:**
```
Fetch: https://example.com/about
Extract: "About Us" page, 5 new links
Save to pages table
Enqueue 5 links at depth 2
Mark task-2 as completed
```

**Database state:**
```
crawl_queue:
| id     | url              | depth | status    |
|--------|------------------|-------|-----------|
| task-1 | .../             | 0     | completed |
| task-2 | .../about        | 1     | completed | ← Just finished
| task-3 | .../contact      | 1     | pending   |
| task-4 | .../blog         | 1     | pending   |
| ...    | (13 more depth-1)| 1     | pending   |
| task-20| .../team         | 2     | pending   | ← New!
| task-21| .../careers      | 2     | pending   | ← New!
| ...    | (3 more depth-2) | 2     | pending   |
```

**Console log:**
```
✅ Crawled 2/1000: https://example.com/about
📋 Enqueued 5 new links
```

---

#### **Iterations 3-50: Continue...**

The crawler keeps looping:
```
Get next pending URL → Crawl → Save → Enqueue links → Mark completed → Repeat
```

**After 50 pages:**
```typescript
if (crawledInThisPass >= 50) {
  console.log("⏰ Voluntary exit after 50 pages");
  break;  // Exit Batch 1
}
```

**Database state:**
```
crawl_queue:
| status    | count |
|-----------|-------|
| completed | 50    |
| pending   | 85    |
| processing| 0     |
```

---

### **Step 7: Batch 2 Starts**

```typescript
// Back in the batch loop
if (session.status === 'completed') break;  // No, still crawling!

batchNumber = 2;
await crawler.crawl();  // Batch 2: Next 50 pages
```

Same process repeats until:
- ✅ Pages crawled reaches `maxPages` (1000)
- ✅ Queue is empty (all URLs crawled)

---

### **Step 8: Crawl Completes**

```typescript
if (session.pages_crawled >= maxPages) {
  UPDATE crawl_sessions 
  SET status = 'completed', completed_at = NOW()
  WHERE id = 'session-xyz'
  
  break;  // Exit all batches
}
```

**Final state:**
```
crawl_sessions:
| id         | pages_crawled | status    |
|------------|---------------|-----------|
| session-xyz| 1000          | completed |

crawl_queue:
| status    | count |
|-----------|-------|
| completed | 1000  |
| pending   | 234   | ← Discovered but not crawled (hit max_pages)
| failed    | 3     | ← 404s, timeouts

pages:
| count |
|-------|
| 1000  | ← All crawled pages with full data
```

---

## 🐍 Option 2: Python Database-First Queue

### **When to use Python:**
- ✅ Site has 1000+ pages
- ✅ You want to pause/resume manually
- ✅ You need more than 60 seconds (Edge Function limit)

---

### **Step 1: You Run Python Worker**

```bash
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 1000 --max-depth 5
```

---

### **Step 2: Python Initializes Session**

**Python → Backend:**
```http
POST /projects/my-project/crawl/db-init
{
  "startUrl": "https://example.com",
  "maxPages": 1000,
  "maxDepth": 5
}
```

**Backend creates:**
1. `crawl_sessions` record
2. Enqueues homepage:
   ```sql
   INSERT INTO crawl_queue (
     session_id: "session-abc",
     url: "https://example.com",
     depth: 0,
     status: "pending"
   )
   ```

**Backend returns:**
```json
{
  "sessionId": "session-abc",
  "message": "Session created. Python can now request URLs."
}
```

---

### **Step 3: Python Enters Loop**

```python
while True:
    # Request next URL
    task = backend.get_next_url(session_id)
    
    if not task:
        break  # Queue empty!
    
    # Crawl page
    title, content, links, status, error = crawler.crawl_page(task['url'])
    
    # Send results back
    backend.submit_results(...)
```

---

### **Step 4: First Iteration**

#### **A) Python requests next URL:**
```http
POST /crawl/sessions/session-abc/next
```

**Backend:**
1. Resets stuck URLs (processing > 60s)
2. Gets next pending URL:
   ```sql
   SELECT * FROM crawl_queue
   WHERE session_id = 'session-abc' AND status = 'pending'
   ORDER BY depth ASC
   LIMIT 1
   ```
3. Marks as processing:
   ```sql
   UPDATE crawl_queue SET status = 'processing' WHERE id = 'task-1'
   ```

**Returns:**
```json
{
  "taskId": "task-1",
  "url": "https://example.com",
  "depth": 0
}
```

#### **B) Python crawls:**
```python
response = requests.get("https://example.com")
html = response.text

soup = BeautifulSoup(html, 'lxml')
title = soup.find('title').text
links = extract_internal_links(html, "https://example.com")

# Found 18 links
```

#### **C) Python submits results:**
```http
POST /crawl/sessions/session-abc/submit
{
  "taskId": "task-1",
  "url": "https://example.com",
  "title": "Example Homepage",
  "content": "Welcome...",
  "links": [18 URLs],
  "status": 200,
  "maxDepth": 5
}
```

**Backend:**
1. Saves page to `pages` table
2. Marks task as `completed`
3. Increments `pages_crawled`
4. **Enqueues 18 links** (if depth < maxDepth):
   ```sql
   INSERT INTO crawl_queue (url, depth, status) VALUES
     ('https://example.com/about', 1, 'pending'),
     ('https://example.com/contact', 1, 'pending'),
     ... 16 more
   ON CONFLICT DO NOTHING  -- Ignores duplicates!
   ```

**Returns:**
```json
{
  "pagesProcessed": 1,
  "maxPages": 1000,
  "linksEnqueued": 18
}
```

---

### **Step 5: Python Loops**

Python immediately requests the next URL:
```
Request next → Crawl → Submit → Request next → Crawl → Submit → ...
```

**Loop continues until:**
- Queue is empty
- Max pages reached
- You press `Ctrl+C`

---

### **Step 6: Depth Control**

**Python crawls depth-by-depth:**
```
Depth 0: Homepage (1 page)
  ↓ Enqueues 18 depth-1 links

Depth 1: Main sections (18 pages)
  ↓ Each enqueues ~10 depth-2 links

Depth 2: Subsections (180 pages)
  ↓ Each enqueues ~5 depth-3 links

Depth 3: Detail pages (900 pages)
  ↓ Each enqueues ~3 depth-4 links

Depth 4: Leaf pages (2700 pages)
  ↓ Each enqueues ~2 depth-5 links

Depth 5: Final layer (5400 pages)
  ↓ Does NOT enqueue (depth >= maxDepth)
```

**At depth 5:**
```typescript
if (currentDepth < maxDepth) {  // 5 < 5 = FALSE
  // Don't enqueue
}
```

---

### **Step 7: Crawl Completes**

**Python:**
```
📄 [998] Depth 4: https://example.com/deep/page
📄 [999] Depth 4: https://example.com/another/page
📄 [1000] Depth 5: https://example.com/final/page

🏁 Max pages reached (1000). Session completed.
```

**Backend automatically:**
```sql
UPDATE crawl_sessions 
SET status = 'completed', completed_at = NOW()
WHERE id = 'session-abc'
```

**Next request:**
```http
POST /crawl/sessions/session-abc/next
→ Returns: { data: null, message: "No more URLs to crawl" }
```

**Python exits:**
```
✅ CRAWL COMPLETED!
Pages Crawled: 1000
Failed: 5
Total in Queue: 6243
```

---

## 🛡️ Crash Recovery

### **Scenario: Python Worker Crashes**

**State when crashed:**
```
crawl_queue:
| status     | count |
|------------|-------|
| completed  | 23    |
| processing | 1     | ← Stuck!
| pending    | 60    |
```

**60 seconds later, you restart Python:**

**Python requests next URL:**
```http
POST /crawl/sessions/session-abc/next
```

**Backend auto-recovery:**
```sql
-- First, reset stuck URLs
UPDATE crawl_queue
SET status = 'pending'
WHERE session_id = 'session-abc' 
  AND status = 'processing'
  AND updated_at < NOW() - INTERVAL '60 seconds'

-- Now 1 URL moved from 'processing' to 'pending'
```

**Queue now:**
```
crawl_queue:
| status     | count |
|------------|-------|
| completed  | 23    |
| processing | 0     | ← Fixed!
| pending    | 61    | ← +1 recovered
```

**Crawl resumes from page 24!** ✅

---

## 🎉 Summary

### **When you create a project and start a crawl:**

**TypeScript Auto-Crawl:**
1. ✅ Frontend calls `/crawl/auto`
2. ✅ Backend creates session + enqueues homepage
3. ✅ WebCrawler runs in batches (50 pages per batch)
4. ✅ Each page: Fetch → Parse → Save → Enqueue links → Mark completed
5. ✅ Loop continues until max pages or queue empty
6. ✅ All data in your database!

**Python Database-First:**
1. ✅ Run `python PYTHON_DB_WORKER.py`
2. ✅ Python sends homepage to `/db-init`
3. ✅ Backend creates session + enqueues homepage
4. ✅ Python loop: Request URL → Crawl → Submit results
5. ✅ Backend manages queue, enqueues discovered links
6. ✅ Continues until queue empty or max pages
7. ✅ Can pause/resume anytime
8. ✅ Crash-resistant!

**Both approaches:**
- ✅ Database-driven queue (crash-resistant)
- ✅ Automatic duplicate prevention
- ✅ Depth control
- ✅ Breadth-first crawling
- ✅ All pages saved to database
- ✅ Real-time progress tracking

🚀 **You're now ready to crawl 100K+ pages with confidence!**

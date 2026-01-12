# 🏗️ Database-First Queue Architecture

## Overview

This system implements a **Database-First Queue** where:
- **Python Worker** = Does the crawling (fetches HTML, extracts links)
- **Backend (Supabase Edge Functions)** = Manages the queue and stores data
- **Database** = Central source of truth for what to crawl next

## 🔄 Complete Flow

### **Step 1: Initialize Crawl**

**Python sends:**
```bash
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 1000 --max-depth 5
```

**Python → Backend:**
```http
POST /projects/my-project/crawl/db-init
{
  "startUrl": "https://example.com",
  "maxPages": 1000,
  "maxDepth": 5
}
```

**Backend does:**
1. Creates `crawl_sessions` record
2. Inserts homepage into `crawl_queue`:
   ```sql
   INSERT INTO crawl_queue (
     session_id, 
     url, 
     normalized_url, 
     depth, 
     status
   ) VALUES (
     'session-123',
     'https://example.com',
     'https://example.com',
     0,
     'pending'
   )
   ```
3. Returns `sessionId` to Python

**Response:**
```json
{
  "success": true,
  "data": {
    "sessionId": "session-123",
    "projectId": "my-project",
    "maxPages": 1000,
    "maxDepth": 5
  }
}
```

---

### **Step 2: Get Next URL (Loop)**

**Python → Backend:**
```http
POST /crawl/sessions/session-123/next
```

**Backend does:**
1. **Reset stuck URLs** (processing > 60 seconds):
   ```sql
   UPDATE crawl_queue 
   SET status = 'pending'
   WHERE session_id = 'session-123'
     AND status = 'processing'
     AND updated_at < NOW() - INTERVAL '60 seconds'
   ```

2. **Get next pending URL:**
   ```sql
   SELECT * FROM crawl_queue
   WHERE session_id = 'session-123'
     AND status = 'pending'
   ORDER BY depth ASC, created_at ASC
   LIMIT 1
   ```

3. **Mark as processing:**
   ```sql
   UPDATE crawl_queue
   SET status = 'processing', updated_at = NOW()
   WHERE id = 'task-456'
   ```

**Response (if URL found):**
```json
{
  "success": true,
  "data": {
    "taskId": "task-456",
    "url": "https://example.com/about",
    "depth": 1,
    "parentUrl": "https://example.com"
  }
}
```

**Response (if queue empty):**
```json
{
  "success": true,
  "data": null,
  "message": "No more URLs to crawl"
}
```

---

### **Step 3: Crawl Page**

**Python does:**
1. Fetch HTML from `https://example.com/about`
2. Extract title: "About Us"
3. Extract text content
4. Extract all internal links:
   ```python
   links = [
     "https://example.com/team",
     "https://example.com/contact",
     "https://example.com/careers"
   ]
   ```

---

### **Step 4: Submit Results**

**Python → Backend:**
```http
POST /crawl/sessions/session-123/submit
{
  "taskId": "task-456",
  "url": "https://example.com/about",
  "title": "About Us",
  "content": "We are a company that...",
  "links": [
    "https://example.com/team",
    "https://example.com/contact",
    "https://example.com/careers"
  ],
  "status": 200,
  "maxDepth": 5
}
```

**Backend does:**

1. **Save page to database:**
   ```sql
   INSERT INTO pages (
     project_id,
     session_id,
     url,
     title,
     content,
     internal_links,
     depth,
     status_code
   ) VALUES (
     'my-project',
     'session-123',
     'https://example.com/about',
     'About Us',
     'We are a company...',
     ARRAY['https://example.com/team', ...],
     1,
     200
   )
   ```

2. **Mark task as completed:**
   ```sql
   UPDATE crawl_queue
   SET status = 'completed'
   WHERE id = 'task-456'
   ```

3. **Increment pages counter:**
   ```sql
   UPDATE crawl_sessions
   SET pages_crawled = pages_crawled + 1
   WHERE id = 'session-123'
   ```

4. **Enqueue discovered links** (only if depth < maxDepth):
   ```sql
   -- Current depth = 1, maxDepth = 5, so enqueue at depth 2
   INSERT INTO crawl_queue (
     session_id,
     url,
     normalized_url,
     depth,
     parent_url,
     status
   ) VALUES
     ('session-123', 'https://example.com/team', 'https://example.com/team', 2, 'https://example.com/about', 'pending'),
     ('session-123', 'https://example.com/contact', 'https://example.com/contact', 2, 'https://example.com/about', 'pending'),
     ('session-123', 'https://example.com/careers', 'https://example.com/careers', 2, 'https://example.com/about', 'pending')
   ON CONFLICT (session_id, normalized_url) DO NOTHING  -- Ignores duplicates!
   ```

5. **Check if max pages reached:**
   ```sql
   IF pages_crawled >= max_pages THEN
     UPDATE crawl_sessions
     SET status = 'completed', completed_at = NOW()
     WHERE id = 'session-123'
   ```

**Response:**
```json
{
  "success": true,
  "data": {
    "pagesProcessed": 25,
    "maxPages": 1000,
    "linksEnqueued": 3
  }
}
```

---

### **Step 5: Loop Back to Step 2**

Python immediately requests the next URL and repeats the cycle:
```
Get Next URL → Crawl → Submit → Get Next URL → Crawl → Submit → ...
```

**Loop continues until:**
- ✅ Queue is empty (no more pending URLs)
- ✅ Max pages reached
- ❌ Session marked as 'stopped' or 'error'

---

## 📊 Database Schema

### **crawl_queue**
```sql
CREATE TABLE crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  status TEXT DEFAULT 'pending',  -- 'pending' | 'processing' | 'completed' | 'failed'
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE (session_id, normalized_url)  -- Prevents duplicate URLs!
);

CREATE INDEX idx_queue_pending 
ON crawl_queue (session_id, status, depth, created_at);
```

### **crawl_sessions**
```sql
CREATE TABLE crawl_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id TEXT NOT NULL,
  start_url TEXT NOT NULL,
  status TEXT DEFAULT 'crawling',  -- 'crawling' | 'completed' | 'stopped' | 'error'
  pages_crawled INTEGER DEFAULT 0,
  max_pages INTEGER DEFAULT 100,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  errors TEXT[]
);
```

---

## 🎯 Key Features

### **1. Depth Control**
- Each URL has a `depth` value (0 = homepage, 1 = first level, etc.)
- Backend only enqueues links if `currentDepth < maxDepth`
- **Minimum maxDepth: 5** (configurable up to 20)

### **2. Duplicate Prevention**
- Database has `UNIQUE (session_id, normalized_url)` constraint
- If Python discovers the same URL twice, `INSERT ... ON CONFLICT DO NOTHING` ignores it
- No duplicate crawls!

### **3. Crash Recovery**
- If Python worker crashes mid-crawl, URLs stay in 'processing' state
- When Python restarts and calls `/next`, backend automatically resets stuck URLs:
  ```sql
  UPDATE crawl_queue
  SET status = 'pending'
  WHERE status = 'processing' AND updated_at < NOW() - 60 seconds
  ```
- Crawl resumes from where it left off!

### **4. Breadth-First Crawling**
- Queue is ordered by `depth ASC, created_at ASC`
- Homepage (depth 0) crawled first
- All depth-1 pages crawled before any depth-2 pages
- Ensures important pages are crawled first

---

## 🚀 Usage

### **Setup**

1. **Update PYTHON_DB_WORKER.py configuration:**
   ```python
   BACKEND_URL = "https://your-project.supabase.co/functions/v1/make-server-4180e2ca"
   ANON_KEY = "your-supabase-anon-key"
   ```

2. **Install Python dependencies:**
   ```bash
   pip install requests beautifulsoup4 lxml
   ```

### **Run Crawler**

```bash
# Basic usage
python PYTHON_DB_WORKER.py my-project https://example.com

# With options
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 1000 --max-depth 5

# Large site
python PYTHON_DB_WORKER.py big-site https://bigsiteto.com --max-pages 10000 --max-depth 10
```

### **Monitor Progress**

The worker prints live stats every 10 pages:
```
📊 STATS: Pending: 245 | Completed: 50 | Failed: 2 | Total: 297
```

---

## 🔧 Backend API Reference

### **1. Initialize Crawl**
```http
POST /projects/:projectId/crawl/db-init
Content-Type: application/json

{
  "startUrl": "https://example.com",
  "maxPages": 1000,
  "maxDepth": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sessionId": "uuid-here",
    "projectId": "my-project",
    "maxPages": 1000,
    "maxDepth": 5
  }
}
```

---

### **2. Get Next URL**
```http
POST /crawl/sessions/:sessionId/next
```

**Response (URL available):**
```json
{
  "success": true,
  "data": {
    "taskId": "uuid",
    "url": "https://example.com/page",
    "depth": 2,
    "parentUrl": "https://example.com"
  }
}
```

**Response (queue empty):**
```json
{
  "success": true,
  "data": null,
  "message": "No more URLs to crawl"
}
```

---

### **3. Submit Results**
```http
POST /crawl/sessions/:sessionId/submit
Content-Type: application/json

{
  "taskId": "uuid",
  "url": "https://example.com/page",
  "title": "Page Title",
  "content": "Page content...",
  "links": ["https://example.com/link1", "https://example.com/link2"],
  "status": 200,
  "maxDepth": 5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "pagesProcessed": 150,
    "maxPages": 1000,
    "linksEnqueued": 2
  }
}
```

---

### **4. Get Stats**
```http
GET /crawl/sessions/:sessionId/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "pending": 245,
    "processing": 1,
    "completed": 150,
    "failed": 3,
    "total": 399,
    "sessionStatus": "crawling",
    "pagesCrawled": 150,
    "maxPages": 1000
  }
}
```

---

## ⚡ Performance

- **TypeScript crawler** = Best for 10-1000 pages (auto-crawl in Edge Functions)
- **Python worker** = Best for 1K-100K+ pages (runs on your machine, no timeouts)

### **Why Python for Large Sites?**

1. **No timeouts** - Edge Functions have 60s limit, Python runs indefinitely
2. **Better control** - Run on your machine, pause/resume anytime
3. **Parallel workers** - Run multiple Python workers for same session (coming soon)
4. **JS rendering** - Can add Selenium/Playwright support easily

---

## 🐛 Debugging

### **Check Queue Status**
```bash
# See what's in the queue
curl https://your-project.supabase.co/functions/v1/make-server-4180e2ca/crawl/sessions/SESSION_ID/stats \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### **Common Issues**

**1. "No more URLs to crawl" after 1 page**
- Check `maxDepth` - if set to 0, no links are enqueued
- Ensure links are internal (same domain)

**2. URLs stuck in 'processing'**
- Backend auto-resets after 60 seconds
- Or manually reset:
  ```sql
  UPDATE crawl_queue
  SET status = 'pending'
  WHERE session_id = 'your-session-id' AND status = 'processing'
  ```

**3. Duplicate URLs being crawled**
- Check `normalized_url` - ensure normalization is consistent
- Database constraint should prevent this

---

## 🎉 Summary

**You create a project → Add URL → Start crawl**

**What happens:**

1. ✅ Python sends homepage to backend
2. ✅ Backend creates session and queues homepage
3. ✅ Python enters loop:
   - Request next URL
   - Crawl it
   - Send links back
   - Backend enqueues links (if depth < maxDepth)
   - Repeat!
4. ✅ Loop continues until queue is empty or max pages reached
5. ✅ All data is in your Supabase database

**Benefits:**
- ✅ Crash-resistant (queue persists in DB)
- ✅ Resumable (restart Python worker anytime)
- ✅ No duplicates (DB constraint)
- ✅ Depth control (configurable 0-20)
- ✅ Scalable (can add multiple workers)

🚀 **Ready to crawl 100K+ pages!**

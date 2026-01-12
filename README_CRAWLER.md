# 🚀 Internal Link Analyzer - Crawler System

## 📖 Overview

You now have a **dual-crawler system** with two complementary approaches:

1. **TypeScript Auto-Crawl** - Fast, zero-setup, runs in Edge Functions (10-1000 pages)
2. **Python DB-First Queue** - Production-grade, resumable, unlimited pages (1K-100K+ pages)

Both share the same **database-driven queue architecture** with crash recovery, duplicate prevention, and depth control.

---

## 📚 Documentation Index

### **🎯 Start Here**
- **[HOW_IT_WORKS.md](./HOW_IT_WORKS.md)** - Complete explanation: "You create a project, add URL, start crawl... what happens next?"

### **🚀 Quick Setup**
- **[QUICK_START.md](./QUICK_START.md)** - Get Python worker running in 5 minutes

### **🔍 Choose Your Crawler**
- **[CRAWLER_COMPARISON.md](./CRAWLER_COMPARISON.md)** - Which crawler for which use case?

### **🏗️ Deep Technical**
- **[DATABASE_FIRST_ARCHITECTURE.md](./DATABASE_FIRST_ARCHITECTURE.md)** - Complete architecture, API reference, database schema

### **✅ What Was Built**
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - All changes, new endpoints, requirements checklist

---

## 🎯 Quick Decision Guide

### **I have a small site (< 1000 pages):**
→ Use **TypeScript Auto-Crawl**
```typescript
// In your React dashboard, click "Start New Crawl"
// Or via code:
await api.startAutoCrawl(projectId, 1000);
```

### **I have a large site (1000+ pages):**
→ Use **Python DB-First Queue**
```bash
# One-time setup
pip install requests beautifulsoup4 lxml

# Configure PYTHON_DB_WORKER.py (lines 41-42)
BACKEND_URL = "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca"
ANON_KEY = "your-anon-key"

# Run
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 10000 --max-depth 5
```

---

## 🗂️ File Structure

### **Documentation**
```
/HOW_IT_WORKS.md                    - Complete flow explanation
/QUICK_START.md                     - Python setup guide
/CRAWLER_COMPARISON.md              - Feature comparison
/DATABASE_FIRST_ARCHITECTURE.md     - Technical deep-dive
/IMPLEMENTATION_SUMMARY.md          - What was implemented
/README_CRAWLER.md                  - This file
```

### **Code**
```
/PYTHON_DB_WORKER.py                - Python crawler worker
/supabase/functions/server/
  ├── index.tsx                     - API endpoints (4 new DB-First endpoints)
  ├── web_crawler.tsx               - TypeScript crawler
  ├── queue_manager.tsx             - Queue operations
  └── crawler_api.tsx               - Helper functions
```

---

## 🔧 Backend Endpoints

### **TypeScript Auto-Crawl**
```http
POST /projects/:projectId/crawl/auto
{
  "maxPages": 1000,
  "enableJsRendering": false,
  "discoverSitemap": true
}
```

### **Python DB-First Queue**

#### **1. Initialize Session**
```http
POST /projects/:projectId/crawl/db-init
{
  "startUrl": "https://example.com",
  "maxPages": 1000,
  "maxDepth": 5
}
```

#### **2. Get Next URL**
```http
POST /crawl/sessions/:sessionId/next
```

#### **3. Submit Results**
```http
POST /crawl/sessions/:sessionId/submit
{
  "taskId": "uuid",
  "url": "https://example.com/page",
  "title": "Page Title",
  "content": "...",
  "links": ["https://example.com/link1", ...],
  "maxDepth": 5
}
```

#### **4. Get Stats**
```http
GET /crawl/sessions/:sessionId/stats
```

---

## 📊 Database Schema

### **crawl_sessions**
```sql
CREATE TABLE crawl_sessions (
  id UUID PRIMARY KEY,
  project_id TEXT NOT NULL,
  start_url TEXT,
  status TEXT DEFAULT 'crawling',  -- 'crawling' | 'completed' | 'stopped'
  pages_crawled INTEGER DEFAULT 0,
  max_pages INTEGER DEFAULT 100,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

### **crawl_queue**
```sql
CREATE TABLE crawl_queue (
  id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  status TEXT DEFAULT 'pending',  -- 'pending' | 'processing' | 'completed' | 'failed'
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE (session_id, normalized_url)  -- Prevents duplicates
);

CREATE INDEX idx_queue_pending 
ON crawl_queue (session_id, status, depth, created_at);
```

### **pages**
```sql
CREATE TABLE pages (
  id UUID PRIMARY KEY,
  project_id TEXT NOT NULL,
  session_id UUID,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  title TEXT,
  content TEXT,
  internal_links TEXT[],
  status_code INTEGER,
  depth INTEGER DEFAULT 0,
  crawled_at TIMESTAMP DEFAULT NOW()
);
```

---

## ✅ Key Features

### **🛡️ Crash Recovery**
- URLs stuck in 'processing' > 60s are auto-reset to 'pending'
- Python worker can restart anytime and resume from where it left off

### **🚫 Duplicate Prevention**
- Database unique constraint: `(session_id, normalized_url)`
- Same URL discovered multiple times? Only crawled once!

### **📏 Depth Control**
- Each URL has a depth value (0 = homepage, 1 = first level, etc.)
- Backend only enqueues links if `currentDepth < maxDepth`
- Configurable: 0-20 (default: 5 for Python, 20 for TypeScript)

### **🔄 Breadth-First Crawling**
- Queue ordered by `depth ASC, created_at ASC`
- All depth-0 pages crawled before any depth-1
- Ensures important pages are crawled first

### **⏸️ Pause & Resume**
- Python worker: Press `Ctrl+C` to stop
- Restart anytime with same session ID (future feature)
- TypeScript crawler: Automatic batching handles edge function timeouts

---

## 🎯 Complete Flow Example

### **You run:**
```bash
python PYTHON_DB_WORKER.py my-site https://example.com --max-pages 1000 --max-depth 5
```

### **What happens:**

1. **Initialize (Python → Backend):**
   - Python sends homepage to backend
   - Backend creates session, enqueues homepage

2. **Loop starts (Python):**
   ```
   while True:
       task = backend.get_next_url()
       if not task: break
       
       title, content, links = crawl_page(task.url)
       backend.submit_results(title, content, links)
   ```

3. **First iteration:**
   - Backend returns: `{ url: "https://example.com", depth: 0 }`
   - Python crawls homepage, finds 20 links
   - Python sends results to backend
   - Backend saves page, enqueues 20 links at depth 1

4. **Second iteration:**
   - Backend returns: `{ url: "https://example.com/about", depth: 1 }`
   - Python crawls about page, finds 10 links
   - Backend enqueues 10 links at depth 2

5. **Continues until:**
   - Queue is empty
   - Max pages reached (1000)
   - Max depth reached (5)

6. **Result:**
   - 1000 pages in database
   - All links discovered (maybe 5000+ URLs in queue)
   - Only 1000 crawled (hit max_pages limit)

---

## 🔍 Monitoring Progress

### **Python Worker (Terminal Output):**
```
📄 [1] Depth 0: https://example.com
  ✅ Title: Example Homepage
  📋 Found 20 internal links
  💾 Saved to DB (1/1000 pages)
  📋 Enqueued 20 new links

📄 [2] Depth 1: https://example.com/about
  ✅ Title: About Us
  📋 Found 10 internal links
  💾 Saved to DB (2/1000 pages)
  📋 Enqueued 10 new links

📊 STATS: Pending: 28 | Completed: 2 | Failed: 0 | Total: 30
```

### **TypeScript Auto-Crawl (Browser Console):**
```
[Session abc] ===== BATCH 1 START =====
[Session abc] Connectivity test passed!
[Session abc] WebCrawler created successfully
✅ Crawled 1/1000: https://example.com
📋 Enqueued 20 new links
[Session abc] ===== BATCH 1 COMPLETE =====
```

### **Database Query:**
```sql
-- Check progress
SELECT status, COUNT(*) 
FROM crawl_queue 
WHERE session_id = 'your-session-id' 
GROUP BY status;

-- Results:
-- pending: 150
-- processing: 1
-- completed: 50
-- failed: 2
```

---

## 🐛 Troubleshooting

### **TypeScript Auto-Crawl**

**Problem:** Stops after 2 pages
- ✅ **Fixed!** Changed `seedOnly: false`, added batch loop, reset stuck URLs

**Problem:** Timeout errors
- Use Python worker instead (no timeouts)

**Problem:** Max pages capped at 1000
- This is by design (Edge Function limits)
- Use Python for larger sites

---

### **Python DB-First**

**Problem:** "Failed to initialize"
- Check `BACKEND_URL` and `ANON_KEY` in Python file
- Ensure `crawl_queue` table exists (run `/setup-pro-crawler`)

**Problem:** "No module named 'bs4'"
```bash
pip install beautifulsoup4
```

**Problem:** Crawl stops after 1 page
- Check `maxDepth` (must be >= 1)
- Verify site has internal links

**Problem:** URLs getting stuck in 'processing'
- Auto-recovery after 60 seconds
- Or manually reset:
  ```sql
  UPDATE crawl_queue 
  SET status = 'pending' 
  WHERE session_id = 'xxx' AND status = 'processing'
  ```

---

## 📈 Performance Tips

### **Small Sites (< 100 pages):**
- Use TypeScript Auto-Crawl
- Set `maxPages: 100`, `maxDepth: 3`

### **Medium Sites (100-1000 pages):**
- Use TypeScript Auto-Crawl
- Set `maxPages: 1000`, `maxDepth: 5`

### **Large Sites (1K-10K pages):**
- Use Python DB-First Queue
- Set `maxPages: 10000`, `maxDepth: 8`
- Run overnight

### **Massive Sites (10K-100K+ pages):**
- Use Python DB-First Queue
- Set `maxPages: 100000`, `maxDepth: 10`
- Use `screen` or `tmux` to keep it running
- May take 1-3 days

---

## 🎉 Success Checklist

After implementation, you should have:

### **✅ Database Tables**
- `crawl_sessions` - Session tracking
- `crawl_queue` - URL queue with status
- `pages` - Crawled page data

### **✅ Backend Endpoints**
- `/crawl/auto` - TypeScript auto-crawl
- `/crawl/db-init` - Initialize Python session
- `/crawl/sessions/:id/next` - Get next URL
- `/crawl/sessions/:id/submit` - Submit results
- `/crawl/sessions/:id/stats` - Get stats

### **✅ Files**
- `PYTHON_DB_WORKER.py` - Python worker
- `web_crawler.tsx` - TypeScript crawler
- `queue_manager.tsx` - Queue operations
- Complete documentation suite

### **✅ Features**
- Crash recovery (auto-reset stuck URLs)
- Duplicate prevention (unique constraint)
- Depth control (configurable 0-20)
- Breadth-first crawling
- Pause/resume (Python only)
- Live progress monitoring

---

## 🚀 Next Steps

1. **Test TypeScript Auto-Crawl:**
   - Create a test project
   - Click "Start New Crawl"
   - Verify it crawls multiple pages

2. **Setup Python Worker:**
   - Follow `QUICK_START.md`
   - Test with `--max-pages 10`
   - Verify database updates

3. **Read Architecture Docs:**
   - `HOW_IT_WORKS.md` for complete flow
   - `DATABASE_FIRST_ARCHITECTURE.md` for technical details

4. **Choose Your Crawler:**
   - See `CRAWLER_COMPARISON.md`
   - Pick based on site size

5. **Start Crawling!**
   - Small sites → TypeScript
   - Large sites → Python
   - Both save to same database!

---

## 📞 Support

### **Check Documentation:**
- `HOW_IT_WORKS.md` - Flow explanation
- `QUICK_START.md` - Setup guide
- `CRAWLER_COMPARISON.md` - Feature comparison
- `DATABASE_FIRST_ARCHITECTURE.md` - Technical reference
- `IMPLEMENTATION_SUMMARY.md` - What was built

### **Common Questions:**
- "Which crawler should I use?" → See `CRAWLER_COMPARISON.md`
- "How does it work?" → See `HOW_IT_WORKS.md`
- "How to setup Python?" → See `QUICK_START.md`
- "What are the API endpoints?" → See `DATABASE_FIRST_ARCHITECTURE.md`

---

## 🎯 Summary

**You asked:** "Tell me how it works, I create a project, add URL, start crawl. What happens next?"

**Answer:** You now have TWO options:

1. **TypeScript Auto-Crawl** (Easy):
   - Click "Start New Crawl" → Automatic crawling → Done!
   - Best for sites < 1000 pages

2. **Python DB-First Queue** (Powerful):
   - Run Python script → It requests URLs from backend → Crawls them → Sends results back → Backend enqueues discovered links → Loop continues
   - Best for sites 1000+ pages

Both use the same **database-driven queue** with crash recovery, duplicate prevention, and depth control.

**Read `HOW_IT_WORKS.md` for the complete step-by-step explanation!**

🚀 **Happy Crawling!**

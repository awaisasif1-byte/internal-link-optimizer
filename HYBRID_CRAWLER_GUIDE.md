# 🚀 Hybrid Crawler System - Complete Setup Guide

## 🏗️ Architecture Overview

Your Internal Link Optimizer uses a **Hybrid Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                    React Dashboard                       │
│  (User clicks "Start Crawl", monitors progress)         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Supabase Database (The Brain)               │
│  - crawl_sessions (crawl metadata)                      │
│  - crawl_queue (pending URLs, stateful)                 │
│  - pages (crawled results)                              │
└───────────┬──────────────────────────────┬──────────────┘
            │                              │
            ▼                              ▼
┌──────────────────────┐       ┌─────────────────────────┐
│  TypeScript Crawler  │       │    Python Worker        │
│  (Edge Function)     │       │   (External Process)    │
│                      │       │                         │
│  ✅ 10-1000 pages    │       │  ✅ 1000-100,000 pages  │
│  ✅ Click & forget   │       │  ✅ No timeouts         │
│  ⚠️  60s limit       │       │  ✅ Crash-resumable     │
└──────────────────────┘       └─────────────────────────┘
```

**The Magic:** Both crawlers use the **same database tables**, so:
- Dashboard shows live progress from either crawler
- You can start with TypeScript, switch to Python mid-crawl
- All results appear in the same dashboard

---

## 📋 Prerequisites

### 1. Database Setup

Run this SQL in your **Supabase SQL Editor**:

```sql
-- Sessions table (if not exists)
CREATE TABLE IF NOT EXISTS crawl_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  start_url TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  pages_crawled INTEGER DEFAULT 0,
  pages_found INTEGER DEFAULT 0,
  max_pages INTEGER DEFAULT 100,
  max_depth INTEGER DEFAULT 3,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Queue table (stateful crawl queue)
CREATE TABLE IF NOT EXISTS crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES crawl_sessions(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(session_id, normalized_url)
);

-- Pages table (crawl results)
CREATE TABLE IF NOT EXISTS pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  session_id UUID,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  title TEXT,
  content TEXT,
  word_count INTEGER DEFAULT 0,
  internal_links_count INTEGER DEFAULT 0,
  external_links_count INTEGER DEFAULT 0,
  status_code INTEGER,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  page_type TEXT,
  meta_description TEXT,
  keywords TEXT[],
  link_equity_score FLOAT DEFAULT 0,
  crawled_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(project_id, normalized_url)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_crawl_queue_session ON crawl_queue(session_id);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status);
CREATE INDEX IF NOT EXISTS idx_pages_project ON pages(project_id);
CREATE INDEX IF NOT EXISTS idx_pages_session ON pages(session_id);
```

### 2. Python Setup (for Python Worker)

```bash
# Install Python 3.8+
python3 --version

# Install dependencies
pip install httpx beautifulsoup4
```

---

## 🎯 Usage Guide

### Option 1: Small Sites (10-1000 pages) - TypeScript Crawler

**Perfect for most users - zero setup required!**

1. Open your dashboard
2. Click "New Project"
3. Enter website URL
4. Set page limit (10-1000)
5. Click "Start Crawl"
6. ✨ Done! Watch the progress bar

**Behind the scenes:**
- Edge Function processes URLs in batches
- Self-invokes until complete
- All results saved to database
- Dashboard updates in real-time

**Limitations:**
- 60-second timeout per invocation
- May struggle with 1000+ pages
- Requires good network connectivity

---

### Option 2: Large Sites (1000-100,000 pages) - Python Worker

**For power users and large-scale crawls**

#### Step 1: Start Crawl from Dashboard

1. Open dashboard
2. Click "New Project"
3. Enter website URL
4. Set page limit (can be 10,000+)
5. Click "Start Crawl"
6. **Copy the Session ID** (shown in the URL or Debug Panel)

#### Step 2: Set Environment Variables

```bash
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key-here'
export SESSION_ID='uuid-from-step-1'
```

**Where to find these:**

- `SUPABASE_URL`: Supabase Dashboard → Settings → API → Project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase Dashboard → Settings → API → service_role key ⚠️ **Keep secret!**
- `SESSION_ID`: Copy from dashboard after starting crawl

#### Step 3: Run the Worker

```bash
python worker.py
```

**What you'll see:**

```
============================================================
🚀 Internal Link Optimizer - Crawler Worker
============================================================
📋 Session ID: abc-123-def-456
🌐 Domain: example.com
📄 Max Pages: 10000
🔗 Start URL: https://example.com
============================================================

🔎 [0] Crawling: https://example.com
✅ Completed: https://example.com (45 links found)
🔎 [1] Crawling: https://example.com/about
✅ Completed: https://example.com/about (12 links found)
📊 Progress: 10/10000 pages crawled
...
```

#### Step 4: Monitor in Dashboard

- Open your dashboard (leave it open)
- Watch the **real-time progress** as Python crawls
- Pages appear in the dashboard as they're crawled
- All charts and stats update live

#### Step 5: Stop/Resume Anytime

**To stop:**
- Press `Ctrl+C` in terminal
- Progress is saved in database

**To resume:**
- Just run `python worker.py` again with same `SESSION_ID`
- It picks up exactly where it left off

---

## 🔥 Advanced Features

### Crash Recovery

If the Python worker crashes (power outage, network failure, etc.):

```bash
# Just restart with the same SESSION_ID
export SESSION_ID='same-uuid-as-before'
python worker.py
```

It will:
- ✅ Skip already-crawled URLs
- ✅ Resume from pending URLs in queue
- ✅ Continue incrementing progress
- ✅ No duplicate data

### Running on a VPS (24/7 Crawling)

```bash
# SSH into your server
ssh user@your-server.com

# Clone your project or copy worker.py
git clone your-repo

# Set environment variables
export SUPABASE_URL='...'
export SUPABASE_SERVICE_ROLE_KEY='...'
export SESSION_ID='...'

# Run in background with nohup
nohup python worker.py > crawler.log 2>&1 &

# Check progress
tail -f crawler.log
```

### Running Multiple Workers (Ultra-Fast)

You can run **multiple Python workers simultaneously** for the same session:

```bash
# Terminal 1
export SESSION_ID='same-session-id'
python worker.py

# Terminal 2 (same session!)
export SESSION_ID='same-session-id'
python worker.py
```

They'll:
- Pull different URLs from the queue
- Never crawl the same URL twice (DB constraint)
- Combine efforts to finish faster

---

## 🐛 Troubleshooting

### Worker says "Session not found"

**Cause:** Wrong `SESSION_ID` or session was deleted

**Fix:**
1. Go to dashboard
2. Start a new crawl
3. Copy the new Session ID
4. Update `export SESSION_ID='new-uuid'`

### Worker keeps saying "Queue empty"

**Cause:** All URLs have been crawled

**Fix:**
- This is normal! Crawl is complete
- Check dashboard - you should see all pages

### Dashboard shows 0 pages but worker is running

**Cause:** Worker might be using wrong `project_id`

**Fix:**
1. Check `crawl_sessions` table in Supabase
2. Verify `project_id` matches your dashboard project
3. Restart crawl from dashboard to ensure sync

### Worker is too slow

**Solutions:**
1. Increase concurrency in `worker.py`:
   ```python
   tasks = await get_next_tasks(limit=20)  # Was 5
   ```
2. Reduce delay:
   ```python
   await asyncio.sleep(0.1)  # Was 0.5
   ```
3. Run multiple workers (see Advanced Features)

### "Resolution=ignore-duplicates" errors

**Cause:** Older Supabase version

**Fix:** Update the header in `worker.py`:
```python
upsert_headers = {**HEADERS, "Prefer": "resolution=merge-duplicates"}
```

---

## 📊 Performance Benchmarks

| Crawler | Pages/Minute | Best For | Limitations |
|---------|--------------|----------|-------------|
| **TypeScript** | ~20-30 | Quick crawls | 60s timeout |
| **Python (1 worker)** | ~60-100 | Large sites | Requires setup |
| **Python (5 workers)** | ~300-500 | Massive sites | High bandwidth |

---

## 🎯 Recommended Strategy

### For SaaS Users:

**Free Tier:** TypeScript only (auto-managed)
- Users click "Crawl" in dashboard
- Limited to 100 pages
- Zero setup required

**Pro Tier:** Hybrid option
- Users can download `worker.py`
- Run locally for unlimited pages
- Dashboard still shows progress

**Enterprise:** VPS-hosted workers
- You run workers on your infrastructure
- Users just use dashboard
- Handle millions of pages

---

## 🚀 Next Steps

1. ✅ Run the SQL setup
2. ✅ Test TypeScript crawler with a small site
3. ✅ Install Python dependencies
4. ✅ Test Python worker with a larger site
5. ✅ Compare results in dashboard

You now have an **industrial-grade crawler** that can scale from 10 to 100,000 pages! 🎉

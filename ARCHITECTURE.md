# 🏗️ Hybrid Crawler Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         REACT DASHBOARD                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐               │
│  │ New Project  │  │ Start Crawl  │  │ View Stats  │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘               │
│         │                 │                  │                       │
└─────────┼─────────────────┼──────────────────┼───────────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SUPABASE DATABASE (The Brain)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐               │
│  │   projects   │  │crawl_sessions│  │crawl_queue  │               │
│  │  (websites)  │  │  (tracking)  │  │  (pending)  │               │
│  └──────────────┘  └──────────────┘  └─────────────┘               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐               │
│  │    pages     │  │internal_links│  │opportunities│               │
│  │  (results)   │  │ (graph data) │  │(suggestions)│               │
│  └──────────────┘  └──────────────┘  └─────────────┘               │
└──────────┬────────────────────────────────┬──────────────────────────┘
           │                                │
           ▼                                ▼
┌────────────────────────┐      ┌──────────────────────────┐
│  TYPESCRIPT CRAWLER    │      │    PYTHON WORKER         │
│  (Edge Function)       │      │    (External Process)    │
├────────────────────────┤      ├──────────────────────────┤
│ ✅ 10-1000 pages       │      │ ✅ 1000-100,000 pages    │
│ ✅ Click & forget      │      │ ✅ No timeout limits     │
│ ✅ Zero setup          │      │ ✅ Runs for days         │
│ ⚠️  60s per invocation │      │ ⚠️  Requires Python      │
└────────────────────────┘      └──────────────────────────┘
```

## Data Flow

### Starting a Crawl (User Action)

```
User clicks "Start Crawl"
    ↓
Dashboard creates:
    1. crawl_session record
    2. Initial crawl_queue entry (start URL)
    ↓
Database now has:
    - session_id: abc-123
    - crawl_queue: [{ url: "https://example.com", status: "pending" }]
```

### TypeScript Crawler Flow

```
Edge Function invoked
    ↓
1. SELECT * FROM crawl_queue WHERE status='pending' LIMIT 10
    ↓
2. For each URL:
    - Fetch HTML
    - Parse content
    - Extract links
    - Save to pages table
    - Add new links to crawl_queue
    - Mark as 'completed'
    ↓
3. Self-invoke if queue not empty
    ↓
Repeat until queue empty or max_pages reached
```

### Python Worker Flow

```
python worker.py starts
    ↓
1. SELECT * FROM crawl_queue WHERE status='pending' LIMIT 5
    ↓
2. For each URL:
    - Update status to 'processing'
    - Fetch HTML
    - Parse content
    - Extract links
    - Save to pages table
    - Add new links to crawl_queue
    - Mark as 'completed'
    ↓
3. Loop forever (no timeout!)
    ↓
Stops when queue empty or Ctrl+C
```

## Crash Recovery

### What Happens When It Crashes

```
Crawler running...
Page 1: ✅ Saved to DB
Page 2: ✅ Saved to DB
Page 3: ✅ Saved to DB
Page 4: ⚡ CRASH!
```

**TypeScript:**
```
crawl_queue table still has:
- Page 4: status = 'pending' ❌ (was processing)
- Page 5-1000: status = 'pending' ✅

Just restart crawl → picks up from Page 4
```

**Python:**
```
crawl_queue table still has:
- Page 4: status = 'processing' ⚠️
- Page 5-1000: status = 'pending' ✅

Run: python worker.py
    ↓
Skips 'processing' (will timeout after 1 hour)
Starts with Page 5 ✅
```

## Real-Time Updates

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Python Worker  │         │    Database     │         │   Dashboard     │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │ 1. Crawl page            │                           │
         │────────────────────────→│                           │
         │                           │                           │
         │ 2. Save to pages table   │                           │
         │────────────────────────→│                           │
         │                           │                           │
         │                           │ 3. Dashboard polls        │
         │                           │←──────────────────────────│
         │                           │                           │
         │                           │ 4. Return new pages       │
         │                           │──────────────────────────→│
         │                           │                           │
         │                           │                  ✨ User sees update!
```

## Parallel Processing

### Multiple Python Workers

```
Worker 1                    Database                    Worker 2
   ↓                           ↓                           ↓
GET pending URL 1          crawl_queue              GET pending URL 2
   ↓                           ↓                           ↓
Process URL 1             [URL 1: processing]        Process URL 2
   ↓                      [URL 2: processing]             ↓
Save results              [URL 3: pending]           Save results
   ↓                      [URL 4: pending]                ↓
COMPLETE                  [URL 1: completed]         COMPLETE
   ↓                      [URL 2: completed]              ↓
GET URL 3                 [URL 3: processing] ←───── GET URL 4
   ↓                      [URL 4: processing]             ↓
```

**No conflicts!** Database ensures each URL is only fetched once via:
- `UNIQUE(session_id, normalized_url)` constraint
- Atomic status updates

## Database Tables Explained

### crawl_queue (The To-Do List)

| Column | Purpose | Example |
|--------|---------|---------|
| `session_id` | Which crawl this belongs to | `abc-123` |
| `url` | What to crawl | `https://example.com/page` |
| `normalized_url` | Deduplicated version | `https://example.com/page` |
| `depth` | How many clicks from homepage | `2` |
| `parent_url` | Where we found this link | `https://example.com` |
| `status` | Current state | `pending`, `processing`, `completed`, `failed` |

### pages (The Results)

| Column | Purpose | Example |
|--------|---------|---------|
| `project_id` | Which website | `proj-456` |
| `url` | Page URL | `https://example.com/about` |
| `title` | Page title | `About Us` |
| `content` | Page text | `We are a company...` |
| `word_count` | Content length | `350` |
| `internal_links_count` | Links found | `25` |
| `page_type` | Classified type | `informational` |
| `keywords` | Extracted keywords | `["company", "team"]` |
| `link_equity_score` | SEO metric | `75.5` |

## Choosing the Right Crawler

```
                    TypeScript          Python
                    ──────────          ──────
Pages needed        < 1000              > 1000
Setup time          0 minutes           5 minutes
Infrastructure      None                Local/VPS
Speed              20-30 pages/min     60-100 pages/min
Timeout limit       Yes (60s)           No
Dashboard control   ✅ Full             ✅ Full
Resume after crash  ✅ Yes              ✅ Yes
Multiple workers    ❌ No               ✅ Yes
Cost                Supabase only       Supabase + compute
```

## Decision Tree

```
Need to crawl a website?
    ↓
    ├─ Less than 1000 pages?
    │   ↓
    │   YES → Use TypeScript crawler
    │         (Click "Start Crawl" in dashboard)
    │
    └─ More than 1000 pages?
        ↓
        YES → Use Python worker
              1. Click "Start Crawl" in dashboard
              2. Copy session ID
              3. Run: python worker.py
```

## Hybrid in Action

### Scenario: Crawling 5000 page site

**Step 1: Start in Dashboard**
```
User: Create project → Click "Start Crawl"
DB: session_id = abc-123
    crawl_queue = [homepage]
```

**Step 2: TypeScript tries (optional)**
```
TypeScript: Processes 100 pages
            60s timeout hits
            Stops (100 pages saved ✅)
DB: pages = 100
    crawl_queue = 4900 pending URLs
```

**Step 3: Python takes over**
```
Terminal: python worker.py
Python: Picks up remaining 4900 URLs
        Runs for 2 hours (no timeout!)
        Completes all 5000 pages ✅
```

**Result:** Dashboard shows all 5000 pages! 🎉

---

## Summary

**The Brain:** Database (Supabase)
**The Muscle:** TypeScript OR Python (your choice)
**The Interface:** React Dashboard (always)

Both crawlers speak the same language (database tables), so they work together seamlessly!

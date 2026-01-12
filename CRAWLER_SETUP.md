# 🚀 Scalable Web Crawler - Setup Instructions

Your crawler has been upgraded to a **production-ready, DB-backed queue system** using Gemini's clean architecture!

## ✅ What Changed

### Old System (Messy)
- KV-based queue (complex, hard to debug)
- Hardcoded limits
- No user control over crawl settings
- Multiple confusing crawl endpoints

### New System (Clean)
- **DB-backed queue** - Resume from anywhere
- **User-configurable limits** - 10 to 1000 pages via slider
- **Single unified crawler** - One clean WebCrawler class
- **Inline semantic analysis** - Saves + analyzes pages together
- **Better error handling** - No unnecessary console logs

---

## 🛠️ Setup (ONE-TIME ONLY)

### Step 1: Run SQL Setup

1. Open your **Supabase Dashboard**
2. Go to **SQL Editor**
3. Copy and paste this SQL:

```sql
-- Create crawl_queue table
CREATE TABLE IF NOT EXISTS crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER NOT NULL DEFAULT 0,
  parent_url TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_url_per_session UNIQUE (session_id, normalized_url)
);

CREATE INDEX IF NOT EXISTS idx_crawl_queue_session_status ON crawl_queue(session_id, status);
CREATE INDEX IF NOT EXISTS idx_crawl_queue_depth ON crawl_queue(depth);

CREATE OR REPLACE FUNCTION increment_pages_crawled(session_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE crawl_sessions
  SET pages_crawled = pages_crawled + 1,
      updated_at = NOW()
  WHERE id = session_id;
END;
$$ LANGUAGE plpgsql;

SELECT 'Setup complete!' AS status;
```

4. Click **RUN**
5. You should see: `Setup complete!`

---

## 🎯 How It Works Now

### Creating a New Project

1. Click **"New Project"** in the sidebar
2. Enter project name, description, and website URL
3. **Set crawl limit** using the slider (10-1000 pages)
4. Click **"Create"**
5. Crawler starts immediately!

### What Happens Behind the Scenes

1. **Session Created** - A new crawl session is created in the DB
2. **Queue Initialized** - Homepage is added to the queue
3. **Crawler Starts** - WebCrawler fetches URLs from queue one by one
4. **Pages Saved** - Each page is saved + analyzed immediately
5. **New Links Discovered** - Internal links are added to the queue
6. **Progress Updates** - Database tracks `pages_crawled` counter
7. **Completion** - When queue is empty or max pages reached, crawl completes

---

## 📊 Architecture

```
┌─────────────────┐
│  User Creates   │
│    Project      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Crawl Session   │  ← Stores: max_pages, pages_crawled, status
│    Created      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Queue Table    │  ← URLs to crawl (pending/processing/completed)
│   Initialized   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WebCrawler     │  ← Fetches next URL, crawls, saves, repeats
│   Processes     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Pages Saved    │  ← Upsert to avoid duplicates
│  & Analyzed     │  ← Extract keywords, entities, vectors
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Dashboard     │  ← Real-time progress updates
│    Updates      │
└─────────────────┘
```

---

## 🐛 Debugging

If crawl shows "0 pages":

1. **Check Supabase Edge Function Logs**
   - Dashboard → Edge Functions → Logs
   - Look for errors in `web_crawler.tsx`

2. **Check Database**
   ```sql
   -- See queue status
   SELECT status, COUNT(*) FROM crawl_queue GROUP BY status;
   
   -- See recent pages
   SELECT url, title, created_at FROM pages ORDER BY created_at DESC LIMIT 10;
   ```

3. **Common Issues**
   - **Table doesn't exist** → Run the SQL setup above
   - **Function not found** → Make sure `increment_pages_crawled` function exists
   - **Timeout** → Crawler stops after 50 pages per invocation (resumes automatically)

---

## 🚀 Next Steps

Your crawler is now production-ready and can:

✅ Crawl 1-1000 pages per project  
✅ Resume from any point if interrupted  
✅ Respect robots.txt  
✅ Extract semantic data (keywords, entities)  
✅ Show real-time progress  
✅ Handle duplicates gracefully  

**No more mess, just clean scalable crawling! 🎉**

---

## 💡 Tips

- **Start small** - Test with 10-50 pages first
- **Scale up** - Once confirmed working, try 500-1000 pages
- **Monitor logs** - Watch Supabase Edge Function logs during first crawl
- **Database constraints** - The unique constraint prevents duplicate URLs automatically

Enjoy your competitive SaaS tool! 🚀

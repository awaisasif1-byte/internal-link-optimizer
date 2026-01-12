# 🚀 PRODUCTION CRAWLER - 30 SECOND SETUP

## ⚡ QUICK SETUP (3 Steps)

### **Step 1: Copy the SQL**
The SQL is in the file `/CREATE_CRAWL_QUEUE_TABLE.sql` or copy this:

```sql
CREATE TABLE IF NOT EXISTS crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  priority INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_session_url UNIQUE(session_id, normalized_url)
);

CREATE INDEX IF NOT EXISTS idx_queue_session_status ON crawl_queue(session_id, status);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON crawl_queue(priority DESC, depth ASC);
```

### **Step 2: Open Supabase SQL Editor**
1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click **"SQL Editor"** in the left sidebar
4. Click **"New Query"**

### **Step 3: Paste and Run**
1. Paste the SQL from Step 1
2. Click **"RUN"** (or press Cmd/Ctrl + Enter)
3. You should see: ✅ "Success. No rows returned"

---

## ✅ DONE!

Now when you click **"Start New Crawl"** in your dashboard, the production crawler will work perfectly!

---

## 🎯 WHAT HAPPENS NEXT

When you start a crawl:
- ✅ Crawls up to 10,000 pages
- ✅ Processes 15 pages per batch
- ✅ Extracts comprehensive SEO data
- ✅ Saves incrementally (no data loss)
- ✅ Continues until complete

---

## 📊 VERIFY IT WORKED

After running the SQL, check your Supabase **Table Editor**:
- You should see a new table called **`crawl_queue`**
- It will have 0 rows (that's normal - it fills up when you crawl)

---

## 🐛 TROUBLESHOOTING

**Error: "relation crawl_sessions does not exist"**
- Run the main setup first: POST /make-server-4180e2ca/setup

**Error: "permission denied"**
- Make sure you're logged in as the project owner
- Try using the SQL Editor instead of the API

**Still having issues?**
- A modal will automatically popup when you click "Start New Crawl"
- The modal has a direct link to your SQL Editor
- Just copy/paste/run and you're done!

---

## 🎉 YOU'RE ALL SET!

The production crawler is ready. Just click "Start New Crawl" and watch it work! 🚀

# 🚀 Quick Start Guide - Database-First Crawler

## 📋 Prerequisites

1. **Python 3.7+** installed
2. **Supabase project** with tables created (run setup-pro-crawler first)
3. **Your Supabase credentials:**
   - Project URL: `https://YOUR_PROJECT.supabase.co`
   - Anon Key: `eyJhbG...` (get from Supabase dashboard)

---

## 🔧 Step 1: Setup Python Worker

### **1.1 Install Dependencies**
```bash
pip install requests beautifulsoup4 lxml
```

### **1.2 Configure Worker**

Open `PYTHON_DB_WORKER.py` and update these lines:

```python
# Line 41-42
BACKEND_URL = "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca"
ANON_KEY = "YOUR_SUPABASE_ANON_KEY"
```

**Where to find these:**
1. Go to your Supabase dashboard
2. Click on your project
3. Go to **Settings → API**
4. Copy:
   - **URL** → Use in `BACKEND_URL`
   - **anon / public** key → Use in `ANON_KEY`

---

## 🏃 Step 2: Run Your First Crawl

### **Basic Crawl (100 pages, depth 3)**
```bash
python PYTHON_DB_WORKER.py my-first-project https://example.com
```

### **Full Crawl (1000 pages, depth 5)**
```bash
python PYTHON_DB_WORKER.py my-project https://yoursite.com --max-pages 1000 --max-depth 5
```

### **Large Site (10K pages, depth 10)**
```bash
python PYTHON_DB_WORKER.py big-site https://largesite.com --max-pages 10000 --max-depth 10
```

---

## 📊 Step 3: Monitor Progress

### **In Terminal**
The worker shows live progress:
```
📄 [1] Depth 0: https://example.com
  🌐 Fetching: https://example.com
  ✅ Title: Example Domain
  📋 Found 25 internal links
  💾 Saved to DB (1/1000 pages)
  📋 Enqueued 25 new links

📄 [2] Depth 1: https://example.com/about
  ...

📊 STATS: Pending: 48 | Completed: 10 | Failed: 0 | Total: 58
```

### **In Your Frontend**
Go to your React dashboard and refresh - you'll see pages appearing in real-time!

---

## 🎯 Understanding the Output

```bash
📄 [25] Depth 2: https://example.com/blog/post-1
  🌐 Fetching: https://example.com/blog/post-1
  ✅ Title: Blog Post 1
  📋 Found 12 internal links
  💾 Saved to DB (25/1000 pages)
  📋 Enqueued 8 new links
```

- **[25]** = This is the 25th page crawled
- **Depth 2** = This page is 2 clicks away from homepage
- **Found 12 links** = Total links on the page
- **Enqueued 8** = Only 8 were new (4 were duplicates)

---

## 🛑 Stopping & Resuming

### **Stop Crawl**
Press `Ctrl+C` in terminal.

**What happens:**
- Python worker stops
- Database still has all the pending URLs
- Session status remains "crawling"

### **Resume Crawl**
Just run the same command again with the **same project ID**:

```bash
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 1000 --max-depth 5
```

**What happens:**
- Backend creates a NEW session
- Starts fresh from homepage

**Note:** To truly resume the SAME session, you'd need to modify the script to accept a `--session-id` parameter and skip the init step. (Feature can be added!)

---

## 📈 Advanced Usage

### **Test Small Site First**
```bash
# Crawl only 10 pages, depth 2 (for testing)
python PYTHON_DB_WORKER.py test-site https://example.com --max-pages 10 --max-depth 2
```

### **Depth Strategies**

| Depth | Use Case | Example |
|-------|----------|---------|
| 1-2 | Homepage + main sections | Company website with 5 pages |
| 3-5 | **Standard blogs/sites** | Most websites (recommended) |
| 6-10 | Large sites with categories | E-commerce, news sites |
| 10+ | Massive sites | Wikipedia, large marketplaces |

**⚠️ Warning:** Higher depth = exponentially more pages!
- Depth 3 might find 100 pages
- Depth 5 might find 1,000 pages
- Depth 10 might find 100,000+ pages

---

## 🔍 Checking Results

### **Option 1: Frontend Dashboard**
1. Open your React app
2. Navigate to the project
3. See all crawled pages, links, opportunities

### **Option 2: Direct API Call**
```bash
# Get all crawled pages
curl "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/projects/my-project/pages" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### **Option 3: Supabase Dashboard**
1. Go to Supabase → Table Editor
2. Open `pages` table
3. Filter by `project_id = 'my-project'`
4. See all crawled pages!

---

## ❓ FAQ

### **Q: Can I crawl multiple sites simultaneously?**
Yes! Just use different project IDs:
```bash
# Terminal 1
python PYTHON_DB_WORKER.py site-1 https://site1.com

# Terminal 2
python PYTHON_DB_WORKER.py site-2 https://site2.com
```

### **Q: What if the worker crashes?**
Restart it! The backend automatically resets URLs that were "stuck in processing" for > 60 seconds.

### **Q: Can I use the TypeScript auto-crawler instead?**
Yes! For sites under 1000 pages:
1. Go to your React dashboard
2. Click "Start New Crawl"
3. It uses `/crawl/auto` endpoint (TypeScript WebCrawler)

Use Python when:
- ✅ Site has 1000+ pages
- ✅ You need depth > 5
- ✅ You want to pause/resume manually
- ✅ Edge Functions timeout (60s limit)

### **Q: How do I change max depth mid-crawl?**
You can't change an existing session. But you can:
1. Stop current crawl
2. Start new crawl with different depth

### **Q: Where are the Supabase credentials stored?**
In the Python file. **Never commit ANON_KEY to git!** 

Better approach:
```python
import os
ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
```

Then run:
```bash
export SUPABASE_ANON_KEY="your-key-here"
python PYTHON_DB_WORKER.py ...
```

---

## 🎉 Success Checklist

After your first crawl, you should have:

- ✅ `crawl_sessions` table with 1 row (your session)
- ✅ `crawl_queue` table with many rows (all discovered URLs)
- ✅ `pages` table with crawled page data
- ✅ `internal_links` analyzed automatically by intelligence layer
- ✅ Opportunities generated in dashboard

---

## 🆘 Troubleshooting

### **Error: "Failed to initialize"**
- Check your `BACKEND_URL` and `ANON_KEY` are correct
- Ensure `crawl_queue` table exists (run `/setup-pro-crawler` endpoint first)

### **Crawl stops after 1 page**
- Check `maxDepth` - must be at least 1 to enqueue links
- Verify site has internal links

### **"No module named 'bs4'"**
```bash
pip install beautifulsoup4
```

### **"No module named 'lxml'"**
```bash
pip install lxml
```

---

## 📚 Next Steps

1. **Read** `DATABASE_FIRST_ARCHITECTURE.md` for deep-dive technical details
2. **Explore** your crawled data in the React dashboard
3. **Analyze** internal linking opportunities
4. **Export** your crawl results via the export endpoint

🚀 **Happy Crawling!**

# 🚀 Quick Start - Hybrid Crawler System

Get your Internal Link Optimizer running in under 10 minutes!

---

## 📋 Prerequisites

- ✅ Supabase account (free tier works!)
- ✅ Database access
- 🐍 Python 3.8+ (optional, for large sites only)

---

## Step 1: Database Setup (One-Time)

### Open Supabase SQL Editor

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click **SQL Editor** in left sidebar
4. Click **New Query**

### Run the Setup SQL

Copy and paste the entire contents of `database-setup.sql` and click **RUN**.

**This creates:**
- ✅ `projects` table
- ✅ `crawl_sessions` table
- ✅ `crawl_queue` table (the brain!)
- ✅ `pages` table (the results!)
- ✅ `internal_links` table
- ✅ `opportunities` table
- ✅ All necessary indexes

**Expected result:** `Success. No rows returned`

---

## Step 2: Test Your Dashboard

### Open Your App

1. Navigate to your React app
2. You should see the dashboard

### Create Your First Project

1. Click **"New Project"** or **"+"** button
2. Enter:
   - **Project Name:** "Test Site"
   - **Website URL:** `https://example.com` (or any small site)
   - **Max Pages:** 50 (start small!)
3. Click **"Create Project"**

---

## Step 3: Run Your First Crawl

### Option A: TypeScript Crawler (Recommended for First Test)

Perfect for sites with **10-1000 pages**.

**Steps:**
1. Click **"Start Crawl"** button
2. Watch the progress bar fill up
3. See pages appear in real-time
4. Done! ✨

**What's happening behind the scenes:**
```
Your dashboard → Creates session → Adds start URL to queue →
Edge Function processes queue → Saves pages to DB →
Dashboard updates in real-time
```

**If you see "Setup Required" modal:**
- Click "Copy SQL"
- Open Supabase SQL Editor
- Paste and run
- Come back and click "Start Crawl" again

---

### Option B: Python Worker (For Large Sites)

Perfect for sites with **1000+ pages**.

#### Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install httpx beautifulsoup4
```

#### Start a Crawl in Dashboard

1. Click **"Start Crawl"**
2. **Copy the Session ID** from:
   - URL bar: `/project/abc-123/session/`**`SESSION-ID-HERE`**
   - Or from the Debug Panel (if visible)

#### Set Environment Variables

**macOS/Linux:**
```bash
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'
export SESSION_ID='session-id-from-step-2'
```

**Windows (PowerShell):**
```powershell
$env:SUPABASE_URL='https://your-project.supabase.co'
$env:SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'
$env:SESSION_ID='session-id-from-step-2'
```

**Finding your Supabase keys:**
1. Supabase Dashboard → Settings → API
2. **Project URL** → Copy to `SUPABASE_URL`
3. **service_role key** → Copy to `SUPABASE_SERVICE_ROLE_KEY`

⚠️ **IMPORTANT:** The service_role key is sensitive! Never commit it to Git.

#### Run the Worker

```bash
python worker.py
```

Or use the helper script:
```bash
chmod +x start_worker.sh
./start_worker.sh
```

**What you'll see:**
```
============================================================
🚀 Internal Link Optimizer - Crawler Worker
============================================================
📋 Session ID: abc-123-def-456
🌐 Domain: example.com
📄 Max Pages: 5000
🔗 Start URL: https://example.com
============================================================

🔎 [0] Crawling: https://example.com
✅ Completed: https://example.com (45 links found)
🔎 [1] Crawling: https://example.com/about
✅ Completed: https://example.com/about (12 links found)
📊 Progress: 10/5000 pages crawled
...
```

**Dashboard will update in real-time!** Open your dashboard while Python runs and watch the magic happen. 🪄

---

## Step 4: View Your Results

### In the Dashboard

Once crawling is complete (or in progress):

1. **Overview Tab:**
   - Total pages crawled
   - Internal links found
   - Link health score
   - Distribution charts

2. **Pages Tab:**
   - All crawled pages
   - Search and filter
   - Sort by various metrics
   - Click any page for details

3. **Link Graph Tab:**
   - Visual site architecture
   - Tree view (hierarchical)
   - Force graph (network)
   - See how pages connect

4. **Intelligence Tab:**
   - Keyword analysis
   - Page type classification
   - Content recommendations
   - Link opportunities

---

## 🎉 You're Done!

Your crawler is now operational! Here's what you've accomplished:

✅ Database tables created  
✅ First project created  
✅ First crawl completed  
✅ Data visible in dashboard  
✅ Both crawlers available (TypeScript + Python)  

---

## 🚀 What's Next?

### Test With Different Sites

1. Add another project
2. Try a larger site (100-500 pages)
3. Compare TypeScript vs Python speed

### Explore Features

- **Link Opportunities:** Auto-generated suggestions
- **Page Types:** See how pages are classified
- **Link Equity:** Understand which pages are most important
- **Export Data:** Download CSV reports

### Scale Up

- Run Python worker for 10,000+ page sites
- Use multiple Python workers in parallel
- Set up automated crawls with cron jobs

---

## 🐛 Troubleshooting

### "Table does not exist" error

**Fix:** You didn't run `database-setup.sql`
- Go to Supabase SQL Editor
- Copy contents of `database-setup.sql`
- Run it

### TypeScript crawler says "Setup Required"

**Fix:** Missing `crawl_queue` table
- Click "Copy SQL" in the modal
- Run in Supabase SQL Editor
- Try again

### Python worker says "Session not found"

**Fix:** Wrong `SESSION_ID` or session deleted
- Start new crawl in dashboard
- Copy the new Session ID
- Update `SESSION_ID` environment variable

### Dashboard shows 0 pages

**Fix:** Check if crawl is still running
- Look at `crawl_sessions` table status
- Check `crawl_queue` for pending URLs
- Try running Python worker manually

### Pages crawling but not appearing

**Fix:** Refresh dashboard
- Browser may be caching
- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

---

## 📚 Additional Resources

- **Full Architecture:** See `ARCHITECTURE.md`
- **Comparison Guide:** See `CRAWLER_COMPARISON.md`
- **Python Details:** See `PYTHON_WORKER_README.md`
- **Complete Guide:** See `HYBRID_CRAWLER_GUIDE.md`

---

## 💡 Pro Tips

### For Best Performance

1. **Start small:** Test with 10-50 pages first
2. **Use TypeScript** for quick tests
3. **Use Python** for production crawls
4. **Monitor progress** in dashboard
5. **Don't close dashboard** while crawling (helps with visibility)

### For Large Sites

1. Increase page limit to 5000+
2. Run Python worker on a VPS or cloud server
3. Use `nohup python worker.py &` for background execution
4. Monitor with `tail -f crawler.log`

### For Development

1. Keep page limits low (10-100)
2. Use TypeScript for faster iteration
3. Check `crawl_queue` table to debug
4. Use Debug Panel in dashboard

---

## 🎯 Common Use Cases

### Quick Site Audit (TypeScript)
```
1. Create project
2. Set max pages: 100
3. Click "Start Crawl"
4. Wait 3-5 minutes
5. Review Overview tab
```

### Deep Site Analysis (Python)
```
1. Create project
2. Set max pages: 5000
3. Click "Start Crawl"
4. Copy Session ID
5. Run: python worker.py
6. Let it run overnight
7. Review complete analysis next day
```

### Ongoing Monitoring (Scheduled)
```
1. Set up cron job on VPS
2. Weekly crawl of important sites
3. Compare results over time
4. Track improvements
```

---

## ✅ Success Checklist

- [ ] Database tables created
- [ ] Dashboard loads without errors
- [ ] Can create new project
- [ ] TypeScript crawler works for small site
- [ ] Python installed (if needed)
- [ ] Python worker tested (if needed)
- [ ] Can view results in all tabs
- [ ] Understand when to use each crawler

---

## 🆘 Need Help?

If you're stuck:

1. Check `TROUBLESHOOTING_GUIDE.md`
2. Review `HYBRID_CRAWLER_GUIDE.md`
3. Verify database tables exist in Supabase
4. Check browser console for errors
5. Check Supabase logs for backend errors

---

## 🚀 You're Ready!

You now have an **industrial-grade internal link crawler** that can:
- Handle 10 to 100,000+ pages
- Resume after crashes
- Show real-time progress
- Run in the cloud OR locally
- Scale with your needs

**Go build something amazing!** 🎉

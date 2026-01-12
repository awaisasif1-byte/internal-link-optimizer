# 🕷️ Local Crawler Setup

Your crawler is now ready to run **on your local PC** with no timeout limits!

## 🚀 Quick Start Guide

### Step 1: Download and Install

1. **Download this project** to your local machine
2. **Open terminal/command prompt** in the project folder
3. **Install dependencies:**
   ```bash
   npm install
   ```

### Step 2: Configure Environment Variables

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your Supabase credentials:**
   - Go to your Supabase project dashboard
   - Click **Settings** (gear icon) → **API**
   - Copy "**Project URL**" → paste as `SUPABASE_URL`
   - Copy "**service_role**" secret → paste as `SUPABASE_SERVICE_ROLE_KEY`

### Step 3: Start a Crawl in the Web App

1. Open your web application
2. Create a new project
3. Click "**Start Crawl**"
4. **Copy the session ID** from the browser URL or console logs

### Step 4: Run the Local Crawler

```bash
npm run crawl -- --session YOUR_SESSION_ID_HERE
```

**Example:**
```bash
npm run crawl -- --session abc123-def456-ghi789
```

---

## 📊 What You'll See

```
========================================
🕷️  LOCAL CRAWLER STARTED
========================================
📋 Session ID: abc123-def456
🌐 Supabase URL: https://your-project.supabase.co
========================================

🌐 [1/100] Fetching: https://example.com/
  ✅ Title: Example Domain
  📊 500 words, 25 internal links found
  ➕ Added 25 new URLs to queue

🌐 [2/100] Fetching: https://example.com/about
  ✅ Title: About Us
  📊 750 words, 18 internal links found
  ➕ Added 10 new URLs to queue

...

========================================
✅ CRAWL COMPLETED!
========================================
📄 Pages Processed: 100
🔗 Links Discovered: 452
❌ Errors: 2
⏱️  Duration: 180s
⚡ Speed: 0.56 pages/sec
========================================
```

---

## 🎯 Benefits of Local Crawling

✅ **No timeout limits** - Crawl 1000s of pages  
✅ **Full control** - See real-time logs in your terminal  
✅ **Easy debugging** - Error messages appear immediately  
✅ **Pause/Resume** - Press `Ctrl+C` to stop (status saved)  
✅ **Fast & Reliable** - Uses your PC's resources

---

## ⚠️ Troubleshooting

### "Missing environment variables"
Make sure you created the `.env` file with correct Supabase credentials.

### "Session not found"
Start a crawl in the web app first, then copy the session ID.

### "Cannot connect to database"
Double-check your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

---

## 🛑 Stopping a Crawl

Press `Ctrl+C` in your terminal to gracefully stop the crawler. The session status will be marked as "stopped" in the database.

---

## 📝 Notes

- The crawler connects directly to your Supabase database
- Crawled data appears in your web dashboard in real-time
- One crawler per session - don't run multiple at once
- Respects a 500ms delay between requests (be nice to servers!)

---

**Happy Crawling!** 🚀

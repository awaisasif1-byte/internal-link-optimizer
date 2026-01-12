# 🔍 Crawler Comparison Guide

## Which Crawler Should I Use?

| Feature | TypeScript Auto-Crawl | Python DB-First Queue |
|---------|----------------------|----------------------|
| **Best For** | Small-medium sites (10-1000 pages) | Large sites (1K-100K+ pages) |
| **Max Pages** | ~1000 (Edge Function timeout limit) | Unlimited |
| **Max Depth** | 20 | 20 |
| **Timeout** | 60 seconds per batch | No timeout (runs indefinitely) |
| **Pause/Resume** | ❌ No | ✅ Yes |
| **Crash Recovery** | ❌ Must restart from scratch | ✅ Auto-recovers stuck URLs |
| **Setup Complexity** | ✅ Zero setup (click button) | ⚠️ Requires Python installation |
| **Speed** | Fast (runs in Edge Function) | Moderate (network latency per request) |
| **Parallel Workers** | ❌ No | ✅ Yes (future feature) |
| **JS Rendering** | ❌ Not supported | ⚠️ Can add Selenium (manual setup) |
| **Where It Runs** | Supabase Edge Function | Your local machine |
| **Observability** | Limited (check database manually) | ✅ Live terminal output |

---

## 📊 Use Case Recommendations

### **Use TypeScript Auto-Crawl if:**
- ✅ Site has < 1000 pages
- ✅ You want zero setup (just click a button)
- ✅ You're okay with 60s timeout per batch
- ✅ You don't need to pause mid-crawl
- ✅ Site doesn't require JavaScript rendering

**Example sites:**
- Company websites (5-50 pages)
- Small blogs (10-500 pages)
- Portfolio sites (3-20 pages)
- Documentation sites (50-300 pages)

---

### **Use Python DB-First Queue if:**
- ✅ Site has 1000+ pages
- ✅ You need to crawl 10K-100K+ pages
- ✅ You want to pause and resume anytime
- ✅ You're okay installing Python dependencies
- ✅ You want live progress monitoring
- ✅ Crawl might take hours/days
- ✅ You need crash recovery

**Example sites:**
- E-commerce sites (1K-100K products)
- News websites (10K+ articles)
- Large blogs (5K+ posts)
- Wikipedia-style sites (100K+ pages)
- Forums (50K+ threads)

---

## 🚀 Quick Start Commands

### **TypeScript Auto-Crawl**
```typescript
// In your React dashboard
<button onClick={handleStartCrawl}>
  Start New Crawl
</button>

// Or via API
await api.startAutoCrawl(projectId, 1000);
```

**What happens:**
1. Click button
2. Wait 2-10 minutes
3. Done! (up to 1000 pages crawled)

---

### **Python DB-First Queue**
```bash
# Install dependencies (one-time)
pip install requests beautifulsoup4 lxml

# Configure (one-time)
# Edit PYTHON_DB_WORKER.py lines 41-42
BACKEND_URL = "https://your-project.supabase.co/functions/v1/make-server-4180e2ca"
ANON_KEY = "your-anon-key"

# Run crawler
python PYTHON_DB_WORKER.py my-project https://example.com --max-pages 10000 --max-depth 5

# Let it run (hours/days for large sites)
# Can pause with Ctrl+C anytime
```

**What happens:**
1. Run command
2. See live progress in terminal
3. Can stop anytime (Ctrl+C)
4. Restart to resume (with new session)

---

## ⚡ Performance Comparison

### **Small Site (100 pages, depth 3)**

**TypeScript Auto-Crawl:**
```
Time: ~2 minutes
Pages: 100
Result: ✅ Perfect choice!
```

**Python DB-First:**
```
Time: ~5 minutes (network overhead)
Pages: 100
Result: ⚠️ Overkill (use TypeScript instead)
```

**Winner:** TypeScript Auto-Crawl

---

### **Medium Site (1000 pages, depth 5)**

**TypeScript Auto-Crawl:**
```
Time: ~10-20 minutes
Pages: 1000
Result: ✅ Works, might hit timeout in some batches
```

**Python DB-First:**
```
Time: ~20-30 minutes
Pages: 1000
Result: ✅ More reliable for this size
```

**Winner:** Either (TypeScript is faster, Python is more reliable)

---

### **Large Site (10,000 pages, depth 8)**

**TypeScript Auto-Crawl:**
```
Time: ???
Pages: Will likely fail with timeout errors
Result: ❌ Not recommended
```

**Python DB-First:**
```
Time: ~3-5 hours
Pages: 10,000
Result: ✅ Perfect! Handles timeouts gracefully
```

**Winner:** Python DB-First Queue

---

### **Massive Site (100,000 pages, depth 10)**

**TypeScript Auto-Crawl:**
```
Result: ❌ Impossible (timeout limits)
```

**Python DB-First:**
```
Time: ~20-40 hours
Pages: 100,000
Result: ✅ Designed for this!
Can pause overnight, resume next day
```

**Winner:** Python DB-First Queue (only option)

---

## 🔧 Architecture Differences

### **TypeScript Auto-Crawl**
```
Frontend
   ↓
Backend (Edge Function)
   ↓
WebCrawler
   ↓ (loops internally)
Crawls all pages
   ↓
Saves to database
   ↓
Returns when done (or timeout)
```

**Pros:**
- ✅ Simple (one API call)
- ✅ Fast (no network overhead)

**Cons:**
- ❌ Must complete in 60s per batch
- ❌ Can't pause mid-crawl
- ❌ Crash = restart from scratch

---

### **Python DB-First Queue**
```
Python Worker (Your Machine)
   ↓
Backend: "Give me next URL"
   ↓
Backend: "Here: https://example.com/page-1"
   ↓
Python: Crawls page-1
   ↓
Python → Backend: "Here's the data + 10 links"
   ↓
Backend: Saves data, enqueues 10 links
   ↓
Python: "Give me next URL"
   ↓
Backend: "Here: https://example.com/page-2"
   ↓
... loop continues ...
```

**Pros:**
- ✅ No timeouts
- ✅ Can pause/resume
- ✅ Crash = auto-recovery
- ✅ Live progress monitoring

**Cons:**
- ❌ Network latency (each request = API call)
- ❌ Requires Python setup
- ❌ Must keep terminal open

---

## 🎯 Decision Matrix

### **Choose TypeScript if:**
```
Site Pages < 1000
AND
You want zero setup
AND
You're okay with potential timeouts
```

### **Choose Python if:**
```
Site Pages > 1000
OR
You need pause/resume
OR
Crawl will take > 1 hour
OR
You need crash recovery
```

---

## 💡 Pro Tips

### **For TypeScript Auto-Crawl:**
1. ✅ Start with `maxPages: 100` to test first
2. ✅ Monitor console logs in browser DevTools
3. ✅ If timeouts occur, reduce `maxPages` or use Python
4. ✅ Best for quick prototypes and demos

### **For Python DB-First:**
1. ✅ Test with `--max-pages 10` first to verify setup
2. ✅ Use `--max-depth 3` for initial crawls, increase gradually
3. ✅ Keep terminal open (use `screen` or `tmux` for long crawls)
4. ✅ Check queue stats periodically:
   ```bash
   curl https://your-project.supabase.co/.../crawl/sessions/SESSION_ID/stats \
     -H "Authorization: Bearer YOUR_KEY"
   ```
5. ✅ For massive sites (100K+ pages), run overnight

---

## 📈 Scaling Strategies

### **TypeScript Auto-Crawl Scaling:**
```
Small site (100 pages):     maxPages: 100, maxDepth: 3
Medium site (500 pages):    maxPages: 500, maxDepth: 5
Large site (1000 pages):    maxPages: 1000, maxDepth: 8
```

**Hard limit:** ~1000 pages (Edge Function timeout)

---

### **Python DB-First Scaling:**
```
Small site (100 pages):     maxPages: 100, maxDepth: 3
Medium site (1K pages):     maxPages: 1000, maxDepth: 5
Large site (10K pages):     maxPages: 10000, maxDepth: 8
Massive site (100K pages):  maxPages: 100000, maxDepth: 10
```

**No hard limit!** (only disk space and time)

---

## 🆚 Side-by-Side Example

### **Scenario: E-commerce site with 5,000 products**

#### **Option A: TypeScript Auto-Crawl**
```typescript
// Frontend
await api.startAutoCrawl('ecom-site', 5000);

// Result:
❌ Timeout errors after ~1500 pages
❌ Need to restart multiple times
❌ Total time: ~2 hours (with manual restarts)
```

#### **Option B: Python DB-First**
```bash
python PYTHON_DB_WORKER.py ecom-site https://shop.com --max-pages 5000 --max-depth 5

# Result:
✅ Smooth crawl
✅ Can pause for lunch, resume after
✅ Total time: ~1.5 hours (one run)
```

**Winner:** Python (for this use case)

---

## 🎉 Conclusion

**For 90% of sites < 1000 pages:**
→ Use **TypeScript Auto-Crawl** (easier, faster)

**For 10% of large sites > 1000 pages:**
→ Use **Python DB-First Queue** (reliable, scalable)

**Both use the same database schema, so you can switch anytime!**

---

## 🚀 Next Steps

1. **Read:** `HOW_IT_WORKS.md` for complete flow explanation
2. **Try:** TypeScript Auto-Crawl first (zero setup)
3. **Upgrade:** To Python if you hit limits
4. **Reference:** `QUICK_START.md` for Python setup
5. **Deep Dive:** `DATABASE_FIRST_ARCHITECTURE.md` for technical details

Happy Crawling! 🎯

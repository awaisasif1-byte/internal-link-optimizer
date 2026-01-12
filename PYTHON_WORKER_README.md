# 🐍 Python Crawler Worker

Industrial-strength crawler for large-scale internal link analysis (1,000-100,000 pages).

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start a Crawl in Dashboard

1. Open your React dashboard
2. Create new project
3. Click "Start Crawl"
4. Copy the **Session ID** from the URL or Debug Panel

### 3. Set Environment Variables

```bash
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'
export SESSION_ID='uuid-from-dashboard'
```

**Finding your keys:**
- Supabase Dashboard → Settings → API
- URL: Under "Project URL"
- Service Key: Under "Project API keys" → `service_role` (keep secret!)

### 4. Run Worker

```bash
python worker.py
```

Or use the helper script:

```bash
chmod +x start_worker.sh
./start_worker.sh
```

## Features

✅ **Crash-Proof** - All state in database, resume anytime  
✅ **No Timeouts** - Runs for hours/days without limits  
✅ **Real-Time Updates** - Dashboard shows live progress  
✅ **Semantic Analysis** - Keywords, page types, link equity  
✅ **Duplicate Prevention** - Never crawls same URL twice  
✅ **Respectful** - Honors robots.txt, polite delays  

## Architecture

```
Dashboard (Start) → Database (Queue) → Python Worker → Database (Results) → Dashboard (Display)
```

The worker:
1. Pulls pending URLs from `crawl_queue` table
2. Crawls each page
3. Saves results to `pages` table
4. Adds discovered links back to queue
5. Repeats until queue is empty

## Advanced Usage

### Stop and Resume

```bash
# Stop anytime with Ctrl+C
^C

# Resume later (same SESSION_ID)
python worker.py
```

### Multiple Workers (Parallel Crawling)

Run multiple instances with the same `SESSION_ID`:

```bash
# Terminal 1
python worker.py

# Terminal 2 (same SESSION_ID!)
python worker.py
```

They'll automatically coordinate via the database.

### Background Execution (VPS/Server)

```bash
nohup python worker.py > crawler.log 2>&1 &
tail -f crawler.log
```

### Custom Configuration

Edit `worker.py` to adjust:

```python
# Concurrency (URLs processed simultaneously)
tasks = await get_next_tasks(limit=5)  # Increase for faster crawling

# Politeness delay
await asyncio.sleep(0.5)  # Decrease for faster (less polite) crawling

# Request timeout
async with httpx.AsyncClient(timeout=15.0)  # Increase for slow sites
```

## Troubleshooting

### "Session not found"
- Wrong `SESSION_ID` or session deleted
- Start new crawl in dashboard and copy new ID

### "Queue empty" but pages missing
- Crawl may be complete
- Check dashboard - all pages should be there
- Verify `max_pages` limit wasn't reached

### Slow crawling
- Increase concurrency: `limit=20` instead of `limit=5`
- Reduce delay: `sleep(0.1)` instead of `sleep(0.5)`
- Run multiple workers in parallel

### Database errors
- Check `SUPABASE_SERVICE_ROLE_KEY` is correct
- Verify database tables exist (run setup SQL)
- Check Supabase dashboard for API limits

## Performance

| Workers | Pages/Min | Best For |
|---------|-----------|----------|
| 1 worker | 60-100 | Normal sites |
| 3 workers | 180-300 | Large sites |
| 5 workers | 300-500 | Massive sites |

## Security Notes

⚠️ **Never commit `SUPABASE_SERVICE_ROLE_KEY` to version control**

It bypasses Row Level Security and has full database access.

Use environment variables or `.env` files (add to `.gitignore`).

## Need Help?

See the full guide: [HYBRID_CRAWLER_GUIDE.md](./HYBRID_CRAWLER_GUIDE.md)

# Backend Integration Guide

This guide explains how to connect your Python crawler to the React dashboard.

## Architecture

```
Python Crawler → Supabase API → React Dashboard
```

- **Database**: Supabase PostgreSQL
- **Backend API**: Supabase Edge Functions (Deno/Hono)
- **Frontend**: React + TypeScript

## Setup Instructions

### 1. Database Setup

The database schema is already defined in `/supabase/migrations/001_create_schema.sql`.

Tables created:
- `projects` - Website projects
- `crawl_sessions` - Crawl history/progress
- `pages` - Crawled pages with metrics
- `internal_links` - Links between pages
- `opportunities` - Internal linking suggestions

### 2. Get Supabase Credentials

You need two values from your Supabase project:

1. **Project ID**: Found in your Supabase project URL
   ```
   https://[YOUR_PROJECT_ID].supabase.co
   ```

2. **Anon Key**: Found in Project Settings > API > anon/public key

### 3. Configure Python Crawler

Set environment variables:

```bash
export SUPABASE_PROJECT_ID="your-project-id"
export SUPABASE_ANON_KEY="your-anon-key"
```

### 4. Install Python Dependencies

```bash
pip install requests aiohttp beautifulsoup4 numpy
```

### 5. Run the Crawler

#### Option A: Create Project via Dashboard
1. Open the React dashboard
2. Click "New Project" in sidebar
3. Fill in project details
4. Copy the project ID from the URL after creation

#### Option B: Create Project via API
```bash
curl -X POST https://YOUR_PROJECT_ID.supabase.co/functions/v1/make-server-4180e2ca/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{
    "name": "My Website",
    "description": "Website audit",
    "url": "https://example.com"
  }'
```

#### Run Crawler and Upload Results

```bash
cd python_integration
python upload_crawler.py <project-id> <website-url> [max-pages]
```

Example:
```bash
python upload_crawler.py abc-123-def-456 https://example.com 50
```

## API Endpoints

All endpoints are prefixed with `/make-server-4180e2ca/`

### Projects
- `GET /projects` - List all projects
- `POST /projects` - Create new project
- `GET /projects/:id` - Get project with stats

### Crawling
- `POST /projects/:id/crawl/start` - Start crawl session
- `POST /projects/:id/crawl/results` - Upload crawler results
- `GET /projects/:id/crawl/sessions` - Get crawl history

### Data
- `GET /projects/:id/stats` - Get dashboard statistics
- `GET /projects/:id/pages` - Get crawled pages
- `GET /projects/:id/opportunities` - Get linking opportunities

## Data Flow

### 1. Create Project
```
React Dashboard → POST /projects → Database
```

### 2. Start Crawl
```
Python Script → POST /projects/:id/crawl/start → Create session in DB
```

### 3. Run Crawler
```
Python crawler.py → Crawl website → Generate pages array
```

### 4. Upload Results
```
Python Script → POST /projects/:id/crawl/results → Save to DB
```

### 5. View Dashboard
```
React Dashboard → GET /projects/:id/stats → Display metrics
```

## Crawler Output Format

Your `crawler.py` should return pages in this format:

```python
{
  "url": "https://example.com/page",
  "depth": 0,
  "title": "Page Title",
  "status": 200,
  "content": "Page content...",
  "internal_links": ["https://example.com/other-page"],
  "link_equity_score": 5.23,
  "opps": [
    {
      "from": "https://example.com/page",
      "to": "https://example.com/other-page",
      "anchor": "Anchor Text",
      "type": "Precision",
      "priority": "High"
    }
  ],
  "broken_count": 2,
  "score": 87
}
```

## Dashboard Features Using Real Data

Once connected, the dashboard will show:

✅ **KPI Cards** - Total pages, links, issues, opportunities, health score
✅ **Page Performance Table** - All crawled pages with metrics
✅ **Link Distribution Charts** - Visual analytics
✅ **Action Items** - Critical issues and quick wins
✅ **Recent Activity** - Crawl history
✅ **Site Health** - Overall score and suggestions

## Troubleshooting

### CORS Errors
The backend is configured with open CORS. If you see CORS errors, check that you're using the correct project ID.

### 401 Unauthorized
Make sure you're passing the `Authorization: Bearer YOUR_ANON_KEY` header in all requests.

### No Data Showing
1. Check that the crawler uploaded results successfully
2. Verify the project ID matches
3. Check browser console for API errors

### Database Connection Issues
The backend uses `SUPABASE_SERVICE_ROLE_KEY` environment variable. This is automatically set in Supabase Edge Functions.

## Example Workflow

```bash
# 1. Create project (via dashboard or API)
# Returns: { "id": "abc-123", "name": "My Site", ... }

# 2. Run crawler
python upload_crawler.py abc-123 https://mysite.com 100

# Output:
# === Starting Crawl Session ===
# ✓ Crawl session started: xyz-789
#
# === Crawling https://mysite.com ===
# [SUCCESS] 200: https://mysite.com/
# [SUCCESS] 200: https://mysite.com/about
# ...
#
# === Crawl Complete ===
# Total pages crawled: 42
# Successful: 40
# Failed: 2
#
# === Uploading Results ===
# Uploading 42 pages to backend...
# ✓ Successfully uploaded results!
#
# ✓ Done!

# 3. View in dashboard
# Navigate to the project in your React app to see all metrics!
```

## Next Steps

1. **Automate Crawls**: Set up a cron job to run crawler regularly
2. **Webhooks**: Add notifications when crawls complete
3. **Export Reports**: Download CSV/PDF reports
4. **API Integration**: Use the API in your own tools

## Support

Check these files for implementation details:
- `/supabase/functions/server/crawler_api.tsx` - Backend API logic
- `/src/app/hooks/useApi.ts` - Frontend API client
- `/python_integration/upload_crawler.py` - Python integration script

# Crawl Integration Guide

## Overview

This document explains how the crawl workflow works from creating a project to viewing results.

## Complete Workflow

### 1. Database Setup (One-Time)

Before anything works, you must create the database tables:

1. Go to your Supabase Dashboard
2. Navigate to SQL Editor
3. Copy the SQL from the database setup screen in the app
4. Run it to create all tables: `projects`, `crawl_sessions`, `pages`, `internal_links`, `opportunities`

### 2. Create a New Project

**Frontend Flow:**
1. User clicks "New Project" in the app
2. Fills out the form (name, description, URL)
3. Clicks "Create"

**Backend Flow:**
1. `NewProjectScreen` calls `api.createProject(name, description, url)`
2. API creates project in database → returns `{ id: "project-uuid", ... }`
3. `NewProjectScreen` calls `api.startCrawl(projectId, 50)`
4. API creates crawl session in database → returns `{ id: "session-uuid", ... }`
5. App navigates to `CrawlingProgressScreen` with `projectId` and `crawlSessionId`

### 3. Crawling Progress Screen

**What it shows:**
- Crawl session status (running, completed, error)
- Progress bar (pages crawled / max pages)
- Instructions on how to run the Python crawler
- Real-time list of crawled pages
- Auto-refreshes every 3 seconds

**The screen displays:**
```bash
# Command to run your crawler
python integration/supabase_integration.py \
  --project-id <PROJECT_ID> \
  --session-id <SESSION_ID> \
  --url https://example.com
```

### 4. Running the Python Crawler

**Setup Environment Variables:**
```bash
# Get these from /utils/supabase/info.tsx
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_ANON_KEY='your-anon-key-here'
```

**Run the Integration Script:**
```bash
python integration/supabase_integration.py \
  --project-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --session-id b2c3d4e5-f6g7-8901-bcde-f12345678901 \
  --url https://example.com \
  --max-pages 50
```

**What the script does:**
1. Imports your crawler modules (`crawler.py`, `opportunities.py`, `scoring.py`)
2. Runs the crawler on the specified URL
3. Formats the results
4. Saves pages via `POST /projects/{id}/crawl/results`
5. Saves opportunities via `POST /projects/{id}/opportunities`

### 5. Data Flow

```
User Creates Project
    ↓
Frontend calls API
    ↓
Database: project + crawl_session created
    ↓
User sees Crawling Progress Screen
    ↓
User runs Python script with IDs
    ↓
Python crawler runs
    ↓
Results saved to API endpoints
    ↓
Database: pages + opportunities + internal_links saved
    ↓
Frontend auto-refreshes (every 3 seconds)
    ↓
User sees crawled pages appear
    ↓
When complete: User clicks "View Dashboard"
    ↓
Dashboard shows stats, charts, opportunities
```

### 6. API Endpoints Used

#### Create Project
```
POST /projects
Body: { name, description, base_url }
Returns: { id, name, base_url, status, created_at, updated_at }
```

#### Start Crawl Session
```
POST /projects/{id}/crawl/start
Body: { maxPages }
Returns: { id, project_id, status, pages_crawled, max_pages, started_at }
```

#### Save Crawl Results
```
POST /projects/{id}/crawl/results
Body: {
  crawl_session_id,
  pages: [
    { url, title, depth, status, content, link_equity_score, health_score, broken_count },
    ...
  ]
}
```

#### Save Opportunities
```
POST /projects/{id}/opportunities
Body: {
  opportunities: [
    { from_url, to_url, anchor, type, priority },
    ...
  ]
}
```

#### Get Project Data
```
GET /projects/{id}
GET /projects/{id}/pages
GET /projects/{id}/opportunities
GET /projects/{id}/crawl/sessions
GET /projects/{id}/stats
```

### 7. Updating Crawl Status

The Python integration script automatically updates the crawl session:

**During crawl:**
- Pages are added to database
- `pages_crawled` count increases
- Frontend shows progress

**When complete:**
- Script marks session as `completed`
- Frontend shows "Crawling Complete!"
- User can navigate to dashboard

### 8. Troubleshooting

#### "Could not find the table 'public.projects'"
- You haven't run the database setup SQL yet
- Go to Supabase SQL Editor and run the setup script

#### "Missing environment variables"
- Set `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Get values from `/utils/supabase/info.tsx`

#### "Could not import crawler modules"
- The integration script can't find your Python files
- Make sure `crawler.py`, `opportunities.py`, `scoring.py` exist
- Script will use mock data for testing

#### "API request failed"
- Check that your Supabase project is running
- Verify the API endpoints are working
- Check browser console for errors

#### Pages not appearing
- Make sure you're using the correct project ID and session ID
- Check that the Python script is actually running
- Look for error messages in the Python output
- Verify the API calls are succeeding (check Python output)

### 9. Testing Without Your Crawler

If you don't have your crawler ready, the integration script will automatically use mock data. This lets you test the entire flow end-to-end without needing the real crawler.

The mock data includes:
- 2 sample pages
- 1 sample opportunity
- All properly formatted for the database

### 10. Next Steps After Crawling

Once crawling is complete:
1. Click "View Dashboard"
2. See project statistics
3. View all crawled pages
4. Review internal linking opportunities
5. Analyze link distribution charts
6. Check link health trends

## Files Involved

### Frontend
- `/src/app/App.tsx` - Main app routing
- `/src/app/components/NewProjectScreen.tsx` - Project creation form
- `/src/app/components/CrawlingProgressScreen.tsx` - Wrapper for progress view
- `/src/app/components/CrawlingProgressConnected.tsx` - Connected progress component
- `/src/app/components/DashboardConnected.tsx` - Dashboard with real data
- `/src/app/hooks/useApi.tsx` - API client and hooks

### Backend
- `/supabase/functions/server/index.tsx` - Main API server
- `/supabase/functions/server/crawler_api.tsx` - Crawl-specific endpoints
- `/supabase/migrations/001_create_schema.sql` - Database schema

### Python Integration
- `/integration/supabase_integration.py` - Main integration script
- `/integration/README.md` - Integration instructions
- `/crawler.py` - Your crawler (user-provided)
- `/opportunities.py` - Your opportunity finder (user-provided)
- `/scoring.py` - Your scoring calculator (user-provided)

## Summary

The workflow is now fully connected:
1. ✅ Create project → stores in database
2. ✅ Start crawl session → stores session ID
3. ✅ Show progress screen → displays real-time updates
4. ✅ Run Python crawler → saves results via API
5. ✅ Auto-refresh → shows live progress
6. ✅ Complete → navigate to dashboard
7. ✅ Dashboard → displays analyzed data

Everything is working together! 🎉

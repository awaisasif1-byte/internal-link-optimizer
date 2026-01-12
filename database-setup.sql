-- ============================================================
-- HYBRID CRAWLER SYSTEM - COMPLETE DATABASE SETUP
-- ============================================================
-- Run this SQL in your Supabase SQL Editor to set up all tables
-- for both TypeScript (Edge Function) and Python crawlers
-- ============================================================

-- 1. PROJECTS TABLE
-- Stores information about each website being analyzed
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. CRAWL SESSIONS TABLE
-- Each crawl gets its own session for tracking progress
CREATE TABLE IF NOT EXISTS crawl_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  start_url TEXT NOT NULL,
  status TEXT DEFAULT 'pending', -- pending, running, completed, failed
  pages_crawled INTEGER DEFAULT 0,
  pages_found INTEGER DEFAULT 0,
  max_pages INTEGER DEFAULT 100,
  max_depth INTEGER DEFAULT 3,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. CRAWL QUEUE TABLE (THE BRAIN)
-- Stateful queue - both TypeScript and Python read from here
-- This makes the system truly resumable and crash-proof
CREATE TABLE IF NOT EXISTS crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  priority INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_session_url UNIQUE(session_id, normalized_url)
);

-- 4. PAGES TABLE (THE RESULTS)
-- Both crawlers write crawled data here
-- Dashboard reads from here to display results
CREATE TABLE IF NOT EXISTS pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  session_id UUID REFERENCES crawl_sessions(id) ON DELETE SET NULL,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  title TEXT,
  content TEXT,
  word_count INTEGER DEFAULT 0,
  internal_links_count INTEGER DEFAULT 0,
  external_links_count INTEGER DEFAULT 0,
  status_code INTEGER,
  depth INTEGER DEFAULT 0,
  parent_url TEXT,
  page_type TEXT, -- homepage, blog, product, category, page
  meta_description TEXT,
  keywords TEXT[], -- Array of extracted keywords
  link_equity_score FLOAT DEFAULT 0,
  health_score INTEGER DEFAULT 0,
  broken_count INTEGER DEFAULT 0,
  crawled_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_project_url UNIQUE(project_id, normalized_url)
);

-- 5. INTERNAL LINKS TABLE
-- Tracks the actual link relationships between pages
CREATE TABLE IF NOT EXISTS internal_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
  target_page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
  source_url TEXT NOT NULL,
  target_url TEXT NOT NULL,
  anchor_text TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. OPPORTUNITIES TABLE
-- Stores optimization suggestions (link opportunities, broken links, etc.)
CREATE TABLE IF NOT EXISTS opportunities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
  type TEXT NOT NULL, -- 'link_opportunity', 'broken_link', 'orphan_page', etc.
  severity TEXT NOT NULL, -- 'high', 'medium', 'low'
  title TEXT NOT NULL,
  description TEXT,
  source_url TEXT,
  target_url TEXT,
  status TEXT DEFAULT 'open', -- 'open', 'dismissed', 'fixed'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_url ON projects(url);

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_project ON crawl_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON crawl_sessions(status);

-- Queue indexes (CRITICAL for crawler performance)
CREATE INDEX IF NOT EXISTS idx_queue_session_status ON crawl_queue(session_id, status);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON crawl_queue(priority DESC, depth ASC);
CREATE INDEX IF NOT EXISTS idx_queue_normalized ON crawl_queue(normalized_url);

-- Pages indexes
CREATE INDEX IF NOT EXISTS idx_pages_project ON pages(project_id);
CREATE INDEX IF NOT EXISTS idx_pages_session ON pages(session_id);
CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url);
CREATE INDEX IF NOT EXISTS idx_pages_normalized ON pages(normalized_url);
CREATE INDEX IF NOT EXISTS idx_pages_type ON pages(page_type);

-- Links indexes
CREATE INDEX IF NOT EXISTS idx_links_project ON internal_links(project_id);
CREATE INDEX IF NOT EXISTS idx_links_source ON internal_links(source_page_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON internal_links(target_page_id);

-- Opportunities indexes
CREATE INDEX IF NOT EXISTS idx_opportunities_project ON opportunities(project_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_type ON opportunities(type);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);

-- ============================================================
-- SUCCESS!
-- ============================================================
-- ✅ Database is now ready for both TypeScript and Python crawlers
-- ✅ Both crawlers can read/write to the same tables
-- ✅ Dashboard will display results in real-time
-- ✅ System is crash-proof and resumable
--
-- Next steps:
-- 1. Test TypeScript crawler from dashboard (small sites)
-- 2. Use Python worker for large sites (1000+ pages)
-- 3. Both use the same crawl_queue and pages tables
-- ============================================================

-- ================================================================
-- PRODUCTION CRAWLER - CREATE CRAWL QUEUE TABLE
-- ================================================================
-- Copy and paste this entire SQL into your Supabase SQL Editor
-- Then click "RUN" to create the table
-- ================================================================

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

-- ================================================================
-- DONE! You can now use the production crawler
-- ================================================================

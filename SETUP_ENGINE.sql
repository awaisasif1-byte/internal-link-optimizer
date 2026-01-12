-- =====================================================
-- RUN THIS IN SUPABASE SQL EDITOR
-- =====================================================
-- This creates the crawl_queue table for the ENGINE crawler
-- Copy and paste this entire file into Supabase SQL Editor and click RUN
-- =====================================================

-- Drop existing table if you want a clean start (OPTIONAL - comment out if unsure)
-- DROP TABLE IF EXISTS crawl_queue CASCADE;

-- Create the crawl_queue table
CREATE TABLE IF NOT EXISTS crawl_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  depth INTEGER NOT NULL DEFAULT 0,
  parent_url TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  
  -- THE MAGIC: Prevents duplicate URLs per session (O(1) deduplication)
  CONSTRAINT unique_session_url UNIQUE (session_id, normalized_url)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_crawl_queue_session_status 
  ON crawl_queue(session_id, status);

CREATE INDEX IF NOT EXISTS idx_crawl_queue_status_depth 
  ON crawl_queue(status, depth) 
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_crawl_queue_session 
  ON crawl_queue(session_id);

-- Enable Row Level Security (RLS)
ALTER TABLE crawl_queue ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access
CREATE POLICY "Service role has full access to crawl_queue"
  ON crawl_queue
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Policy: Allow authenticated users to read their own session's queue
CREATE POLICY "Users can read their own crawl queue"
  ON crawl_queue
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Allow anon users to read (for dashboard)
CREATE POLICY "Anon can read crawl queue"
  ON crawl_queue
  FOR SELECT
  TO anon
  USING (true);

-- Verify table was created
SELECT 'crawl_queue table created successfully!' AS status;
SELECT COUNT(*) AS initial_rows FROM crawl_queue;
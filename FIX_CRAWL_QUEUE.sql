-- =====================================================
-- FIX FOR EXISTING crawl_queue TABLE
-- =====================================================
-- Run this if you already created the crawl_queue table
-- but it's missing the parent_url column
-- =====================================================

-- Add parent_url column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='crawl_queue' 
        AND column_name='parent_url'
    ) THEN
        ALTER TABLE crawl_queue ADD COLUMN parent_url TEXT;
        RAISE NOTICE 'Added parent_url column to crawl_queue';
    ELSE
        RAISE NOTICE 'parent_url column already exists';
    END IF;
END $$;

-- Verify the fix
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'crawl_queue'
ORDER BY ordinal_position;

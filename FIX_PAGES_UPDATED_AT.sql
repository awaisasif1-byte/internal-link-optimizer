-- =====================================================
-- FIX: Add updated_at column to pages table
-- =====================================================
-- This fixes the error: Could not find the 'updated_at' 
-- column of 'pages' in the schema cache
-- =====================================================

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='pages' 
        AND column_name='updated_at'
    ) THEN
        ALTER TABLE pages ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Added updated_at column to pages table';
    ELSE
        RAISE NOTICE 'updated_at column already exists';
    END IF;
END $$;

-- Verify the fix
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'pages'
ORDER BY ordinal_position;

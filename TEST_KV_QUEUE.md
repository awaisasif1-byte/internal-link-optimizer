# KV QUEUE TEST GUIDE

## Test the KV Queue System

### 1. Test via Browser Console

Open your browser console and test the queue functions:

```javascript
// Test creating a project (this should work now)
const response = await fetch('https://mdkhcjbtgroxtqgvxpaw.supabase.co/functions/v1/make-server-4180e2ca/projects', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_ANON_KEY_HERE'
  },
  body: JSON.stringify({
    name: 'Test Project',
    description: 'Testing KV queue',
    url: 'https://example.com'
  })
});

const result = await response.json();
console.log('Project creation result:', result);
```

### 2. Check Supabase Logs

Go to:
- Supabase Dashboard
- Edge Functions
- Logs

Look for:
- ✅ `[Pro Crawler] ✅ Using KV-based queue - NO TABLE SETUP REQUIRED!`
- ❌ Any errors mentioning `kvQueue.enqueueUrls is not a function`

### 3. Verify Module Structure

The crawler_kv_queue.tsx file should have these exports:
- ✅ `export async function enqueueUrls(...)`
- ✅ `export async function dequeuePending(...)`
- ✅ `export async function urlExistsInQueue(...)`
- ✅ `export async function updateQueueItem(...)`
- ✅ `export async function markProcessing(...)`
- ✅ `export async function markCompleted(...)`
- ✅ `export async function markFailed(...)`
- ✅ `export async function countPending(...)`
- ✅ `export async function clearQueue(...)`

### 4. Test KV Store Directly

```javascript
// Test KV store (should work)
const testResponse = await fetch('https://mdkhcjbtgroxtqgvxpaw.supabase.co/functions/v1/make-server-4180e2ca/health');
console.log('Health check:', await testResponse.json());
```

## Common Issues

### Issue 1: "kvQueue.enqueueUrls is not a function"

**Cause:** The crawler_kv_queue.tsx file isn't being loaded correctly

**Solution:**
1. Check that all functions in `/supabase/functions/server/crawler_kv_queue.tsx` have `export` keyword
2. Verify the import in `/supabase/functions/server/crawler_production.tsx` is: `import * as kvQueue from './crawler_kv_queue.tsx';`
3. Redeploy the Edge Function

### Issue 2: "Failed to parse queue item"

**Cause:** JSONB values being treated as strings

**Solution:**
1. Verify `/supabase/functions/server/kv_store.tsx` line 86 returns: `return data ?? [];`
2. Verify queue functions don't use `JSON.parse()` or `JSON.stringify()`

### Issue 3: "Could not find the table 'public.crawl_queue'"

**Cause:** Still trying to use the old table-based queue

**Solution:**
1. Verify `/supabase/functions/server/crawler_production.tsx` imports: `import * as kvQueue from './crawler_kv_queue.tsx';`
2. Check that all references to `supabase.from('crawl_queue')` have been replaced with `kvQueue.*` functions

## Expected Behavior

When you create a project and start a crawl:

1. ✅ Project created successfully
2. ✅ Crawl session initialized
3. ✅ Homepage added to KV queue
4. ✅ Batches start processing
5. ✅ Pages crawled and saved
6. ✅ New URLs discovered and added to queue
7. ✅ Queue items marked as completed
8. ✅ Process continues until done

## Logs to Look For

**Success:**
```
[Pro Crawler] Starting for project abc123, max 100 pages
[Pro Crawler] ✅ Using KV-based queue - NO TABLE SETUP REQUIRED!
✅ Initialized session def456 for https://example.com
✅ Queue system: KV-based (no table required!)
🚀 [Batch def456] Starting batch processing
📊 Processing 1 URLs
✅ Crawled: https://example.com
➕ Added 15 URLs to queue
📊 Batch complete: 1 success, 0 failed (Total: 1/100)
```

**Failure:**
```
Error creating project: Error: API request failed: 500
kvQueue.enqueueUrls is not a function
```

If you see the failure, the module isn't loading correctly.

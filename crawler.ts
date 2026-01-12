/**
 * LOCAL CRAWLER - Runs on your PC (No timeout limits!)
 * 
 * Usage:
 *   npm run crawl -- --session YOUR_SESSION_ID
 * 
 * Example:
 *   npm run crawl -- --session abc123-def456-ghi789
 */

import { createClient } from '@supabase/supabase-js';

// Get environment variables
const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('❌ ERROR: Missing environment variables!');
  console.error('Please create a .env file with:');
  console.error('  SUPABASE_URL=https://your-project.supabase.co');
  console.error('  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// Get session ID from command line
const args = process.argv.slice(2);
const sessionArg = args.find(arg => arg.startsWith('--session'));
const SESSION_ID = sessionArg ? sessionArg.split('=')[1] || args[args.indexOf(sessionArg) + 1] : null;

if (!SESSION_ID) {
  console.error('❌ ERROR: Missing session ID!');
  console.error('Usage: npm run crawl -- --session YOUR_SESSION_ID');
  console.error('');
  console.error('Get the session ID from the browser URL when starting a crawl.');
  process.exit(1);
}

console.log('========================================');
console.log('🕷️  LOCAL CRAWLER STARTED');
console.log('========================================');
console.log(`📋 Session ID: ${SESSION_ID}`);
console.log(`🌐 Supabase URL: ${SUPABASE_URL}`);
console.log('========================================\n');

// Stats
let pagesProcessed = 0;
let totalLinks = 0;
let errors = 0;
let startTime = Date.now();

/**
 * Process a single URL from the queue
 */
async function processNextUrl(): Promise<boolean> {
  // Get next pending URL
  const { data: queueItem, error: queueError } = await supabase
    .from('crawl_queue')
    .select('*')
    .eq('session_id', SESSION_ID)
    .eq('status', 'pending')
    .order('depth', { ascending: true })
    .limit(1)
    .single();

  if (queueError || !queueItem) {
    console.log('\n📭 No more pending URLs in queue');
    return false; // No more URLs to process
  }

  // Mark as processing
  await supabase
    .from('crawl_queue')
    .update({ status: 'processing' })
    .eq('id', queueItem.id);

  // Get session details
  const { data: session } = await supabase
    .from('crawl_sessions')
    .select('*')
    .eq('id', SESSION_ID)
    .single();

  if (!session) {
    console.error('❌ Session not found');
    return false;
  }

  // Check if max pages reached
  if (session.pages_crawled >= session.max_pages) {
    console.log(`\n🏁 Max pages (${session.max_pages}) reached!`);
    return false;
  }

  try {
    console.log(`\n🌐 [${session.pages_crawled + 1}/${session.max_pages}] Fetching: ${queueItem.url}`);

    // Fetch the page
    const response = await fetch(queueItem.url, {
      headers: { 
        'User-Agent': 'Internal-Link-Analyzer-Bot/1.0',
        'Accept': 'text/html',
      },
      signal: AbortSignal.timeout(15000), // 15 second timeout per page
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();

    // Parse title
    const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/i);
    const title = titleMatch ? titleMatch[1].trim().substring(0, 255) : 'Untitled';

    // Parse meta description
    const descMatch = html.match(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']*)["']/i);
    const description = descMatch ? descMatch[1].substring(0, 500) : null;

    // Extract text content (remove scripts, styles, tags)
    const textContent = html
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const wordCount = textContent.split(/\s+/).length;

    // Extract internal links
    const linkRegex = /<a[^>]*href=["']([^"']*)["']/gi;
    const links: string[] = [];
    let match;

    // Get project base URL
    const { data: project } = await supabase
      .from('projects')
      .select('base_url')
      .eq('id', session.project_id)
      .single();

    while ((match = linkRegex.exec(html)) !== null) {
      const href = match[1];

      try {
        const absoluteUrl = new URL(href, queueItem.url).href;

        if (project && absoluteUrl.startsWith(project.base_url)) {
          // Clean URL (remove fragments and query params)
          const cleanUrl = absoluteUrl.split('#')[0].split('?')[0];
          if (!links.includes(cleanUrl) && cleanUrl !== queueItem.url) {
            links.push(cleanUrl);
          }
        }
      } catch (e) {
        // Invalid URL, skip
      }
    }

    console.log(`  ✅ Title: ${title}`);
    console.log(`  📊 ${wordCount} words, ${links.length} internal links found`);

    // Save page to database
    const { error: pageError } = await supabase
      .from('pages')
      .upsert({
        project_id: session.project_id,
        crawl_session_id: SESSION_ID,
        url: queueItem.url,
        title,
        meta_description: description,
        depth: queueItem.depth,
        status: response.status,
        word_count: wordCount,
        content: textContent.substring(0, 100000), // Limit to 100KB
      }, { onConflict: 'project_id,url' });

    if (pageError) {
      console.error(`  ❌ Failed to save page: ${pageError.message}`);
      errors++;
    } else {
      pagesProcessed++;

      // Add discovered links to queue
      let addedCount = 0;
      for (const link of links) {
        const { error: insertError } = await supabase
          .from('crawl_queue')
          .insert({
            session_id: SESSION_ID,
            url: link,
            depth: queueItem.depth + 1,
            status: 'pending',
          });

        if (!insertError) {
          addedCount++;
          totalLinks++;
        }
      }

      if (addedCount > 0) {
        console.log(`  ➕ Added ${addedCount} new URLs to queue`);
      }
    }

    // Mark queue item as completed
    await supabase
      .from('crawl_queue')
      .update({ status: 'completed' })
      .eq('id', queueItem.id);

    // Update session progress
    await supabase
      .from('crawl_sessions')
      .update({ pages_crawled: session.pages_crawled + 1 })
      .eq('id', SESSION_ID);

    return true; // Successfully processed

  } catch (fetchError: any) {
    console.error(`  ❌ Error: ${fetchError.message}`);
    errors++;

    // Mark as failed
    await supabase
      .from('crawl_queue')
      .update({ status: 'failed' })
      .eq('id', queueItem.id);

    return true; // Continue processing other URLs
  }
}

/**
 * Main crawler loop
 */
async function startCrawling() {
  // Verify session exists
  const { data: session, error: sessionError } = await supabase
    .from('crawl_sessions')
    .select('*')
    .eq('id', SESSION_ID)
    .single();

  if (sessionError || !session) {
    console.error('❌ Crawl session not found!');
    console.error('Make sure you started a crawl in the web app first.');
    process.exit(1);
  }

  console.log(`📦 Project ID: ${session.project_id}`);
  console.log(`🎯 Max Pages: ${session.max_pages}`);
  console.log(`📈 Already Crawled: ${session.pages_crawled}`);
  console.log('');

  // Update session status to running
  await supabase
    .from('crawl_sessions')
    .update({ status: 'running' })
    .eq('id', SESSION_ID);

  // Process URLs continuously
  let hasMore = true;
  while (hasMore) {
    hasMore = await processNextUrl();

    // Small delay between requests (be nice to servers)
    if (hasMore) {
      await new Promise(resolve => setTimeout(resolve, 500)); // 500ms delay
    }
  }

  // Mark session as completed
  await supabase
    .from('crawl_sessions')
    .update({ 
      status: 'completed',
      completed_at: new Date().toISOString()
    })
    .eq('id', SESSION_ID);

  // Print summary
  const duration = Math.round((Date.now() - startTime) / 1000);
  console.log('\n========================================');
  console.log('✅ CRAWL COMPLETED!');
  console.log('========================================');
  console.log(`📄 Pages Processed: ${pagesProcessed}`);
  console.log(`🔗 Links Discovered: ${totalLinks}`);
  console.log(`❌ Errors: ${errors}`);
  console.log(`⏱️  Duration: ${duration}s`);
  console.log(`⚡ Speed: ${(pagesProcessed / duration).toFixed(2)} pages/sec`);
  console.log('========================================\n');
}

// Handle Ctrl+C gracefully
process.on('SIGINT', async () => {
  console.log('\n\n⚠️  Crawler stopped by user');
  console.log('Marking session as stopped...');
  
  await supabase
    .from('crawl_sessions')
    .update({ 
      status: 'stopped',
      completed_at: new Date().toISOString()
    })
    .eq('id', SESSION_ID);
  
  console.log('✅ Session marked as stopped. You can resume later.');
  process.exit(0);
});

// Start!
startCrawling().catch(error => {
  console.error('\n❌ FATAL ERROR:', error);
  process.exit(1);
});

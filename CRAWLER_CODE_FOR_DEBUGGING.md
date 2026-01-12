# WEB CRAWLER CODE - FOR DEBUGGING

## Problem Description
The crawler stops after exactly 11 pages, despite having a limit of 100 pages and maxDepth of 10. The logs show it's finding links but not continuing to crawl them.

## System Context
- **Runtime**: Supabase Edge Functions (Deno)
- **Max Pages**: 100
- **Max Depth**: 10
- **Concurrent Requests**: 2
- **Features**: Sitemap discovery, robots.txt parsing, real-time database saving

---

## FILE 1: /supabase/functions/server/crawler.tsx

```typescript
/**
 * TypeScript Web Crawler for Internal Link Analysis
 * Runs in Supabase Edge Function (Deno runtime)
 * Features: Sitemap Discovery, JS Rendering, Link Analysis
 */

import { parseSitemap, parseRobotsTxt, isUrlAllowed, type RobotsRule } from './sitemap_parser.tsx';
import {
  extractStructuredContent,
  extractKeywords,
  extractEntities,
  createSemanticVector,
  storePageAnalysis,
  updatePageMetadata,
} from './semantic_analyzer.tsx';

interface CrawlPage {
  url: string;
  depth: number;
  title: string;
  meta_description?: string;
  status: number;
  content: string;
  internal_links: string[];
  content_internal_links?: string[];
  external_links?: string[];
  link_equity_score: number;
  broken_count: number;
  score: number;
  page_type?: string;
  keywords?: string[];
  anchor_texts?: Map<string, string>;
  opps?: Array<{
    from: string;
    to: string;
    anchor: string;
    type: string;
    priority: string;
  }>;
}

interface CrawlOptions {
  maxPages: number;
  maxDepth: number;
  baseUrl: string;
  projectId: string;
  sessionId: string;
  onProgress?: (crawled: number, total: number) => void;
  supabaseClient?: any;
  enableJsRendering?: boolean;
  discoverSitemap?: boolean;
  realtimeSave?: boolean;
}

export class WebCrawler {
  private visited = new Set<string>();
  private queue: Array<{ url: string; depth: number }> = [];
  private queued = new Set<string>();
  private pages: Map<string, CrawlPage> = new Map();
  private baseUrl: string;
  private baseDomain: string;
  private maxPages: number;
  private maxDepth: number;
  private shouldStop = false;
  private sessionId: string;
  private projectId: string;
  private supabase: any;
  private enableJsRendering: boolean;
  private discoverSitemap: boolean;
  private realtimeSave: boolean;
  private sitemapUrls: Set<string> = new Set();
  private sitemapTotalPages = 0;
  private robotsRules: RobotsRule | null = null;
  private robotsDisallowedCount = 0;
  private browser: any = null;

  constructor(options: CrawlOptions) {
    this.baseUrl = this.normalizeUrl(options.baseUrl);
    this.baseDomain = new URL(this.baseUrl).hostname;
    this.maxPages = options.maxPages;
    this.maxDepth = options.maxDepth;
    this.sessionId = options.sessionId;
    this.projectId = options.projectId;
    this.supabase = options.supabaseClient;
    this.enableJsRendering = options.enableJsRendering || false;
    this.discoverSitemap = options.discoverSitemap !== false;
    this.realtimeSave = options.realtimeSave !== false;
    
    // Start with base URL
    this.queue.push({ url: this.baseUrl, depth: 0 });
    this.queued.add(this.baseUrl);
  }

  stop() {
    console.log('Crawler stop requested');
    this.shouldStop = true;
  }

  private isSitemapUrl(url: string): boolean {
    const urlLower = url.toLowerCase();
    return (
      urlLower.endsWith('.xml') ||
      urlLower.includes('/sitemap') ||
      urlLower.includes('sitemap.xml') ||
      urlLower.includes('sitemap_index') ||
      urlLower.endsWith('.rss')
    );
  }

  private async discoverSitemapUrls(): Promise<void> {
    if (!this.discoverSitemap) {
      console.log('Sitemap discovery disabled');
      return;
    }

    const sitemapResult = await parseSitemap(this.baseUrl);
    
    if (sitemapResult.sitemapFound) {
      console.log(`✅ Sitemap found at ${sitemapResult.sitemapUrl}`);
      console.log(`📊 Total pages in sitemap: ${sitemapResult.totalPages}`);
      
      this.sitemapTotalPages = sitemapResult.totalPages;
      sitemapResult.urls.forEach(url => this.sitemapUrls.add(url));
      console.log(`📊 Sitemap will be used for orphan detection only (not pre-queuing URLs)`);
    } else {
      console.log('ℹ️ No sitemap found, will rely on crawling');
    }
  }

  async crawl(): Promise<CrawlPage[]> {
    console.log(`Starting crawl: maxPages=${this.maxPages}, maxDepth=${this.maxDepth}`);
    console.log(`JS Rendering: ${this.enableJsRendering ? 'Enabled' : 'Disabled'}`);
    console.log(`Sitemap Discovery: ${this.discoverSitemap ? 'Enabled' : 'Disabled'}`);
    
    this.robotsRules = await parseRobotsTxt(this.baseUrl);
    await this.discoverSitemapUrls();
    
    let lastProgressUpdate = 0;
    const CONCURRENT_REQUESTS = 2;
    let emptyBatchCount = 0;

    while (this.queue.length > 0 && this.visited.size < this.maxPages) {
      if (this.shouldStop) {
        console.log(`Crawl stopped by user after ${this.visited.size} pages`);
        break;
      }
      
      if (this.visited.size > 0 && this.visited.size % 10 === 0) {
        console.log(`\n📊 STATUS: Visited ${this.visited.size} pages, Queue has ${this.queue.length} URLs`);
        console.log(`   Next 3 in queue: ${this.queue.slice(0, 3).map(q => `${q.url} (d:${q.depth})`).join(', ')}`);
      }
      
      // Check database for stop signal every 5 pages
      if (this.supabase && this.sessionId && this.visited.size % 5 === 0) {
        try {
          const { data: session } = await this.supabase
            .from('crawl_sessions')
            .select('status')
            .eq('id', this.sessionId)
            .single();
          
          if (session?.status === 'stopped') {
            console.log(`[Session ${this.sessionId}] Stop signal detected from database`);
            this.shouldStop = true;
            break;
          }
        } catch (error: any) {
          console.error('Error checking stop status:', error);
        }
      }
      
      // Update progress in database every 3 pages
      if (this.supabase && this.sessionId && this.visited.size - lastProgressUpdate >= 3) {
        try {
          await this.supabase
            .from('crawl_sessions')
            .update({ pages_crawled: this.visited.size })
            .eq('id', this.sessionId);
          
          lastProgressUpdate = this.visited.size;
          console.log(`[Session ${this.sessionId}] Progress update: ${this.visited.size} pages crawled`);
        } catch (error: any) {
          console.error('Error updating progress:', error);
        }
      }

      // Process multiple pages concurrently
      const batch: Array<{ url: string; depth: number }> = [];
      
      while (batch.length < CONCURRENT_REQUESTS && this.queue.length > 0 && this.visited.size + batch.length < this.maxPages) {
        const item = this.queue.shift()!;
        
        if (this.visited.has(item.url) || item.depth > this.maxDepth || this.isSitemapUrl(item.url)) {
          continue;
        }
        
        if (this.robotsRules && !isUrlAllowed(item.url, this.robotsRules)) {
          console.log(`🤖 Skipping ${item.url} (blocked by robots.txt)`);
          this.robotsDisallowedCount++;
          continue;
        }
        
        batch.push(item);
      }
      
      if (batch.length === 0) {
        emptyBatchCount++;
        
        console.log(`\n⚠️  Empty batch #${emptyBatchCount}`);
        console.log(`   Queue size: ${this.queue.length}`);
        console.log(`   Visited size: ${this.visited.size}`);
        console.log(`   Max pages: ${this.maxPages}`);
        console.log(`   Max depth: ${this.maxDepth}`);
        
        if (this.queue.length > 0) {
          const sampleSize = Math.min(10, this.queue.length);
          console.log(`\n   🔍 Analyzing next ${sampleSize} URLs in queue:`);
          for (let i = 0; i < sampleSize; i++) {
            const item = this.queue[i];
            const reasons: string[] = [];
            if (this.visited.has(item.url)) reasons.push('✗ already visited');
            if (item.depth > this.maxDepth) reasons.push(`✗ depth ${item.depth} > max ${this.maxDepth}`);
            if (this.isSitemapUrl(item.url)) reasons.push('✗ sitemap/xml file');
            if (this.robotsRules && !isUrlAllowed(item.url, this.robotsRules)) reasons.push('✗ blocked by robots.txt');
            
            const status = reasons.length > 0 ? reasons.join(', ') : '✓ OK (should be crawled!)';
            console.log(`   ${i + 1}. [depth:${item.depth}] ${item.url}`);
            console.log(`      → ${status}`);
          }
        } else {
          console.log(`   ⚠️  Queue is completely empty!`);
        }
        
        if (emptyBatchCount > 10) {
          console.log(`\n🛑 Stopping crawl - too many empty batches. Queue might only contain filtered URLs.`);
          break;
        }
        continue;
      }
      
      emptyBatchCount = 0;
      
      console.log(`\n[${this.visited.size}/${this.maxPages}] Processing batch of ${batch.length} pages...`);
      console.log(`   Queue size: ${this.queue.length} | Depth range: ${Math.min(...batch.map(b => b.depth))}-${Math.max(...batch.map(b => b.depth))}`);
      
      batch.forEach(({ url, depth }) => {
        console.log(`   → Crawling: ${url} (depth: ${depth})`);
      });
      
      const batchResults = await Promise.allSettled(
        batch.map(({ url, depth }) => 
          this.crawlPage(url, depth).catch(error => {
            console.error(`Error crawling ${url}:`, error.message);
            return null;
          })
        )
      );
      
      let totalLinksFound = 0;
      let totalLinksAdded = 0;
      
      for (let i = 0; i < batchResults.length; i++) {
        const result = batchResults[i];
        const { url, depth } = batch[i];
        
        if (result.status === 'fulfilled' && result.value) {
          const page = result.value;
          this.pages.set(url, page);
          this.visited.add(url);
          
          console.log(`\n  🔍 Page: ${page.title}`);
          console.log(`     URL: ${url}`);
          console.log(`     Status: ${page.status}`);
          console.log(`     Found ${page.internal_links.length} internal links total`);
          console.log(`     Content links: ${page.content_internal_links?.length || 0}`);
          console.log(`     External links: ${page.external_links?.length || 0}`);
          
          if (page.internal_links.length > 0) {
            console.log(`     First 10 internal links found:`);
            page.internal_links.slice(0, 10).forEach((link, idx) => {
              const isInQueue = this.queue.some(q => q.url === link);
              const wasVisited = this.visited.has(link);
              const status = wasVisited ? '[VISITED]' : isInQueue ? '[IN QUEUE]' : '[NEW]';
              console.log(`       ${idx + 1}. ${status} ${link}`);
            });
          } else {
            console.log(`     ⚠️  WARNING: No internal links found on this page!`);
          }
          
          let addedLinks = 0;
          let skippedAlreadyVisited = 0;
          let skippedSitemap = 0;
          let skippedSelfReference = 0;
          let skippedAlreadyQueued = 0;
          
          for (const link of page.internal_links) {
            const normalizedLink = this.normalizeUrl(link);
            
            if (normalizedLink.includes('sitemap')) {
              skippedSitemap++;
              continue;
            }
            
            if (this.visited.has(normalizedLink)) {
              skippedAlreadyVisited++;
              continue;
            }
            
            if (this.queued.has(normalizedLink)) {
              skippedAlreadyQueued++;
              continue;
            }
            
            if (normalizedLink === this.normalizeUrl(url)) {
              skippedSelfReference++;
              continue;
            }
            
            this.queue.push({ url: normalizedLink, depth: depth + 1 });
            this.queued.add(normalizedLink);
            addedLinks++;
          }
          
          totalLinksFound += page.internal_links.length;
          totalLinksAdded += addedLinks;
          
          console.log(`     ✅ Added ${addedLinks} new links to queue (depth ${depth + 1})`);
          console.log(`     ⏭️  Skipped: ${skippedAlreadyVisited} visited, ${skippedAlreadyQueued} already queued, ${skippedSitemap} sitemap, ${skippedSelfReference} self-reference`);
          
          if (this.realtimeSave) {
            await this.saveAndAnalyzePage(page);
          }
        } else {
          console.log(`  ❌ Failed to crawl: ${url}`);
        }
      }
      
      console.log(`\n📊 BATCH COMPLETE: Found ${totalLinksFound} links, added ${totalLinksAdded} to queue`);
      console.log(`   Queue now has ${this.queue.length} URLs, visited ${this.visited.size}/${this.maxPages}`);
    }

    const result = Array.from(this.pages.values());
    
    if (!this.shouldStop) {
      this.calculatePageRank();
      this.calculateHealthScores(result);
      this.identifyOrphanPages();
    }
    
    this.visited.clear();
    this.queue = [];
    this.pages.clear();
    this.sitemapUrls.clear();

    console.log(`Crawl finished: ${result.length} pages`);
    return result;
  }

  private identifyOrphanPages() {
    if (this.sitemapUrls.size === 0) return;
    const crawledUrls = new Set(Array.from(this.pages.keys()));
    const orphans: string[] = [];
    for (const sitemapUrl of this.sitemapUrls) {
      if (!crawledUrls.has(sitemapUrl)) {
        orphans.push(sitemapUrl);
      }
    }
    if (orphans.length > 0) {
      console.log(`🚨 Found ${orphans.length} orphan pages (in sitemap but no internal links):`);
      orphans.slice(0, 10).forEach(url => console.log(`  - ${url}`));
    }
  }

  private async crawlPage(url: string, depth: number): Promise<CrawlPage> {
    return await this.crawlPageWithFetch(url, depth);
  }

  private async crawlPageWithFetch(url: string, depth: number): Promise<CrawlPage> {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Internal-Link-Analyzer-Bot/1.0',
      },
      signal: AbortSignal.timeout(20000),
    });

    const status = response.status;
    const html = await response.text();

    return this.parseHtml(url, depth, status, html);
  }

  private parseHtml(url: string, depth: number, status: number, html: string): CrawlPage {
    const title = this.extractTitle(html);
    const metaDescription = this.extractMetaDescription(html);
    
    const cleanedHtml = html
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    
    const { links, anchorTexts } = this.extractLinksWithAnchors(html, url);
    const contentLinks = this.extractContentLinks(html, url);
    const externalLinks = this.extractExternalLinks(html, url);
    
    const textContent = cleanedHtml.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    const wordCount = textContent.split(/\s+/).filter(w => w.length > 0).length;
    const pageType = this.classifyPageType(url, wordCount, links.length, contentLinks.length, html);

    return {
      url,
      depth,
      title,
      meta_description: metaDescription,
      status,
      content: cleanedHtml,
      internal_links: links,
      content_internal_links: contentLinks,
      external_links: externalLinks,
      anchor_texts: anchorTexts,
      link_equity_score: 0,
      broken_count: 0,
      score: 0,
      page_type: pageType,
    };
  }
  
  private classifyPageType(url: string, wordCount: number, totalLinks: number, contentLinks: number, html: string): string {
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname.toLowerCase();
      const pathSegments = path.split('/').filter(s => s.length > 0);
      
      if (path === '/' || path === '') return 'homepage';
      
      const categoryPatterns = [
        '/category/', '/categories/', '/tag/', '/tags/', 
        '/archive/', '/archives/', '/topic/', '/topics/',
        '/blog/', '/news/', '/articles/', '/posts/'
      ];
      
      const isCategoryUrl = categoryPatterns.some(pattern => path.includes(pattern));
      const linkToContentRatio = wordCount > 0 ? totalLinks / wordCount : 0;
      const hasHighLinkDensity = linkToContentRatio > 0.05;
      const hasThinContent = wordCount < 300;
      const hasListStructure = (html.match(/<li[^>]*>/gi) || []).length > 10;
      
      if (isCategoryUrl || (hasHighLinkDensity && hasThinContent && hasListStructure)) {
        return 'category';
      }
      
      const productPatterns = ['/product/', '/products/', '/item/', '/shop/'];
      const hasProductUrl = productPatterns.some(pattern => path.includes(pattern));
      const hasPrice = html.match(/\$\d+|\d+\.\d{2}|price/i) !== null;
      const hasAddToCart = html.match(/add.{0,10}cart|buy.now/i) !== null;
      
      if (hasProductUrl || (hasPrice && hasAddToCart && wordCount > 100)) {
        return 'product';
      }
      
      const hasRichContent = wordCount >= 300;
      const hasGoodContentLinkRatio = contentLinks > 0 && contentLinks < wordCount / 100;
      const isDeepInHierarchy = pathSegments.length >= 2;
      
      if (hasRichContent && (hasGoodContentLinkRatio || isDeepInHierarchy)) {
        return 'content';
      }
      
      return 'other';
    } catch (error) {
      console.error('Error classifying page type:', error);
      return 'other';
    }
  }

  private extractTitle(html: string): string {
    const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/i);
    return titleMatch ? titleMatch[1].trim() : 'No Title';
  }

  private extractMetaDescription(html: string): string | undefined {
    const metaMatch = html.match(/<meta\s+name=["']description["']\s+content=["'](.*?)["']\s*\/?>/i);
    return metaMatch ? metaMatch[1].trim() : undefined;
  }

  private extractLinksWithAnchors(html: string, baseUrl: string): { links: string[], anchorTexts: Map<string, string> } {
    const links: string[] = [];
    const anchorTexts = new Map<string, string>();
    
    const sampleAnchorTags = html.match(/<a[^>]*>.*?<\/a>/gi);
    if (sampleAnchorTags && sampleAnchorTags.length > 0) {
      console.log(`\n  🔬 DEBUG: Found ${sampleAnchorTags.length} <a> tags in HTML`);
      console.log(`  First 3 raw anchor tags:`);
      sampleAnchorTags.slice(0, 3).forEach((tag, idx) => {
        console.log(`    ${idx + 1}. ${tag.substring(0, 150)}...`);
      });
    } else {
      console.log(`\n  ⚠️  DEBUG: NO <a> tags found in HTML at all!`);
    }
    
    const linkRegex = /<a\s+(?:[^>]*?\s+)?href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
    let match;
    let matchCount = 0;

    while ((match = linkRegex.exec(html)) !== null) {
      matchCount++;
      try {
        const href = match[1] || match[2] || match[3];
        
        if (!href || href.trim().length === 0) {
          console.log(`  ⚠️  Skipping empty href in match ${matchCount}`);
          continue;
        }
        
        const startPos = match.index + match[0].length;
        const closeTagMatch = html.substring(startPos).match(/([\s\S]*?)<\/a>/i);
        const anchorHtml = closeTagMatch ? closeTagMatch[1] : '';
        const anchorText = anchorHtml.replace(/<[^>]+>/g, '').trim();
        
        const absoluteUrl = this.resolveUrl(href, baseUrl);
        
        if (this.isInternalLink(absoluteUrl)) {
          const normalized = this.normalizeUrl(absoluteUrl);
          if (!links.includes(normalized)) {
            links.push(normalized);
            anchorTexts.set(normalized, anchorText);
          }
        } else {
          if (matchCount <= 5) {
            console.log(`  ⚠️  Link ${matchCount}: ${href} → Not internal (external or invalid)`);
          }
        }
      } catch (error) {
        console.log(`  ❌ Error processing link ${matchCount}: ${error}`);
      }
    }
    
    console.log(`  📊 Regex matched ${matchCount} hrefs, extracted ${links.length} internal links`);
    return { links, anchorTexts };
  }

  private extractContentLinks(html: string, baseUrl: string): string[] {
    let contentHtml = html;
    
    contentHtml = contentHtml.replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '');
    contentHtml = contentHtml.replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, '');
    contentHtml = contentHtml.replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, '');
    contentHtml = contentHtml.replace(/<aside[^>]*>[\s\S]*?<\/aside>/gi, '');
    contentHtml = contentHtml.replace(/<div[^>]*(?:class|id)=["'][^"']*(?:nav|menu|sidebar|header|footer)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    const contentLinks: string[] = [];
    const linkRegex = /<a\s+(?:[^>]*?\s+)?href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
    let match;

    while ((match = linkRegex.exec(contentHtml)) !== null) {
      try {
        const href = match[1] || match[2] || match[3];
        if (!href || href.trim().length === 0) continue;
        
        const absoluteUrl = this.resolveUrl(href, baseUrl);
        
        if (this.isInternalLink(absoluteUrl)) {
          const normalized = this.normalizeUrl(absoluteUrl);
          if (!contentLinks.includes(normalized)) {
            contentLinks.push(normalized);
          }
        }
      } catch (error) {
        // Skip invalid URLs
      }
    }

    return contentLinks;
  }

  private extractExternalLinks(html: string, baseUrl: string): string[] {
    let contentHtml = html;
    
    contentHtml = contentHtml.replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '');
    contentHtml = contentHtml.replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, '');
    contentHtml = contentHtml.replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, '');
    contentHtml = contentHtml.replace(/<aside[^>]*>[\s\S]*?<\/aside>/gi, '');
    contentHtml = contentHtml.replace(/<div[^>]*(?:class|id)=["'][^"']*(?:nav|menu|sidebar|header|footer)[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '');
    
    const externalLinks: string[] = [];
    const linkRegex = /<a\s+(?:[^>]*?\s+)?href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
    let match;

    while ((match = linkRegex.exec(contentHtml)) !== null) {
      try {
        const href = match[1] || match[2] || match[3];
        if (!href || href.trim().length === 0) continue;
        
        const absoluteUrl = this.resolveUrl(href, baseUrl);
        
        if (!this.isInternalLink(absoluteUrl)) {
          const normalized = this.normalizeUrl(absoluteUrl);
          if (!externalLinks.includes(normalized)) {
            externalLinks.push(normalized);
          }
        }
      } catch (error) {
        // Skip invalid URLs
      }
    }

    return externalLinks;
  }

  private resolveUrl(href: string, baseUrl: string): string {
    if (href.startsWith('http://') || href.startsWith('https://')) {
      return href;
    }

    if (href.startsWith('//')) {
      return 'https:' + href;
    }

    if (href.startsWith('/')) {
      const base = new URL(baseUrl);
      return `${base.protocol}//${base.host}${href}`;
    }

    const base = new URL(baseUrl);
    const basePath = base.pathname.endsWith('/') 
      ? base.pathname 
      : base.pathname.substring(0, base.pathname.lastIndexOf('/') + 1);
    
    return `${base.protocol}//${base.host}${basePath}${href}`;
  }

  private isInternalLink(url: string): boolean {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname === this.baseDomain;
    } catch {
      return false;
    }
  }

  private normalizeUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      urlObj.hash = '';
      let pathname = urlObj.pathname;
      if (pathname !== '/' && pathname.endsWith('/')) {
        pathname = pathname.slice(0, -1);
      }
      urlObj.pathname = pathname;
      return urlObj.toString();
    } catch {
      return url;
    }
  }

  private calculatePageRank() {
    const dampingFactor = 0.85;
    const iterations = 10;
    
    const urls = Array.from(this.pages.keys());
    const scores = new Map<string, number>();
    urls.forEach(url => scores.set(url, 1.0));

    const incomingLinks = new Map<string, string[]>();
    urls.forEach(url => incomingLinks.set(url, []));
    
    for (const [fromUrl, page] of this.pages) {
      for (const toUrl of page.internal_links) {
        if (incomingLinks.has(toUrl)) {
          incomingLinks.get(toUrl)!.push(fromUrl);
        }
      }
    }

    for (let i = 0; i < iterations; i++) {
      const newScores = new Map<string, number>();

      for (const url of urls) {
        let score = (1 - dampingFactor);
        const incoming = incomingLinks.get(url) || [];

        for (const fromUrl of incoming) {
          const fromPage = this.pages.get(fromUrl);
          const outgoingCount = fromPage?.internal_links.length || 1;
          score += dampingFactor * (scores.get(fromUrl) || 0) / outgoingCount;
        }

        newScores.set(url, score);
      }

      scores.clear();
      newScores.forEach((score, url) => scores.set(url, score));
    }

    const maxScore = Math.max(...Array.from(scores.values()));
    for (const [url, score] of scores) {
      const page = this.pages.get(url);
      if (page) {
        page.link_equity_score = Math.round((score / maxScore) * 100);
      }
    }
  }

  private calculateHealthScores(pages: CrawlPage[]) {
    for (const page of pages) {
      let score = 100;

      if (page.status !== 200) score -= 50;
      if (!page.title || page.title === 'No Title') score -= 10;
      if (page.internal_links.length === 0) {
        score -= 20;
      } else if (page.internal_links.length < 3) {
        score -= 10;
      }
      if (page.internal_links.length > 100) score -= 15;
      if (page.content.length < 100) score -= 15;

      page.score = Math.max(0, score);
    }
  }

  private async saveAndAnalyzePage(page: CrawlPage) {
    if (!this.supabase) return;
    
    try {
      const pageData: any = {
        project_id: this.projectId,
        crawl_session_id: this.sessionId,
        url: page.url,
        title: page.title,
        depth: page.depth,
        status: page.status,
        content: page.content?.substring(0, 10000),
        link_equity_score: page.link_equity_score || 0,
        health_score: page.score || 0,
        broken_count: page.broken_count || 0,
      };
      
      const { data: savedPage, error } = await this.supabase
        .from('pages')
        .insert([pageData])
        .select()
        .maybeSingle();
      
      if (error) {
        throw error;
      } else if (savedPage) {
        console.log(`   Saved: ${page.url}`);
      }
    } catch (error: any) {
      console.error(`  ❌ Error saving ${page.url}:`, error.message);
    }
  }
}
```

---

## HOW IT'S CALLED

From `/supabase/functions/server/index.tsx`:

```typescript
// POST /projects/:id/crawl/auto
app.post('/make-server-4180e2ca/projects/:id/crawl/auto', async (c) => {
  try {
    const body = await c.req.json();
    const maxPages = Math.min(body.maxPages || 50, 100); // Limit to 100
    const enableJsRendering = body.enableJsRendering || false;
    const discoverSitemap = body.discoverSitemap !== false;
    
    // Create session
    const { data: session, error: sessionError } = await supabase
      .from('crawl_sessions')
      .insert([{
        project_id: projectId,
        status: 'running',
        pages_crawled: 0,
        started_at: new Date().toISOString(),
      }])
      .select()
      .single();
    
    // Launch async crawl
    (async () => {
      const crawler = new WebCrawler({
        baseUrl: project.url,
        maxPages: maxPages,
        maxDepth: 10,
        sessionId: session.id,
        projectId: project.id,
        supabaseClient: supabase,
        enableJsRendering,
        discoverSitemap,
        realtimeSave: true,
      });
      
      const pages = await crawler.crawl();
      await saveCrawlerResults(session.id, project.id, pages);
      
      await supabase
        .from('crawl_sessions')
        .update({ status: 'completed', pages_crawled: pages.length })
        .eq('id', session.id);
    })();
    
    return c.json({ success: true, data: session });
  } catch (error) {
    return c.json({ error: error.message }, 500);
  }
});
```

---

## SYMPTOMS

1. **Crawls exactly 11 pages** then stops
2. **Logs show**:
   - Links are being found (10-30+ links per page)
   - Links are being added to queue
   - Queue size increases (e.g., "Queue now has 45 URLs")
   - But then it stops processing
3. **No errors** - just stops silently
4. **Database saves work** - 11 pages are saved successfully

---

## QUESTIONS FOR OTHER AI

1. Why does the crawler stop at exactly 11 pages?
2. The queue has URLs but they're not being processed - why?
3. Is there a logic error in the main crawl loop (lines 137-297)?
4. Could the database calls be causing timeouts?
5. Is the `normalizeUrl` function causing issues with URL matching?

---

## TEST WEBSITE

The crawler is being tested against real websites (user provides their own URL).

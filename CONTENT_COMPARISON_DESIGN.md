# 🎯 CONTENT COMPARISON PANEL - Design Spec

## 💡 CONCEPT

Transform **Content Overview** into a **Side-by-Side Content Comparison Tool** that shows:
- **Left Panel:** Source page (where to add the link FROM)
- **Right Panel:** Target page (where to link TO)
- **Highlighted Matches:** Paragraphs/sections with shared keywords/context
- **Actionable Insights:** Exactly where to insert the link

---

## 🎨 UI LAYOUT

```
┌─────────────────────────────────────────────────────────────────┐
│  Content Comparison                                    [X Close] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Suggestion: Link these pages (Relevance: 87%)                   │
│  Shared Topics: internal linking, seo strategy, link building    │
│                                                                   │
├──────────────────────────┬──────────────────────────────────────┤
│  FROM (Source Page)      │  TO (Target Page)                    │
├──────────────────────────┼──────────────────────────────────────┤
│  📄 SEO Best Practices   │  📄 Internal Linking Guide           │
│  /blog/seo-tips          │  /guide/internal-linking             │
│  Depth: 2 | Equity: 65   │  Depth: 1 | Equity: 82              │
├──────────────────────────┼──────────────────────────────────────┤
│                          │                                      │
│  <h1>SEO Tips</h1>       │  <h1>Internal Linking</h1>           │
│                          │                                      │
│  <p>Introduction to SEO  │  <p>Master internal linking          │
│  and website optimization│  strategies for better SEO           │
│  ...</p>                 │  results...</p>                      │
│                          │                                      │
│  🟢 MATCH (85%)          │  🟢 MATCH (85%)                      │
│  <p>One of the most      │  <p>Building a strong                │
│  important aspects is    │  internal linking structure          │
│  ✨ internal linking ✨  │  ✨ internal linking ✨              │
│  which helps search      │  connects your pages and             │
│  engines understand      │  distributes link equity             │
│  your site structure     │  across your website                 │
│  and content...</p>      │  effectively...</p>                  │
│                          │                                      │
│  👉 [Add Link Here]      │                                      │
│                          │                                      │
│  <p>Regular content...</p>│  <p>More details...</p>              │
│                          │                                      │
│  🟡 MATCH (62%)          │  🟡 MATCH (62%)                      │
│  <p>Link building and    │  <p>Strategic link                   │
│  ✨ anchor text ✨       │  placement with proper               │
│  optimization...</p>     │  ✨ anchor text ✨...</p>            │
│                          │                                      │
└──────────────────────────┴──────────────────────────────────────┘
│                                                                   │
│  💡 Recommendation:                                               │
│  Add link in paragraph 2 with anchor text: "internal linking     │
│  strategy" - High contextual relevance (85% match)                │
│                                                                   │
│  [Copy Suggested Anchor] [Mark as Implemented] [Dismiss]         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 DATA REQUIREMENTS

### **Input (from AI Suggestion):**
```typescript
{
  from_url: string,
  to_url: string,
  suggested_anchor: string,
  relevance_score: number,
  shared_terms: string[]
}
```

### **API Response (New Endpoint):**
```typescript
GET /projects/:id/compare-content?from_url=X&to_url=Y

Response: {
  source_page: {
    url: string,
    title: string,
    depth: number,
    link_equity_score: number,
    full_content: string,        // 15K chars
    paragraphs: Paragraph[]       // Split into paragraphs
  },
  target_page: {
    url: string,
    title: string,
    depth: number,
    link_equity_score: number,
    full_content: string,
    paragraphs: Paragraph[]
  },
  matches: ContentMatch[],        // Paragraph pairs with similarity scores
  shared_terms: string[],         // Top 10 shared keywords
  suggested_anchor: string,
  best_insertion_point: {
    paragraph_index: number,      // Which paragraph to add link
    position: 'start' | 'middle' | 'end',
    confidence: number            // 0-100
  }
}

interface Paragraph {
  index: number,
  text: string,
  keywords: string[],
  similarity_score?: number       // Match score with target
}

interface ContentMatch {
  source_paragraph_index: number,
  target_paragraph_index: number,
  similarity_score: number,       // 0-100
  shared_keywords: string[],
  match_type: 'high' | 'medium' | 'low'  // >70 | 50-70 | <50
}
```

---

## 🧠 BACKEND ALGORITHM

### **Step 1: Paragraph-Level Splitting**
```typescript
function splitIntoParagraphs(htmlContent: string): Paragraph[] {
  // Extract text from HTML
  const text = stripHtml(htmlContent);
  
  // Split by double newlines or paragraph tags
  const paragraphs = text
    .split(/\n\n+|<\/p>/)
    .map(p => p.trim())
    .filter(p => p.length > 50); // Min 50 chars
  
  return paragraphs.map((text, index) => ({
    index,
    text,
    keywords: extractKeywords(text)
  }));
}
```

### **Step 2: Paragraph Matching (TF-IDF)**
```typescript
function findMatchingParagraphs(
  sourceParagraphs: Paragraph[],
  targetParagraphs: Paragraph[],
  sharedTerms: string[]
): ContentMatch[] {
  const matches: ContentMatch[] = [];
  
  // Build TF-IDF analyzer
  const analyzer = new TFIDFAnalyzer();
  
  // Compare each source paragraph with all target paragraphs
  for (let i = 0; i < sourceParagraphs.length; i++) {
    for (let j = 0; j < targetParagraphs.length; j++) {
      const similarity = analyzer.cosineSimilarity(
        sourceParagraphs[i].text,
        targetParagraphs[j].text
      );
      
      // Only keep matches > 40% similarity
      if (similarity > 0.4) {
        const sharedKeywords = findSharedKeywords(
          sourceParagraphs[i].keywords,
          targetParagraphs[j].keywords,
          sharedTerms
        );
        
        matches.push({
          source_paragraph_index: i,
          target_paragraph_index: j,
          similarity_score: Math.round(similarity * 100),
          shared_keywords: sharedKeywords,
          match_type: similarity > 0.7 ? 'high' : 
                      similarity > 0.5 ? 'medium' : 'low'
        });
      }
    }
  }
  
  // Sort by similarity (highest first)
  return matches.sort((a, b) => b.similarity_score - a.similarity_score);
}
```

### **Step 3: Best Insertion Point**
```typescript
function findBestInsertionPoint(
  sourceParagraphs: Paragraph[],
  matches: ContentMatch[]
): InsertionPoint {
  // Get the highest similarity match
  const bestMatch = matches[0];
  
  if (!bestMatch) {
    // Fallback: first paragraph
    return {
      paragraph_index: 0,
      position: 'end',
      confidence: 50
    };
  }
  
  const paragraph = sourceParagraphs[bestMatch.source_paragraph_index];
  
  // Check if shared keywords appear in first/middle/end of paragraph
  const position = findKeywordPosition(
    paragraph.text,
    bestMatch.shared_keywords
  );
  
  return {
    paragraph_index: bestMatch.source_paragraph_index,
    position,
    confidence: bestMatch.similarity_score
  };
}

function findKeywordPosition(
  text: string,
  keywords: string[]
): 'start' | 'middle' | 'end' {
  const third = Math.floor(text.length / 3);
  
  for (const keyword of keywords) {
    const index = text.toLowerCase().indexOf(keyword.toLowerCase());
    if (index !== -1) {
      if (index < third) return 'start';
      if (index < third * 2) return 'middle';
      return 'end';
    }
  }
  
  return 'middle'; // Default
}
```

---

## 🎨 FRONTEND COMPONENT

### **Component Structure:**
```typescript
interface ContentComparisonProps {
  projectId: string;
  fromUrl: string;
  toUrl: string;
  suggestedAnchor: string;
  onClose: () => void;
}

export function ContentComparison({
  projectId,
  fromUrl,
  toUrl,
  suggestedAnchor,
  onClose
}: ContentComparisonProps) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchComparisonData();
  }, [fromUrl, toUrl]);
  
  async function fetchComparisonData() {
    const response = await api.compareContent(projectId, fromUrl, toUrl);
    setData(response);
    setLoading(false);
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b">
          <h2>Content Comparison</h2>
          <div className="flex gap-2 mt-2">
            {data?.shared_terms.map(term => (
              <span key={term} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                {term}
              </span>
            ))}
          </div>
        </div>
        
        {/* Side-by-Side Panels */}
        <div className="flex-1 grid grid-cols-2 divide-x overflow-hidden">
          {/* Left: Source Page */}
          <div className="overflow-y-auto p-6">
            <PageHeader page={data?.source_page} label="FROM" />
            <ContentParagraphs
              paragraphs={data?.source_page.paragraphs}
              matches={data?.matches}
              side="source"
              bestInsertionPoint={data?.best_insertion_point}
            />
          </div>
          
          {/* Right: Target Page */}
          <div className="overflow-y-auto p-6">
            <PageHeader page={data?.target_page} label="TO" />
            <ContentParagraphs
              paragraphs={data?.target_page.paragraphs}
              matches={data?.matches}
              side="target"
            />
          </div>
        </div>
        
        {/* Footer with Recommendation */}
        <div className="p-6 border-t bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                💡 Recommendation: Add link in paragraph {data?.best_insertion_point.paragraph_index + 1}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                Anchor text: <span className="font-mono bg-gray-100 px-2 py-1 rounded">"{suggestedAnchor}"</span>
              </p>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
              Copy Suggested Anchor
            </button>
            <button className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100">
              Mark as Implemented
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### **Paragraph Highlighting:**
```typescript
function ContentParagraphs({
  paragraphs,
  matches,
  side,
  bestInsertionPoint
}: {
  paragraphs: Paragraph[],
  matches: ContentMatch[],
  side: 'source' | 'target',
  bestInsertionPoint?: InsertionPoint
}) {
  return (
    <div className="space-y-4 mt-4">
      {paragraphs.map((para, index) => {
        // Find if this paragraph has a match
        const match = matches?.find(m => 
          side === 'source' 
            ? m.source_paragraph_index === index
            : m.target_paragraph_index === index
        );
        
        const isInsertionPoint = 
          side === 'source' && 
          bestInsertionPoint?.paragraph_index === index;
        
        return (
          <div
            key={index}
            className={`p-4 rounded-lg border-2 transition-all ${
              match
                ? match.match_type === 'high'
                  ? 'bg-green-50 border-green-300'
                  : match.match_type === 'medium'
                  ? 'bg-yellow-50 border-yellow-300'
                  : 'bg-orange-50 border-orange-300'
                : 'bg-white border-gray-200'
            } ${isInsertionPoint ? 'ring-4 ring-blue-300' : ''}`}
          >
            {match && (
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-medium px-2 py-1 rounded ${
                  match.match_type === 'high'
                    ? 'bg-green-200 text-green-800'
                    : match.match_type === 'medium'
                    ? 'bg-yellow-200 text-yellow-800'
                    : 'bg-orange-200 text-orange-800'
                }`}>
                  {match.similarity_score}% Match
                </span>
                <div className="flex gap-1">
                  {match.shared_keywords.map(kw => (
                    <span key={kw} className="text-xs text-gray-600">
                      #{kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            <p className="text-sm text-gray-700 leading-relaxed">
              {highlightKeywords(para.text, match?.shared_keywords || [])}
            </p>
            
            {isInsertionPoint && (
              <div className="mt-3 pt-3 border-t border-blue-200">
                <button className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 font-medium">
                  👉 Add Link Here
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function highlightKeywords(text: string, keywords: string[]): React.ReactNode {
  if (!keywords.length) return text;
  
  let highlightedText = text;
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b(${keyword})\\b`, 'gi');
    highlightedText = highlightedText.replace(
      regex,
      '<mark class="bg-yellow-200 px-1 rounded">$1</mark>'
    );
  });
  
  return <span dangerouslySetInnerHTML={{ __html: highlightedText }} />;
}
```

---

## 🔗 INTEGRATION WITH AI SUGGESTIONS

### **From AISuggestionsWidget:**
```typescript
function AISuggestionsWidget({ projectId }: { projectId: string }) {
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [showComparison, setShowComparison] = useState(false);
  
  return (
    <>
      <div className="suggestions-list">
        {suggestions.map(suggestion => (
          <div key={suggestion.id} className="suggestion-item">
            <p>{suggestion.from_url} → {suggestion.to_url}</p>
            <button
              onClick={() => {
                setSelectedSuggestion(suggestion);
                setShowComparison(true);
              }}
              className="text-blue-600 hover:underline text-sm"
            >
              Compare Content →
            </button>
          </div>
        ))}
      </div>
      
      {showComparison && selectedSuggestion && (
        <ContentComparison
          projectId={projectId}
          fromUrl={selectedSuggestion.from_url}
          toUrl={selectedSuggestion.to_url}
          suggestedAnchor={selectedSuggestion.suggested_anchor}
          onClose={() => setShowComparison(false)}
        />
      )}
    </>
  );
}
```

---

## 🎯 VALUE PROPOSITION

### **For SEO Experts:**
1. ✅ **Visual Proof** - See exactly WHY the suggestion makes sense
2. ✅ **Actionable** - Know exactly WHERE to add the link
3. ✅ **Context-Aware** - Understand topical relevance at paragraph level
4. ✅ **Time-Saving** - No need to manually read both pages
5. ✅ **Confidence** - High similarity score = high-quality suggestion

### **Competitive Advantage:**
- LinkStorm: Shows suggestions in a table
- **Our Tool:** Shows paragraph-level contextual matching with visual highlighting
- **Result:** 10x more actionable insights

---

## 🚀 IMPLEMENTATION STEPS

### **Backend (3-4 hours):**
1. Create `/compare-content` endpoint
2. Implement paragraph splitting function
3. Implement paragraph-level TF-IDF matching
4. Implement best insertion point logic
5. Test with real content

### **Frontend (3-4 hours):**
1. Create `ContentComparison.tsx` component
2. Create side-by-side layout
3. Implement paragraph highlighting
4. Add keyword highlighting
5. Integrate with AISuggestionsWidget
6. Add "Copy Anchor" functionality

### **Total Time:** 6-8 hours

---

## 📊 EXAMPLE OUTPUT

### **Real Example:**

**From:** `/blog/seo-tips` (Depth 2, Equity 65)  
**To:** `/guide/internal-linking` (Depth 1, Equity 82)  
**Shared Terms:** internal linking, seo strategy, link building, anchor text  
**Relevance:** 87%

**Matches Found:**
1. Paragraph 2 ↔ Paragraph 1: **85% match** (shared: internal linking, site structure)
2. Paragraph 4 ↔ Paragraph 3: **62% match** (shared: anchor text, optimization)

**Recommendation:**  
Add link in paragraph 2 (middle position) with anchor text: "internal linking strategy"

---

## 💡 FUTURE ENHANCEMENTS

1. **Auto-Generate Link HTML** - Generate `<a>` tag with proper anchor text
2. **WordPress Integration** - Direct API to add link to WordPress post
3. **A/B Testing** - Track which suggestions get implemented
4. **Sentiment Analysis** - Ensure linking context is positive
5. **Image Context** - Detect if link should be added near an image
6. **Outbound Link Density** - Warn if paragraph already has too many links

---

## 🎉 CONCLUSION

This transforms your tool from "here are suggestions" to **"here's exactly how to implement them"**.

**SEO Value:**
- Saves 10+ minutes per link implementation
- Higher quality placements (contextually relevant)
- Better anchor text selection (from shared terms)
- Visual confidence in suggestions

**Ready to build this?** 🚀

# Scraper Development Guidelines & Learnings

## Overview

This document captures key learnings, patterns, and best practices from developing and debugging web scrapers for second-hand marketplaces, with specific insights from DBA.dk.

---

## 1. Technical Insights

### 1.1 BeautifulSoup Limitations

| Issue | Symptom | Root Cause | Solution |
|-------|---------|------------|----------|
| Incomplete text extraction | `get_text()` returns very short strings | `<!-- -->` comments split text nodes | Search raw `response.text` directly |
| Missing elements | `find()` returns None for visible content | Client-side rendering (JS) | Use headless browser or find API |
| Malformed HTML | Parser crashes or misses data | Unclosed tags, special chars | Use `html.parser` with error handling |

**Key Learning**: Always verify data exists in raw HTML before assuming parser failure.

```python
# Instead of:
soup = BeautifulSoup(resp.text, 'html.parser')
text = soup.get_text()  # May miss content with many comments

# Try:
if 'expected-text' in resp.text:
    # Data exists, parser is the issue
    text = resp.text
    # Use regex directly
```

### 1.2 Client-Side Rendering Detection

**Indicators of CSR (Client-Side Rendering)**:
- `<script type="module">` importing JS bundles
- `@media(scripting: enabled)` CSS rules
- `<slot>` elements
- `data-*` attributes for component hydration
- Very small `get_text()` output vs large HTML size

**DBA.dk Specific**:
- Uses hybrid rendering: HTML structure exists, content loaded by JS
- Dates and descriptions ARE in initial HTML (not pure CSR)
- Uses `<!-- -->` comments for text node separation
- Framework: Likely React/Vue with server-side structure

### 1.3 HTTP & Compression

**Brotli Compression Issue**:
```python
# httpx does NOT support Brotli (br) decompression
# Must remove 'br' from Accept-Encoding
HEADERS = {
    "Accept-Encoding": "gzip, deflate",  # NOT "gzip, deflate, br"
}
```

**Verification**:
```python
# Check response headers
print(resp.headers.get('content-encoding'))  # Should be 'gzip' or None
```

---

## 2. Platform-Specific Patterns

### 2.1 DBA.dk

#### URL Structure
```
Search: https://www.dba.dk/recommerce/forsale/search?q={query}
Detail: https://www.dba.dk/recommerce/forsale/item/{id}
```

#### Data Location
| Field | Location | Format | Notes |
|-------|----------|--------|-------|
| date_posted | Detail page | `Sidst redigeret: DD.MM.YYYY kl. HH:MM` | In `<section data-testid="object-info">` |
| description | Detail page | Plain text | In `<section data-testid="description">` |
| title | Search page | Card link text | Often needs parent lookup |
| price | Search page | Pattern: `\d{1,3}[.\s,]\d{3,}` | May include "kr" |
| images | Search page | `<img src="...">` | Multiple per listing |

#### HTML Structure
```html
<!-- Date location -->
<section class="mb-8" data-testid="object-info">
  <p>Sidst redigeret<!-- -->: <!-- -->28.3.2026 kl. 08:23...</p>
</section>

<!-- Description location -->
<section data-testid="description" class="about-section">
  <p>Apple iPhone... <!-- -->Vis fuld beskrivelse</p>
</section>
```

#### Extraction Strategies

**Dates** (in order of reliability):
1. Meta tag: `<meta property="article:published_time" content="...">`
2. Raw text regex: `Sidst redigeret.*?(\d{1,2}\.\d{1,2}\.\d{4})`
3. Time elements: `<time datetime="...">`
4. Any date pattern: `\d{1,2}\.\d{1,2}\.\d{4}`

**Descriptions**:
1. BeautifulSoup on `data-testid="description"` section
2. Raw text extraction with HTML tag stripping:
   ```python
   desc_html = resp_text[desc_start:desc_end]
   desc_clean = re.sub(r'<[^>]+>', ' ', desc_html)
   desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
   ```

#### Character Encoding
- Danish characters may appear as unusual Unicode escapes
- `å` → `\u00e5` or `σ`
- `ø` → `\u00f8` or `°`
- `æ` → `\u00e6`
- This is DBA's framework behavior, not a scraper bug

---

## 3. Debugging Workflow

### Step 1: Verify Data Exists
```python
# Save raw HTML for inspection
with open('debug.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)

# Check for expected content
assert 'Sidst redigeret' in resp.text
```

### Step 2: Test Parser Independently
```python
# Test BeautifulSoup on snippet
snippet = '<p>Sidst redigeret<!-- -->: 28.3.2026</p>'
soup = BeautifulSoup(snippet, 'html.parser')
print(soup.get_text())  # May be empty
print(resp.text)  # Use raw text instead
```

### Step 3: Verify Regex Patterns
```python
import re
text = 'Sidst redigeret: 28.3.2026 kl. 08:23'
pattern = r'Sidst redigeret.*?(\d{1,2}\.\d{1,2}\.\d{4})'
assert re.search(pattern, text)
```

### Step 4: Implement Fallback Chain
```python
def extract_date(resp):
    # 1. Try meta tags
    # 2. Try raw text regex
    # 3. Try element extraction
    # 4. Try last-resort pattern
    pass
```

---

## 4. Performance Considerations

### Network Overhead
| Action | Time | Notes |
|--------|------|-------|
| Search page fetch | ~500ms | Single request |
| Detail page fetch | ~15ms | Per listing |
| N listings | 15ms × N | Can add up quickly |

### Optimization Strategies
1. **Batching**: Fetch multiple detail pages concurrently
   ```python
   async with asyncio.TaskGroup() as tg:
       for url in urls:
           tg.create_task(fetch_detail(url))
   ```

2. **Caching**: Cache detail page responses
   ```python
   @lru_cache(maxsize=100)
async def fetch_detail(url):
       ...
   ```

3. **Rate Limiting**: Respect platform limits
   ```python
   await asyncio.sleep(0.5)  # 500ms between requests
   ```

4. **Selective Fetching**: Only fetch detail pages when needed
   - Skip if date not required
   - Use search page data when sufficient

---

## 5. Error Handling Best Practices

### Graceful Degradation
```python
try:
    date = extract_date(resp)
except httpx.TimeoutException:
    date = ""
except httpx.HTTPStatusError:
    date = ""
except Exception:
    date = ""
```

### Debug vs Production
```python
# Development: verbose logging
if self.debug:
    console.print(f"[yellow]Failed to extract date: {e}[/yellow]")

# Production: silent failure
try:
    date = extract_date(resp)
except:
    date = ""
```

---

## 6. Testing Checklist

- [ ] Verify raw HTML contains expected data
- [ ] Test BeautifulSoup parsing on sample HTML
- [ ] Verify regex patterns match actual text
- [ ] Test with multiple URLs (data may vary)
- [ ] Test with different query parameters
- [ ] Handle edge cases (empty results, errors)
- [ ] Verify encoding handling
- [ ] Test rate limiting / concurrent requests

---

## 7. Common Pitfalls

### Pitfall 1: Assuming Data is on Search Page
**Symptom**: Dates always empty
**Fix**: Check if data requires detail page fetch

### Pitfall 2: Relying on Single Extraction Method
**Symptom**: Works for some pages, fails for others
**Fix**: Implement fallback chain

### Pitfall 3: Not Handling Encoding
**Symptom**: Special characters in output
**Fix**: Use UTF-8 consistently, normalize text

### Pitfall 4: No Error Handling
**Symptom**: Single page failure crashes entire scraper
**Fix**: Wrap each page fetch in try/except

### Pitfall 5: No Debug Output
**Symptom**: Can't diagnose why extraction fails
**Fix**: Log intermediate results during development

---

## 8. Tools & Libraries

### Recommended
- **httpx**: Async HTTP client with timeout support
- **BeautifulSoup**: HTML parsing (use `html.parser`)
- **lxml**: Faster parser (if installed: `pip install lxml`)
- **rich**: Pretty console output for debugging

### Optional
- **playwright**: For pure client-side rendered sites
- **selenium**: Alternative to playwright
- **pydantic**: Data validation and parsing

---

## 9. Code Templates

### Basic Scraper Structure
```python
import httpx
from bs4 import BeautifulSoup
import re

class PlatformScraper:
    async def scrape(self, query, max_results=10):
        url = f"https://platform.com/search?q={query}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract listings
            cards = soup.select('...')
            results = []
            for card in cards[:max_results]:
                # Extract data from card
                # Fetch detail page if needed
                results.append(listing)
            
            return results
```

### Fallback Extraction
```python
def extract_with_fallback(soup, resp_text, selectors):
    # Try each selector
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    
    # Try raw text regex
    for pattern in regex_patterns:
        match = re.search(pattern, resp_text)
        if match:
            return match.group(1)
    
    return ""
```

---

## 10. References

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [httpx Documentation](https://www.python-httpx.org/)
- [DBA.dk](https://www.dba.dk)

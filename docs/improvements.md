# Scour — Optimization Backlog

Improvements identified during a code review of the pipeline (scrapers, filters, ranker,
dedup, LLM client, price converter). The architecture itself is solid — modular registry,
dependency injection, typed dataclasses, concurrent scrapers — so these are about **cost,
speed, result quality, and robustness**, not restructuring.

_Last reviewed: 2026-06-15._

## Priority summary

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 1 | Result caching (scrape + per-listing LLM verdicts) | High (cost + speed) | M | ☐ |
| 2 | Fuzzy / cross-platform deduplication | High (result quality) | S | ☐ |
| 3 | Live exchange rates | High (price accuracy) | S | ☐ |
| 4 | Machine-readable output (`--json`) | High (usability/automation) | S | ☐ |
| 5 | Mistral JSON mode + reuse client | Med (reliability + latency) | S | ☐ |
| 6 | Finish UTF-8 / encoding fix (web + modules) | Med (robustness) | S | ◐ partial |
| 7 | Intent-aware filter/scorer with more context | Med (relevance) | M | ☐ |
| 8 | Filter correctness bugs (silent bypass, dead counter) | Med (correctness) | S | ☐ |
| 9 | Stale pipeline docstring | Low (maintainability) | XS | ☐ |

---

## High impact

### 1. Add result caching ☐
**Problem:** every run re-scrapes all three sites *and* re-runs every LLM call. Re-running the
same or an overlapping query pays full scrape + Mistral cost again for listings already seen.

**Change:**
- Scrape cache keyed on `(platform, search_query)` with a short TTL (hours) — see
  `core/pipeline.py` `_execute_scrapers` (~line 318).
- **Per-listing LLM verdict cache** keyed on a content hash of `(url + title + description)`
  for the filter, model-extractor, and scorer. This is the big one: even a *new* query reuses
  model extraction and review summaries for previously-seen listings. Pairs naturally with the
  slow review stage (`REVIEW_DELAY = 4.0s`, `config.py:69`).
- Suggest a simple on-disk cache (e.g. `diskcache` or a JSON/SQLite store under a `.cache/` dir)
  with a `--no-cache` / `--refresh` flag to bypass.

**Acceptance:** a repeated identical query returns in a fraction of the time with near-zero LLM
calls; a partially-overlapping query only pays LLM cost for new listings.

### 2. Fuzzy / cross-platform deduplication ☐
**Problem:** `processors/deduplicator.py:78` collapses **exact URL matches only**. Results are
full of near-duplicates the LLM itself flags ("Same as id 22", "duplicate listing with identical
specs", the same item listed 4× on Tradera, and the same unit on both DBA and Tradera).

**Change:** add a normalized fuzzy pass after the URL pass:
- key on `(normalized_title_tokens, round(price), platform)` for same-platform repeats;
- a cross-platform check on `(round(price), first-N title tokens)` to collapse the same item
  appearing on multiple sites (keep the cheapest / most-detailed).

**Acceptance:** the top-N shows *distinct* items instead of one item repeated; metadata reports
the extra duplicates removed.

### 3. Live exchange rates ☐
**Problem:** `config.EXCHANGE_RATES` (`config.py:45`, DKK 7.45 / SEK 11.20) is hardcoded, so all
converted prices are approximate and cross-currency ranking (which is partly value-for-money) is
skewed.

**Change:** fetch the ECB daily reference rates (free XML, no key) once at startup, cache for the
day, and fall back to the hardcoded constants on failure. Centralize in `processors/price_converter.py`.

**Acceptance:** prices reflect real same-day rates; offline/failed fetch falls back gracefully.

### 4. Machine-readable output (`--json`) ☐
**Problem:** the only CLI output is the rich table (`output.py`), which wraps/truncates long URLs
and can't be consumed programmatically (had to scrape it with `sed`).

**Change:** add `--json` (stdout) and/or `--output results.json` that dumps
`dataclasses.asdict(listing)` for the ranked list. The web adapter already needs this shape.

**Acceptance:** `python second_hand_research.py "..." --json` emits valid JSON of all ranked
listings with full fields and untruncated URLs.

---

## Medium impact

### 5. Mistral JSON mode + client reuse ☐
**Problem A:** prompts ask for JSON but the client sends `response_format={"type": "text"}`
(`llm/client.py:217`), then regex-parses fenced ```` ```json ```` blocks — fragile, causes
parse-failure retries.
**Change:** use `response_format={"type": "json_object"}` (or json_schema) for the filter/score/
model/keyword prompts.

**Problem B:** `MistralClient.chat` builds a **new `Mistral(...)` client (new httpx pool) on every
call** (`llm/client.py:213`) — connection churn on dozens of calls per run.
**Change:** construct the client once and reuse it.

**Acceptance:** fewer JSON parse retries; measurable latency drop on filter/score stages.

### 6. Finish the UTF-8 / encoding fix ◐
**Done:** added a stdout/stderr UTF-8 reconfigure at the top of `second_hand_research.py` (~line 21)
so bare `python second_hand_research.py` no longer crashes on Windows with `UnicodeEncodeError`.

**Still to do:** `output.py`, `filters/llm_filter.py:138`, and `rankers/ranker_module.py:143`
still print raw `✗`/`⚠️` through their own module-level `Console()` instances. The web backend
imports these modules, so the same crash can resurface outside the CLI. Centralize on one shared
`Console` forced to UTF-8 (or drop the non-cp1252 glyphs).

**Acceptance:** running the web backend and CLI in a non-UTF-8 (cp1252) environment never raises
`UnicodeEncodeError`.

### 7. Intent-aware filter/scorer with more context ☐
**Problem:** the filter is pinned to `mistral-small-latest` (`filters/llm_filter.py:62`) with
descriptions truncated to 150 chars (200 for scoring). For use-case queries ("home server for
Immich") it rated *gaming* NUCs and a *defective* unit highly ("great for gaming" on a server
search).

**Change:** feed more description context; make the score prompt explicitly penalize **use-case**
mismatch, not just brand/keyword match; make the model tier configurable instead of hardcoded.

**Acceptance:** for an intent-style query, off-use-case items (gaming, defective, accessory) rank
below genuinely fitting ones.

---

## Correctness bugs (small)

### 8. Filter bugs ☐
- **Silent filter bypass:** `filters/llm_filter.py:154` — if the last retry throws, the whole
  batch is marked `relevant = True`, injecting up to `BATCH_SIZE` (60) unfiltered listings into
  results with no visible warning. Make the failure visible / more graceful.
- **Dead counter:** `total_discarded` in `filters/llm_filter.py` is never incremented, so the
  "{n} listings discarded" summary always prints 0.

### 9. Stale pipeline docstring ☐
`core/pipeline.py:55` describes a two-pass filter ("1st pass" / "2nd pass"), but the code runs a
single filter pass. Update the docstring to match.

---

## Suggested order

`--json` + fuzzy dedup first (quick, immediately better output) → caching (most impactful) →
live FX → Mistral JSON mode/reuse → the rest. Items 1–4 are each self-contained.

---

# Additions from live-usage review (2026-06-15)

Findings from **dogfooding the CLI on a real search** ("smart TV, under 400 DKK, in
Copenhagen") rather than reading the code. These are problems that were actually *hit* in use:
the location requirement was unanswerable, an entire platform's results silently vanished, and an
"exhaustive" sweep still missed listings. They're additive to items 1–9 above; overlaps with
#7 (relevance) and #8 (silent failures) are noted inline.

## Priority summary (live-usage)

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 10 | Capture listing location (postal / city / geo) | High (unlocks location search) | S–M | ☐ |
| 11 | Rank **before** capping to `max_results` (platform-bias bug) | High (correctness) | XS | ☐ |
| 12 | Push filters to the source (price / location / category params) | High (cost + accuracy) | S | ☐ |
| 13 | CLI search filters (`--max-price`, `--location`, `--max-results`, `--sort`, `--platform`) | High (usability) | S | ☐ |
| 14 | Parse JSON-LD / schema.org + sold/availability filter | High (robustness) | M | ☐ |
| 15 | Retry/backoff + rate-limit detail fetches; no silent `except` | Med (completeness) | S | ☐ |
| 16 | Quiet third-party logging (httpx floods stdout) | Low (usability) | XS | ☐ |
| 17 | Structured attribute extraction → faceted filtering | Med (relevance) | M | ☐ |
| 18 | Accessory / type-mismatch detection | Med (precision) | S–M | ☐ |
| 19 | Locale-aware platform selection + ship-vs-pickup tag | Med (relevance) | S | ☐ |
| 20 | Saved searches + new-listing alerts | High (stickiness) | M | ☐ |
| 21 | Distance-based ranking (depends on #10) | Med (relevance) | S | ☐ |

---

## Blocking / correctness

### 10. Capture listing location ☐
**Problem:** `Listing` (`models.py`) has **no location field**, so the tool literally cannot
answer "in Copenhagen" — the most common second-hand constraint. The DBA scraper already fetches
each detail page in `scrapers/dba.py` `_fetch_detail` (~line 69) and then discards the location
that's right there: `data-testid="object-address"` (e.g. `"2200 København N"`) and a `map-link`
href containing `postalCode=`, `lat`, `lon`. (Note: the *description* often names a different city
for pickup, so parse the structured address, **not** the free text — one listing read "Frederiksberg"
in the body but was actually in 4180 Sorø.)

**Change:** add `location: str`, `postal_code: str`, `lat: float`, `lon: float` to `Listing`;
populate them in each scraper (DBA from the detail page; Vinted from its API payload where present);
surface in `output.py` and the `--json` shape.

**Acceptance:** ranked results display a location; can be filtered/ranked by it (see #13, #21).

### 11. Rank before capping to `max_results` ☐
**Problem:** `core/pipeline.py` (~line 178) truncates the pool to `max_results` **before** model
extraction and scoring: `context.listings = context.listings[:_max]`, in scraper-registration
order. In a live run this dropped **every DBA listing** — the first 40 slots were all Vinted, so
the ranker only ever reordered Vinted and the user saw zero local (DBA) results despite 120 being
scraped. Capping an unranked, platform-ordered pool defeats the ranker entirely.

**Change:** move the cap to **after** scoring (rank, then slice). Add a per-platform quota /
interleave so one source can't crowd out the others before ranking. Optionally score in cheaper
batches so ranking the full pool stays affordable.

**Acceptance:** the final top-N is drawn from all platforms by score, not by scraper order; a
platform that scraped results is never silently zeroed out.

---

## Efficiency & robustness

### 12. Push filters down to the source ☐
**Problem:** Scour scrapes everything and relies on the LLM to filter, which is slow and pays LLM
cost on listings that a query param would have excluded for free. DBA's search honors
**`&price_to=400` server-side** (verified: it caps the result set to ≤400 DKK); category and
area params exist too.

**Change:** translate `--max-price` / `--location` / category into native search params per
platform (`scrapers/dba.py` `scrape`, base URL ~line 147) and only fall back to client-side
filtering where a platform lacks the param.

**Acceptance:** a price-capped query fetches a far smaller, already-relevant pool; fewer detail
fetches and LLM calls for the same results.

### 13. CLI search filters ☐
**Problem:** `second_hand_research.py` (argparse) exposes no `--max-price`, `--location`/`--radius`,
`--max-results`, `--sort`, or `--platform`. `DEFAULT_MAX_RESULTS = 40` (`config.py:60`) is not
overridable, so getting more than 40 results required scripting around the tool.

**Change:** add those flags; wire `--max-price`/`--location` to #12, `--max-results` to the cap in
#11, `--sort {score,price,date,distance}` to the ranker, `--platform` to scraper selection (#19).

**Acceptance:** `... "tv" --max-price 400 --location "København" --sort price` works end-to-end
without code edits.

### 14. Parse JSON-LD / schema.org instead of CSS classes ☐
**Problem:** the DBA scraper is hundreds of lines of brittle fallback selectors
(`select('[class*="price"]')`, etc., `scrapers/dba.py`) that break on any redesign. The same pages
embed stable JSON-LD: `"price"`, `"priceCurrency"`, and `"availability": ".../InStock"`.

**Change:** read the JSON-LD/`<meta>` structured data first, fall back to scraping. This also yields
**sold/active status for free** — filter out sold listings (stale "deals" that are already gone).
Pairs with the scraping-robustness notes in `docs/learnings/scraping_guidelines.md`.

**Acceptance:** price/currency/availability come from structured data; results exclude sold items;
scraper survives cosmetic HTML changes.

### 15. Retry, rate-limit, and surface fetch failures ☐
**Problem:** in a large sweep ~900 of ~2,800 detail-page fetches failed under load and were lost.
`scrapers/dba.py` `_fetch_detail` ends in `except Exception: pass` (~line 138) — failures are
silent and never retried, so results are quietly incomplete (distinct from the filter-level silent
bypass in #8). The `_DETAIL_CONCURRENCY = 15` semaphore has no backoff or jitter.

**Change:** add retry-with-backoff + jitter, a politeness delay/limiter, and **count** failed
fetches into `context.metadata` so the run can report "N listings could not be loaded."

**Acceptance:** transient failures retry and mostly succeed; any remaining gaps are reported, not
hidden.

### 16. Quiet third-party logging ☐
**Problem:** `httpx` INFO logging prints one line per request and **buries the actual results** in
normal runs (every page/detail fetch). 

**Change:** set library loggers (`httpx`, `httpcore`) to WARNING by default; gate verbose HTTP logs
behind `--debug`. Keep the funnel metrics the pipeline already emits.

**Acceptance:** a default run shows results and the scraped→deduped→filtered→ranked summary, not a
wall of request logs.

---

## Result quality

### 17. Structured attribute extraction → faceted filtering ☐
**Problem:** the model-extractor only fills `product_model`. There are no typed specs, so a query
like "smart TVs ≥ 40\"" can't be filtered deterministically — relevance is left to fuzzy LLM
scoring, which conflated TVs with accessories. (Extends #7.)

**Change:** extract typed fields (brand, size/inches, resolution, **smart-OS**, condition) into the
`Listing` (or a `attributes: dict`), and let #13's filters key on them.

**Acceptance:** "≥40\" smart TVs" returns only items whose extracted size and smart-OS qualify.

### 18. Accessory / type-mismatch detection ☐
**Problem:** "smart tv" returned a flood of non-TVs — universal remotes, wall mounts, routers,
Wi-Fi extenders, TV boxes/sticks, a Chromecast dongle, an Apple TV box — and a listing **titled**
"TCL Smart TV" whose body was "remote for sale." The relevance filter let these through. (Extends
#7.)

**Change:** add a product-type classifier ("is this the TV itself, or an accessory *for* a TV?")
and a title/description-mismatch flag; down-rank or exclude accessories unless the query asks for
them.

**Acceptance:** an item search returns the items, not their accessories; title/body mismatches are
flagged.

### 19. Locale-aware platform selection + ship-vs-pickup tag ☐
**Problem:** Tradera is **Swedish** — irrelevant for a Copenhagen pickup — yet it's always scraped,
and Vinted is **ship-based** (sellers often abroad; several results had Polish titles), which is
wrong whenever location matters. Nothing marks a result as ship vs local-pickup.

**Change:** choose platforms by region/locale (and consider DK-local sources like GulogGratis /
Facebook Marketplace); tag each result `delivery: ship | pickup` and let `--platform` / location
filters use it.

**Acceptance:** a Copenhagen query prioritizes local-pickup sources; ship-only foreign listings are
clearly marked or excluded.

---

## Workflow / features

### 20. Saved searches + new-listing alerts ☐
**Problem:** second-hand buying is a *standing* need ("tell me when a cheap local smart TV shows
up"), but Scour is one-shot.

**Change:** persist a named search (query + filters), diff against cached results (#1), and notify
on new matches — a natural fit for the project's `/schedule` cron support.

**Acceptance:** `scour watch "..." --max-price 400 --location København` re-runs on a schedule and
reports only newly-listed matches.

### 21. Distance-based ranking ☐
**Problem (depends on #10):** once lat/lon are captured, "nearest first" is the most useful sort
for local pickup, but there's no geo ranking.

**Change:** accept a user origin (postal code or lat/lon), compute distance, and add `distance` as
a `--sort` option and a scoring signal.

**Acceptance:** results can be ordered by proximity to the buyer.

---

## Suggested order (live-usage)

#11 (one-line correctness fix) and #10 (location) first — together they make local search actually
work. Then #14 (JSON-LD) + #15 (retry) to stop losing results, #12/#13 (source-side filters + CLI
flags) for speed and control, then #17/#18 for precision and #19–#21 for reach. #11, #16 are
near-trivial; #10 + #14 unlock the rest.

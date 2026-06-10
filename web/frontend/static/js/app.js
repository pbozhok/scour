// ============================================
// Global State
// ============================================

const STATE = {
    currentQuery: '',
    isSearching: false,
    sortBy: 'score',
    useFilter: true,
    useReviews: true,
    useScoring: true,
};

// ============================================
// Configuration
// ============================================

const CONFIG = {
    apiBaseUrl: '/api/v1',
    defaultCurrency: 'EUR',
    defaultMaxResults: 40,
    animationDuration: 300,
    debounceDelay: 300
};

// ============================================
// DOM Elements (cached)
// ============================================

let elements = {};

function cacheElements() {
    elements = {
        searchForm:      document.getElementById('search-form'),
        searchQuery:     document.getElementById('search-query'),
        searchContainer: document.getElementById('search-container'),
        resultsContainer:document.getElementById('results-container'),
        loadingIndicator:document.getElementById('loading-indicator'),
        errorMessage:    document.getElementById('error-message'),
        toggleFilter:    document.getElementById('toggle-filter'),
        toggleReviews:   document.getElementById('toggle-reviews'),
        toggleScoring:   document.getElementById('toggle-scoring'),
        sortSelector:    document.getElementById('sort-selector'),
    };
}

// ============================================
// Utility Functions
// ============================================

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatPrice(price, currency) {
    if (price === null || price === undefined) return 'N/A';
    const symbols = { EUR: '€', DKK: 'kr', SEK: 'kr' };
    const symbol = symbols[currency] || currency || '';
    return `${symbol}${price.toFixed(2)}`;
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        if (dateString.length >= 10) {
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        }
        return dateString;
    } catch (e) {
        return dateString;
    }
}

function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// ============================================
// Card Rendering
// ============================================

const PLACEHOLDER_SVG = 'data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%230d0d1a"/><text x="50" y="50" text-anchor="middle" dominant-baseline="middle" fill="%23475569" font-size="11" font-family="monospace">no image</text></svg>';

const PLATFORM_CLASSES = {
    vinted:  'vinted',
    tradera: 'tradera',
    dba:     'dba',
};

function platformClass(platformName) {
    const key = (platformName || '').toLowerCase();
    return PLATFORM_CLASSES[key] || 'default';
}

function renderCard(item, index = 0) {
    const card = document.createElement('div');
    card.className = 'card';
    card.dataset.price = item.price || 0;
    card.dataset.score = item.score || 0;
    card.dataset.date  = item.posted_date || '';
    card.style.animationDelay = `${index * 35}ms`;

    const url = item.original_url || '#';
    card.onclick = () => window.open(url, '_blank');

    // ---- Image container ----
    const imageContainer = document.createElement('div');
    imageContainer.className = 'card-image-container';

    const img = document.createElement('img');
    img.alt = item.title || 'Untitled';
    img.className = 'card-image';
    img.loading = 'lazy';
    img.src = item.image_url || PLACEHOLDER_SVG;
    img.onerror = function() {
        if (this.src !== PLACEHOLDER_SVG) {
            this.onerror = null;
            this.src = PLACEHOLDER_SVG;
        }
    };
    imageContainer.appendChild(img);

    // Platform badge (on image)
    const badge = document.createElement('div');
    badge.className = `card-platform-badge ${platformClass(item.platform)}`;
    badge.textContent = item.platform || 'Unknown';
    imageContainer.appendChild(badge);

    // Review hover overlay
    if (item.review && (item.review.average_rating || item.review.review_count || item.review.summary)) {
        const hover = document.createElement('div');
        hover.className = 'card-hover';
        const summary = document.createElement('div');
        summary.className = 'review-summary';

        if (item.review.average_rating) {
            const rating = document.createElement('div');
            rating.className = 'review-rating';
            rating.textContent = `${item.review.average_rating} / 5`;
            summary.appendChild(rating);
        }
        if (item.review.summary) {
            const text = document.createElement('div');
            text.className = 'review-text';
            text.textContent = truncateText(item.review.summary, 110);
            summary.appendChild(text);
        }
        if (item.review.review_count) {
            const count = document.createElement('div');
            count.className = 'review-count';
            count.textContent = `(${item.review.review_count} reviews)`;
            summary.appendChild(count);
        }

        hover.appendChild(summary);
        imageContainer.appendChild(hover);
    }

    card.appendChild(imageContainer);

    // ---- Card content ----
    const content = document.createElement('div');
    content.className = 'card-content';

    const title = document.createElement('h3');
    title.className = 'card-title';
    title.textContent = truncateText(item.title || 'Untitled', 65);
    content.appendChild(title);

    // Meta row
    const meta = document.createElement('div');
    meta.className = 'card-meta';

    const price = document.createElement('span');
    price.className = 'card-price';
    price.textContent = formatPrice(item.price, item.currency);
    meta.appendChild(price);

    if (item.score && item.score > 0) {
        const score = document.createElement('span');
        score.className = 'card-score';
        score.textContent = `★ ${item.score.toFixed(1)}`;
        meta.appendChild(score);
    }

    if (item.posted_date) {
        const date = document.createElement('span');
        date.className = 'card-date';
        date.textContent = formatDate(item.posted_date);
        meta.appendChild(date);
    }

    content.appendChild(meta);

    if (item.score_reason) {
        const reason = document.createElement('div');
        reason.className = 'card-reason';
        reason.textContent = item.score_reason;
        content.appendChild(reason);
    }

    card.appendChild(content);
    return card;
}

function renderCards(response) {
    const container = elements.resultsContainer;
    if (!container) return;

    if (!response || !response.results || response.results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
                <h2>No results found</h2>
                <p>Try a different search query.</p>
            </div>`;
        return;
    }

    let filteredNote = '';
    if (response.llm_filtered && response.llm_filtered > 0) {
        filteredNote = ` · <em>${response.llm_filtered}</em> filtered`;
    }

    let timeNote = '';
    if (response.elapsed_ms != null) {
        const secs = (response.elapsed_ms / 1000).toFixed(1);
        timeNote = ` · <span class="results-time">${secs}s</span>`;
    }

    const headerHtml = `
        <div class="results-header">
            <span class="results-count">
                <em>${response.total_results}</em> results for "<em>${escapeHtml(response.query)}</em>"${filteredNote}${timeNote}
            </span>
        </div>`;

    const fragment = document.createDocumentFragment();
    const grid = document.createElement('div');
    grid.className = 'cards-grid';

    response.results.forEach((item, index) => {
        const cardEl = renderCard(item, index);
        if (cardEl) grid.appendChild(cardEl);
    });

    fragment.appendChild(grid);
    container.innerHTML = headerHtml;
    container.appendChild(fragment);
}

function sortResults(sortBy) {
    const container = elements.resultsContainer;
    if (!container) return;
    const grid = container.querySelector('.cards-grid');
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll('.card'));
    if (cards.length === 0) return;

    cards.sort((a, b) => {
        const aPrice = parseFloat(a.dataset.price || '0');
        const bPrice = parseFloat(b.dataset.price || '0');
        const aScore = parseFloat(a.dataset.score || '0');
        const bScore = parseFloat(b.dataset.score || '0');
        const aDate  = a.dataset.date || '';
        const bDate  = b.dataset.date || '';

        switch (sortBy) {
            case 'price_asc':  return aPrice - bPrice;
            case 'price_desc': return bPrice - aPrice;
            case 'date':       return bDate.localeCompare(aDate);
            default:           return bScore - aScore;
        }
    });

    grid.innerHTML = '';
    cards.forEach(c => grid.appendChild(c));
}

// ============================================
// Loading & Error
// ============================================

function showLoading() {
    if (elements.loadingIndicator) elements.loadingIndicator.style.display = 'flex';
    if (elements.errorMessage)    elements.errorMessage.style.display = 'none';
}

function hideLoading() {
    if (elements.loadingIndicator) elements.loadingIndicator.style.display = 'none';
}

function showError(message) {
    if (!elements.errorMessage) return;
    elements.errorMessage.textContent = message;
    elements.errorMessage.style.display = 'block';
    setTimeout(() => {
        if (elements.errorMessage) elements.errorMessage.style.display = 'none';
    }, 5000);
}

// ============================================
// Search Submission
// ============================================

function handleFormSubmit(event) {
    if (event) event.preventDefault();
    submitSearch();
    return false;
}

function buildQueryParams() {
    const params = new URLSearchParams();
    const query = elements.searchQuery?.value;
    if (query) params.set('query', query);
    params.set('max_results', CONFIG.defaultMaxResults);
    params.set('currency', CONFIG.defaultCurrency);
    params.set('use_filter',  elements.toggleFilter?.value  === 'true' || STATE.useFilter);
    params.set('use_reviews', elements.toggleReviews?.value === 'true' || STATE.useReviews);
    params.set('use_scoring', elements.toggleScoring?.value === 'true' || STATE.useScoring);
    params.set('sort_by', elements.sortSelector?.value || STATE.sortBy);
    return params;
}

function animateSearchToTop() {
    const c = elements.searchContainer;
    if (!c || c.classList.contains('active')) return;

    // FLIP – First: record current screen position (before any layout change)
    const fromY = c.getBoundingClientRect().top;

    // FLIP – Last: apply active layout in one synchronous step
    c.classList.add('active');

    // Reserve page space for content right away (uses compact header height)
    document.documentElement.style.paddingTop = `${c.offsetHeight + 12}px`;

    // FLIP – Invert: push element back to where it was visually
    c.style.transition = 'none';
    c.style.transform  = `translateY(${fromY}px)`;

    // Flush so the browser registers the displaced position before we animate
    void c.offsetHeight;

    // FLIP – Play: GPU-composited transform only, no layout properties in flight
    c.style.transition = 'transform 540ms cubic-bezier(0.22, 1, 0.36, 1)';
    c.style.transform  = 'translateY(0)';

    c.addEventListener('transitionend', function onDone(e) {
        if (e.propertyName !== 'transform') return;
        c.style.transition = '';
        c.style.transform  = '';
    }, { once: true });
}

function submitSearch() {
    const query = elements.searchQuery?.value || document.getElementById('search-query')?.value;
    if (!query || query.trim().length < 1) {
        showError('Please enter a search query');
        return;
    }

    STATE.currentQuery    = query;
    STATE.isSearching     = true;
    STATE.searchStartTime = Date.now();

    animateSearchToTop();

    showLoading();

    const url = `${CONFIG.apiBaseUrl}/search?${buildQueryParams().toString()}`;

    fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            let results = data.results || data.result || [];
            if (!results.length && Array.isArray(data)) results = data;

            renderCards({
                query:        data.query || '',
                results,
                total_results: data.total_results || data.totalResults || results.length,
                llm_filtered:  data.llm_filtered || 0,
                sort_by:       data.sort_by || 'score',
                elapsed_ms:    Date.now() - STATE.searchStartTime,
            });
            STATE.isSearching = false;
        })
        .catch(error => {
            showError(`Search failed: ${error.message}`);
            STATE.isSearching = false;
        })
        .finally(() => {
            hideLoading();
        });
}

// ============================================
// Sort / Toggle helpers
// ============================================

function setSort(sortBy) {
    STATE.sortBy = sortBy;
    if (elements.sortSelector) elements.sortSelector.value = sortBy;
}

function setSortAndSearch(sortBy) {
    setSort(sortBy);
    sortResults(sortBy);
}

function updateToggle(name, value) {
    switch (name) {
        case 'filter':
            STATE.useFilter = value;
            if (elements.toggleFilter) elements.toggleFilter.value = value;
            break;
        case 'reviews':
            STATE.useReviews = value;
            if (elements.toggleReviews) elements.toggleReviews.value = value;
            break;
        case 'scoring':
            STATE.useScoring = value;
            if (elements.toggleScoring) elements.toggleScoring.value = value;
            break;
    }
}

// ============================================
// Init
// ============================================

function initToggleControls() {
    document.querySelectorAll('.toggle-item input[type="checkbox"]').forEach((checkbox, index) => {
        const name = ['filter', 'reviews', 'scoring'][index];
        const urlParams = new URLSearchParams(window.location.search);
        const isChecked = urlParams.get(name) !== 'false';
        checkbox.checked = isChecked;
        updateToggle(name, isChecked);
        checkbox.addEventListener('change', function() { updateToggle(name, this.checked); });
    });
}

function initSortControls() {
    const sortButtons = document.querySelectorAll('.sort-button');
    const paramValue = new URLSearchParams(window.location.search).get('sort_by') || 'score';

    sortButtons.forEach(button => {
        const sortBy = button.dataset.sort;
        button.classList.toggle('active', sortBy === paramValue);
        if (sortBy === paramValue) setSort(sortBy);

        button.addEventListener('click', function() {
            sortButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            setSort(sortBy);
            if (STATE.currentQuery) sortResults(sortBy);
        });
    });
}

function initFormSubmit() {
    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('submit', evt => { evt.preventDefault(); submitSearch(); });
    }
}

function initKeyboardNavigation() {
    document.addEventListener('keydown', evt => {
        if (evt.key === 'Enter' && evt.target === elements.searchQuery) {
            evt.preventDefault();
            submitSearch();
        }
    });
}

function initSearchPosition() {
    const c = elements.searchContainer;
    if (!c) return;
    // Center vertically with a pixel-exact transform so there are no CSS calc quirks
    const offset = Math.round((window.innerHeight - c.offsetHeight) / 2);
    c.style.transition = 'none';
    c.style.transform  = `translateY(${offset}px)`;
    // Re-enable transitions after the initial placement paints
    requestAnimationFrame(() => requestAnimationFrame(() => {
        c.style.transition = '';
    }));
}

document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    initSearchPosition();
    initToggleControls();
    initSortControls();
    initFormSubmit();
    initKeyboardNavigation();
});

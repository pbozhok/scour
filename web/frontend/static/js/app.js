/**
 * Second-Hand Search Web Interface - Main Application JavaScript
 * 
 * This script handles:
 * 1. Search form submission via fetch API
 * 2. Card rendering from API JSON responses
 * 3. Click handlers for card navigation
 * 4. Loading states and error handling
 * 5. Visual feedback during operations
 */

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
        searchForm: document.getElementById('search-form'),
        searchQuery: document.getElementById('search-query'),
        searchContainer: document.getElementById('search-container'),
        resultsContainer: document.getElementById('results-container'),
        loadingIndicator: document.getElementById('loading-indicator'),
        errorMessage: document.getElementById('error-message'),
        toggleFilter: document.getElementById('toggle-filter'),
        toggleReviews: document.getElementById('toggle-reviews'),
        toggleScoring: document.getElementById('toggle-scoring'),
        sortSelector: document.getElementById('sort-selector'),
    };
}

// ============================================
// Utility Functions
// ============================================

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format price based on currency
 */
function formatPrice(price, currency) {
    if (price === null || price === undefined) return 'N/A';
    
    const currencySymbols = {
        'EUR': '\u20ac',
        'DKK': 'kr',
        'SEK': 'kr'
    };
    
    const symbol = currencySymbols[currency] || currency || '';
    return `${symbol}${price.toFixed(2)}`;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
        // Try to parse ISO date (YYYY-MM-DD)
        if (dateString.length >= 10) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
        return dateString;
    } catch (e) {
        return dateString;
    }
}

/**
 * Truncate text to maximum length
 */
function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// ============================================
// Card Rendering
// ============================================

/**
 * Render a single item card from API data
 * Uses DOM methods instead of template literals to avoid escaping issues
 */
function renderCard(item) {
    // Create card element using DOM methods for safety
    const card = document.createElement('div');
    card.className = 'card';
    
    // Set data attributes
    card.dataset.price = item.price || 0;
    card.dataset.score = item.score || 0;
    card.dataset.date = item.posted_date || '';
    
    // Set onclick handler
    const url = item.original_url || '#';
    card.onclick = function() { window.open(url, '_blank'); };
    
    // Image container
    const imageContainer = document.createElement('div');
    imageContainer.className = 'card-image-container';
    
    const img = document.createElement('img');
    img.alt = item.title || 'Untitled';
    img.className = 'card-image';
    img.loading = 'lazy';
    
    // Use data URL for placeholder to ensure it always loads
    const placeholderUrl = 'data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23f1f5f9"/><text x="50" y="50" text-anchor="middle" dominant-baseline="middle" fill="%2394a3b8" font-size="12">No image</text></svg>';
    
    img.src = item.image_url || placeholderUrl;
    img.onerror = function() {
        // Prevent infinite loop - only change src if not already placeholder
        if (this.src !== placeholderUrl) {
            this.onerror = null;
            this.src = placeholderUrl;
        }
    };
    imageContainer.appendChild(img);
    
    // Add review hover if available
    if (item.review && (item.review.average_rating || item.review.review_count || item.review.summary)) {
        const reviewHover = document.createElement('div');
        reviewHover.className = 'card-hover';
        const reviewSummary = document.createElement('div');
        reviewSummary.className = 'review-summary';
        
        if (item.review.average_rating) {
            const ratingDiv = document.createElement('div');
            ratingDiv.className = 'review-rating';
            ratingDiv.textContent = `${item.review.average_rating}/5`;
            reviewSummary.appendChild(ratingDiv);
        }
        if (item.review.summary) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'review-text';
            summaryDiv.textContent = truncateText(item.review.summary, 100);
            reviewSummary.appendChild(summaryDiv);
        }
        if (item.review.review_count) {
            const countDiv = document.createElement('div');
            countDiv.className = 'review-count';
            countDiv.textContent = `(${item.review.review_count} reviews)`;
            reviewSummary.appendChild(countDiv);
        }
        
        reviewHover.appendChild(reviewSummary);
        imageContainer.appendChild(reviewHover);
    }
    
    card.appendChild(imageContainer);
    
    // Card content
    const content = document.createElement('div');
    content.className = 'card-content';
    
    const title = document.createElement('h3');
    title.className = 'card-title';
    title.textContent = truncateText(item.title || 'Untitled', 60);
    content.appendChild(title);
    
    const meta = document.createElement('div');
    meta.className = 'card-meta';
    
    const price = document.createElement('span');
    price.className = 'card-price';
    price.textContent = formatPrice(item.price, item.currency);
    meta.appendChild(price);
    
    // Add score display
    if (item.score && item.score > 0) {
        const score = document.createElement('span');
        score.className = 'card-score';
        score.textContent = `★ ${item.score.toFixed(1)}`;
        meta.appendChild(score);
    }
    
    // Add score reason at the bottom of the card if available
    if (item.score_reason) {
        const reason = document.createElement('div');
        reason.className = 'card-reason';
        reason.textContent = item.score_reason;
        content.appendChild(reason);
    }
    
    if (item.posted_date) {
        const date = document.createElement('span');
        date.className = 'card-date';
        date.textContent = `Posted: ${formatDate(item.posted_date)}`;
        meta.appendChild(date);
    }
    
    const platform = document.createElement('span');
    platform.className = 'card-platform';
    platform.textContent = item.platform || 'Unknown';
    meta.appendChild(platform);
    
    content.appendChild(meta);
    card.appendChild(content);
    
    console.log('Card DOM element created for:', item.title || 'Untitled');
    return card;
}

/**
 * Render all cards from API response
 */
function renderCards(response) {
    const container = elements.resultsContainer;
    
    if (!container) {
        console.warn('renderCards: resultsContainer not found!');
        return;
    }
    
    if (!response || !response.results || response.results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
                <h2>No results found</h2>
                <p>Try a different search query.</p>
            </div>
        `;
        return;
    }
    
    console.log('Rendering', response.results.length, 'cards');
    
    // Build header
    let llmFilteredText = '';
    if (response.llm_filtered && response.llm_filtered > 0) {
        llmFilteredText = ` (${response.llm_filtered} items filtered by LLM)`;
    }
    let headerHtml = `
        <div class="results-header">
            <span class="results-count">${response.total_results} results for "${response.query}"${llmFilteredText}</span>
        </div>
    `;
    
    // Build cards grid - use DocumentFragment for better performance
    const fragment = document.createDocumentFragment();
    const grid = document.createElement('div');
    grid.className = 'cards-grid';
    
    console.log('Creating cards...');
    console.log('response.results:', response.results);
    console.log('response.results type:', typeof response.results);
    console.log('Is array?', Array.isArray(response.results));
    
    // Render all cards
    response.results.forEach((item, index) => {
        console.log(`Card ${index + 1}:`, item.title || 'Untitled');
        const cardElement = renderCard(item);
        console.log(`Card element type: ${cardElement ? cardElement.tagName : 'NULL'}`);
        if (cardElement) {
            grid.appendChild(cardElement);
        } else {
            console.error('Failed to create card element for item:', item);
        }
    });
    
    console.log('Grid children count:', grid.children.length);
    console.log('Grid innerHTML:', grid.innerHTML.substring(0, 200));
    
    fragment.appendChild(grid);
    
    // Set container content
    container.innerHTML = headerHtml;
    container.appendChild(fragment);
    
    console.log('Container innerHTML set, fragment appended');
    console.log('Container children:', container.children.length);
}

/**
 * Sort existing results client-side
 */
function sortResults(sortBy) {
    const container = elements.resultsContainer;
    if (!container || !container.querySelectorAll) return;
    
    const grid = container.querySelector('.cards-grid');
    if (!grid) return;
    
    const cards = grid.querySelectorAll('.card');
    if (cards.length === 0) return;
    
    // Convert NodeList to array for sorting
    const cardsArray = Array.from(cards);
    
    // Sort based on sortBy value using data attributes
    cardsArray.sort((a, b) => {
        const aPrice = parseFloat(a.dataset.price || '0');
        const bPrice = parseFloat(b.dataset.price || '0');
        const aScore = parseFloat(a.dataset.score || '0');
        const bScore = parseFloat(b.dataset.score || '0');
        const aDate = a.dataset.date || '';
        const bDate = b.dataset.date || '';
        
        switch (sortBy) {
            case 'price_asc':
                return aPrice - bPrice;
            case 'price_desc':
                return bPrice - aPrice;
            case 'date':
                return bDate.localeCompare(aDate);
            case 'score':
            default:
                return bScore - aScore;
        }
    });
    
    // Clear grid and re-append sorted cards
    grid.innerHTML = '';
    cardsArray.forEach(card => grid.appendChild(card));
}

// ============================================
// Loading & Error States
// ============================================

/**
 * Show loading state
 */
function showLoading() {
    if (elements.loadingIndicator) {
        elements.loadingIndicator.style.display = 'flex';
    }
    if (elements.errorMessage) {
        elements.errorMessage.style.display = 'none';
    }
}

/**
 * Hide loading state
 */
function hideLoading() {
    if (elements.loadingIndicator) {
        elements.loadingIndicator.style.display = 'none';
    }
}

/**
 * Show error message
 */
function showError(message) {
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
        elements.errorMessage.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            if (elements.errorMessage) {
                elements.errorMessage.style.display = 'none';
            }
        }, 5000);
    }
}

// ============================================
// Search Submission
// ============================================

/**
 * Handle form submission (fallback for inline handler)
 */
function handleFormSubmit(event) {
    if (event) {
        event.preventDefault();
    }
    submitSearch();
    return false;
}

/**
 * Build query parameters from current state
 */
function buildQueryParams() {
    const params = new URLSearchParams();
    
    const query = elements.searchQuery?.value;
    if (query) {
        params.set('query', query);
    }
    
    // Get values from form or state
    params.set('max_results', CONFIG.defaultMaxResults);
    params.set('currency', CONFIG.defaultCurrency);
    
    // Get toggle values
    const useFilter = elements.toggleFilter?.value === 'true' || STATE.useFilter;
    const useReviews = elements.toggleReviews?.value === 'true' || STATE.useReviews;
    const useScoring = elements.toggleScoring?.value === 'true' || STATE.useScoring;
    
    params.set('use_filter', useFilter);
    params.set('use_reviews', useReviews);
    params.set('use_scoring', useScoring);
    
    // Get sort value
    const sortBy = elements.sortSelector?.value || STATE.sortBy;
    params.set('sort_by', sortBy);
    
    return params;
}

/**
 * Submit search via fetch API
 */
function submitSearch() {
    const query = elements.searchQuery?.value || document.getElementById('search-query')?.value;
    
    // Validate query
    if (!query || query.trim().length < 1) {
        showError('Please enter a search query');
        return;
    }
    
    // Update state
    STATE.currentQuery = query;
    STATE.isSearching = true;
    
    // Move search bar to top
    if (elements.searchContainer) {
        elements.searchContainer.classList.add('active');
        document.documentElement.style.paddingTop = '220px';
    }
    
    // Show loading
    showLoading();
    
    // Build URL
    const params = buildQueryParams();
    const url = `${CONFIG.apiBaseUrl}/search?${params.toString()}`;
    
    // Make fetch request
    fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('API Response:', data);
        
        // Handle both 'results' and 'result' field names for compatibility
        let results = data.results || data.result || [];
        
        // If still no results, check if data itself is an array
        if (!results || results.length === 0) {
            if (Array.isArray(data)) {
                results = data;
            }
        }
        
        console.log('Results:', results);
        console.log('Results length:', results.length);
        
        // Reconstruct the expected response structure if needed
        const normalizedResponse = {
            query: data.query || '',
            results: results,
            total_results: data.total_results || data.totalResults || results.length,
            llm_filtered: data.llm_filtered || 0,
            reviews: data.reviews || {},
            sort_by: data.sort_by || 'score',
            toggles: data.toggles || { filtering: true, reviewing: true, scoring: true }
        };
        
        // Render cards
        renderCards(normalizedResponse);
        STATE.isSearching = false;
    })
    .catch(error => {
        console.error('Search error:', error);
        showError(`Search failed: ${error.message}`);
        STATE.isSearching = false;
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Set sort value
 */
function setSort(sortBy) {
    STATE.sortBy = sortBy;
    if (elements.sortSelector) {
        elements.sortSelector.value = sortBy;
    }
}

/**
 * Set sort value and re-sort existing results (client-side only)
 */
function setSortAndSearch(sortBy) {
    setSort(sortBy);
    STATE.sortBy = sortBy;
    // Re-sort existing results without re-fetching
    sortResults(sortBy);
}

/**
 * Update toggle state
 */
function updateToggle(name, value) {
    switch (name) {
        case 'filter':
            STATE.useFilter = value;
            if (elements.toggleFilter) {
                elements.toggleFilter.value = value;
            }
            break;
        case 'reviews':
            STATE.useReviews = value;
            if (elements.toggleReviews) {
                elements.toggleReviews.value = value;
            }
            break;
        case 'scoring':
            STATE.useScoring = value;
            if (elements.toggleScoring) {
                elements.toggleScoring.value = value;
            }
            break;
    }
}

// ============================================
// Toggle Controls
// ============================================

function initToggleControls() {
    const toggleItems = document.querySelectorAll('.toggle-item input[type="checkbox"]');
    
    toggleItems.forEach((checkbox, index) => {
        const name = ['filter', 'reviews', 'scoring'][index];
        
        // Initialize from URL params or defaults
        const urlParams = new URLSearchParams(window.location.search);
        const paramValue = urlParams.get(name);
        const isChecked = paramValue !== 'false';
        
        checkbox.checked = isChecked;
        updateToggle(name, isChecked);
        
        // Add change listener
        checkbox.addEventListener('change', function() {
            updateToggle(name, this.checked);
        });
    });
}

// ============================================
// Sort Controls
// ============================================

function initSortControls() {
    const sortButtons = document.querySelectorAll('.sort-button');
    
    sortButtons.forEach(button => {
        const sortBy = button.dataset.sort;
        
        // Initialize active state from URL or default
        const urlParams = new URLSearchParams(window.location.search);
        const paramValue = urlParams.get('sort_by') || 'score';
        
        if (sortBy === paramValue) {
            button.classList.add('active');
            setSort(sortBy);
        } else {
            button.classList.remove('active');
        }
        
        // Add click listener
        button.addEventListener('click', function() {
            // Update active state
            sortButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            setSort(sortBy);
            
            // Re-sort existing results client-side
            if (STATE.currentQuery) {
                sortResults(sortBy);
            }
        });
    });
}

// ============================================
// Keyboard Navigation
// ============================================

function initKeyboardNavigation() {
    document.addEventListener('keydown', function(evt) {
        // Allow Enter key to submit search
        if (evt.key === 'Enter' && evt.target === elements.searchQuery) {
            evt.preventDefault();
            submitSearch();
        }
    });
}

// ============================================
// Form Submission
// ============================================

function initFormSubmit() {
    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('submit', function(evt) {
            evt.preventDefault();
            submitSearch();
        });
    } else {
        console.error('ERROR: search-form not found!');
    }
}

// ============================================
// Initialize on DOM Load
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    cacheElements();
    
    // Initialize all components
    initToggleControls();
    initSortControls();
    initFormSubmit();
    initKeyboardNavigation();
    
    console.log('✓ Second-Hand Search initialized');
});

// Also log when script loads (before DOMContentLoaded)
console.log('✓ app.js loaded');

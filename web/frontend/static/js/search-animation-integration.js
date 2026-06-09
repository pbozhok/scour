/**
 * Search Animation Integration
 * 
 * This script integrates the SearchAnimation component with the existing
 * search functionality in app.js.
 * 
 * Uses Server-Sent Events (SSE) for real-time phase updates from backend.
 * Connects to SSE BEFORE search starts to catch all phase updates.
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if SearchAnimation class exists
    if (typeof SearchAnimation === 'undefined') {
        console.error('SearchAnimation class not loaded. Check that search-animation.js is loaded before this script.');
        return;
    }

    // Initialize SearchAnimation
    let searchAnimation = null;
    let currentSearchId = null;
    
    try {
        const container = document.getElementById('search-animation');
        if (container) {
            searchAnimation = new SearchAnimation('#search-animation', {
                animationStyle: 'chasing-dots',
                showProgressBar: true,
                showIcon: false,
                sseEndpoint: '/api/v1/search/phases'
            });
        } else {
            console.warn('SearchAnimation container not found');
            return;
        }
    } catch (error) {
        console.error('Failed to initialize SearchAnimation:', error);
        return;
    }

    // Save the original complete method ONCE so connectToSSE can re-wrap it
    // without stacking closures on every search.
    const originalAnimationComplete = searchAnimation.complete.bind(searchAnimation);

    // Function to close existing SSE connection
    function closeSSEConnection() {
        if (searchAnimation && searchAnimation.eventSource) {
            searchAnimation.closeSSE();
        }
        currentSearchId = null;
    }

    // Function to connect to SSE for a specific search
    function connectToSSE(searchId) {
        // Close any existing connection
        closeSSEConnection();
        
        if (!searchAnimation || !searchId) return null;
        
        currentSearchId = searchId;
        
        // Update the SearchAnimation's SSE endpoint with the search_id
        searchAnimation.options.sseEndpoint = `/api/v1/search/phases?search_id=${encodeURIComponent(searchId)}`;
        
        try {
            // Use the SearchAnimation's built-in SSE connection
            searchAnimation.connectSSE();

            // Re-wrap complete each time using the saved original, not the
            // previously-wrapped version, so closures don't stack across searches.
            searchAnimation.complete = function() {
                originalAnimationComplete();
                setTimeout(() => {
                    const container = document.getElementById('search-animation');
                    if (container) container.style.display = 'none';
                }, 1000);
            };

            return searchAnimation.eventSource;
            
        } catch (error) {
            console.warn('⚠ SSE not supported, falling back to client-side estimation:', error);
            // Ensure client-side estimation is running
            if (searchAnimation && !searchAnimation.sseConnected) {
                if (searchAnimation.startClientSideProgression) {
                    searchAnimation.startClientSideProgression();
                }
            }
            return null;
        }
    }

    // Override loading functions if SearchAnimation is available
    if (searchAnimation) {
        // Save original functions
        const originalShowLoading = window.showLoading;
        const originalHideLoading = window.hideLoading;
        const originalShowError = window.showError;

        // Override showLoading
        window.showLoading = function() {
            const animationContainer = document.getElementById('search-animation');
            if (animationContainer) {
                animationContainer.style.display = 'flex';
            }
            
            if (searchAnimation) {
                searchAnimation.reset();
                searchAnimation.start();
            }
            
            // Hide old loading indicator
            const oldLoading = document.getElementById('loading-indicator');
            const oldError = document.getElementById('error-message');
            if (oldLoading) oldLoading.style.display = 'none';
            if (oldError) oldError.style.display = 'none';
            
            // Call original if it exists
            if (originalShowLoading) originalShowLoading();
        };

        // Override hideLoading
        window.hideLoading = function() {
            // Close SSE connection
            closeSSEConnection();
            
            // Hide old loading indicator
            const oldLoading = document.getElementById('loading-indicator');
            if (oldLoading) oldLoading.style.display = 'none';
            
            // Call original if it exists
            if (originalHideLoading) originalHideLoading();
        };

        // Override showError
        window.showError = function(message) {
            if (searchAnimation) {
                searchAnimation.error(message);
            }
            
            // Close SSE connection on error
            closeSSEConnection();
            
            // Hide animation after error is shown
            const animationContainer = document.getElementById('search-animation');
            if (animationContainer) {
                setTimeout(() => {
                    animationContainer.style.display = 'none';
                }, 2000);
            }
            
            // Fallback to old error message
            const oldError = document.getElementById('error-message');
            if (oldError) {
                oldError.textContent = message;
                oldError.style.display = 'block';
                
                // Hide after 5 seconds
                setTimeout(() => {
                    if (oldError) oldError.style.display = 'none';
                }, 5000);
            }
            
            // Call original if it exists
            if (originalShowError) originalShowError(message);
        };

        // Wrap submitSearch to inject search_id and SSE pre-connection.
        // All search params (toggles, sort, etc.) still come from buildQueryParams()
        // in app.js — we only append search_id on top.
        if (window.submitSearch) {
            const originalSubmitSearch = window.submitSearch;

            window.submitSearch = function() {
                const query = document.getElementById('search-query')?.value || '';

                if (!query || query.trim().length < 1) {
                    if (window.showError) window.showError('Please enter a search query');
                    return;
                }

                // Generate search_id and open SSE BEFORE showLoading so we
                // don't miss the early "initiating" phase event.
                const searchId = 'search-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                connectToSSE(searchId);

                // Let the original handle state updates, search bar move,
                // showLoading, buildQueryParams, fetch, renderCards, and hideLoading —
                // but intercept fetch to append search_id to the URL.
                const nativeFetch = window.fetch;
                window.fetch = function(url, init) {
                    if (typeof url === 'string' && url.includes('/api/v1/search')) {
                        const sep = url.includes('?') ? '&' : '?';
                        url = `${url}${sep}search_id=${encodeURIComponent(searchId)}`;
                    }
                    window.fetch = nativeFetch;  // restore immediately after one use
                    return nativeFetch.call(this, url, init);
                };

                originalSubmitSearch();
            };
        } else {
            console.warn('submitSearch function not found');
        }


    }
});

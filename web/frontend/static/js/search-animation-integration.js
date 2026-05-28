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
            
            // Add custom handler for complete state to auto-hide animation
            const originalComplete = searchAnimation.complete.bind(searchAnimation);
            searchAnimation.complete = function() {
                originalComplete();
                // Auto-hide animation after showing completion
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

        // Patch submitSearch to generate search_id and connect to SSE before making request
        if (window.submitSearch) {
            const originalSubmitSearch = window.submitSearch;
            
            window.submitSearch = function() {
                const query = document.getElementById('search-query')?.value || '';
                
                // Validate query
                if (!query || query.trim().length < 1) {
                    if (window.showError) window.showError('Please enter a search query');
                    return;
                }
                
                // Update state
                STATE.currentQuery = query;
                STATE.isSearching = true;
                
                // Move search bar to top
                const searchContainer = document.getElementById('search-container');
                if (searchContainer) {
                    searchContainer.classList.add('active');
                    document.documentElement.style.paddingTop = '220px';
                }
                
                // Generate search_id for this search
                const generatedSearchId = 'search-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                
                // Connect to SSE FIRST, before showing loading animation
                // This ensures we don't miss early phase updates
                connectToSSE(generatedSearchId);
                
                // Show loading with animation (this starts client-side estimation)
                if (window.showLoading) window.showLoading();
                
                // Now build URL with the generated search_id
                const params = new URLSearchParams();
                params.set('query', query);
                params.set('max_results', 40);
                params.set('currency', 'EUR');
                params.set('use_filter', true);
                params.set('use_reviews', true);
                params.set('use_scoring', true);
                params.set('sort_by', 'score');
                params.set('search_id', generatedSearchId);
                
                const url = `/api/v1/search?${params.toString()}`;
                
                // Make fetch request with our search_id
                const originalFetch = window.fetch;
                window.fetch(url, {
                    method: 'GET',
                    headers: {'Accept': 'application/json'}
                })
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (window.renderCards) window.renderCards(data);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    if (window.showError) window.showError(`Search failed: ${error.message}`);
                })
                .finally(() => {
                    STATE.isSearching = false;
                });
            };
        } else {
            console.warn('submitSearch function not found');
        }


    }
});

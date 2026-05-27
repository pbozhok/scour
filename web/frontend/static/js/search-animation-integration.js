/**
 * Search Animation Integration
 * 
 * This script integrates the SearchAnimation component with the existing
 * search functionality in app.js.
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
    
    try {
        const container = document.getElementById('search-animation');
        if (container) {
            searchAnimation = new SearchAnimation('#search-animation', {
                animationStyle: 'chasing-dots',
                showProgressBar: true,
                showIcon: false,
                sseEndpoint: '/api/v1/search/phases'
            });
            
            console.log('\u2713 SearchAnimation initialized');
        } else {
            console.warn('SearchAnimation container not found');
        }
    } catch (error) {
        console.error('Failed to initialize SearchAnimation:', error);
    }

    // Override loading functions if SearchAnimation is available
    if (searchAnimation) {
        // Save original functions if they exist
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
            const animationContainer = document.getElementById('search-animation');
            if (animationContainer) {
                animationContainer.style.display = 'none';
            }
            
            if (searchAnimation) {
                searchAnimation.complete();
            }
            
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

        console.log('\u2713 SearchAnimation integration complete');
    }
});

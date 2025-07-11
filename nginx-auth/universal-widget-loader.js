// 🔐 Universal Supabase Studio Session Widget Auto-Loader
// ========================================================
// Usage: Copy-paste this entire script into browser console
// Or save as bookmark: javascript:(paste this code here)

(function() {
    'use strict';
    
    console.log('🚀 Universal Widget Auto-Loader Started');
    
    // Check if widget already loaded
    if (window.sessionWidget && window.sessionWidget.isActive) {
        console.log('✅ Session widget already active');
        return;
    }
    
    // Prevent multiple instances
    if (window.universalWidgetLoader) {
        console.log('⚠️ Auto-loader already running');
        return;
    }
    window.universalWidgetLoader = true;
    
    // Configuration
    const config = {
        widgetUrl: '/session-widget.js',
        maxRetries: 5,
        retryDelay: 2000,
        checkInterval: 3000
    };
    
    let retries = 0;
    let loadAttempted = false;
    
    // Widget loading function
    function loadWidget() {
        if (loadAttempted && window.sessionWidget && window.sessionWidget.isActive) {
            console.log('✅ Widget successfully loaded and active');
            return true;
        }
        
        if (retries >= config.maxRetries) {
            console.warn('❌ Max retries reached. Widget may not be available.');
            return false;
        }
        
        console.log(`🔄 Loading session widget (attempt ${retries + 1}/${config.maxRetries})`);
        retries++;
        loadAttempted = true;
        
        return fetch(config.widgetUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.text();
            })
            .then(code => {
                console.log(`✅ Widget script loaded (${code.length} chars)`);
                eval(code);
                
                // Verify widget loaded successfully
                setTimeout(() => {
                    if (window.sessionWidget && window.sessionWidget.isActive) {
                        console.log('🎉 Session widget auto-loaded successfully!');
                    } else {
                        console.warn('⚠️ Widget script executed but not active');
                    }
                }, 500);
                
                return true;
            })
            .catch(error => {
                console.error(`❌ Widget load failed (attempt ${retries}):`, error);
                
                // Retry after delay
                setTimeout(() => {
                    loadWidget();
                }, config.retryDelay);
                
                return false;
            });
    }
    
    // Multiple trigger mechanisms
    
    // 1. Immediate load if DOM ready
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log('📄 DOM ready, loading widget immediately');
        loadWidget();
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('📄 DOMContentLoaded triggered, loading widget');
            loadWidget();
        });
    }
    
    // 2. Load after window fully loaded
    window.addEventListener('load', () => {
        setTimeout(() => {
            if (!loadAttempted || (window.sessionWidget && !window.sessionWidget.isActive)) {
                console.log('🏁 Window load complete, ensuring widget is loaded');
                loadWidget();
            }
        }, 1000);
    });
    
    // 3. Periodic check for Supabase Studio UI elements
    function checkForSupabaseUI() {
        const indicators = [
            'div[data-testid="dashboard"]',
            'nav[data-testid="sidebar"]', 
            '.sb-grid-container',
            '[class*="supabase"]',
            '[class*="dashboard"]'
        ];
        
        const found = indicators.some(selector => document.querySelector(selector));
        
        if (found && !loadAttempted) {
            console.log('🎯 Supabase Studio UI detected, loading widget');
            loadWidget();
            return true;
        }
        
        return false;
    }
    
    // 4. MutationObserver for dynamic content
    const observer = new MutationObserver(() => {
        if (checkForSupabaseUI()) {
            observer.disconnect();
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // 5. Fallback periodic check
    const intervalCheck = setInterval(() => {
        if (window.sessionWidget && window.sessionWidget.isActive) {
            console.log('✅ Widget active, stopping checks');
            clearInterval(intervalCheck);
            observer.disconnect();
            return;
        }
        
        if (checkForSupabaseUI() || document.querySelector('#root')) {
            console.log('🔄 UI detected via interval check');
            loadWidget();
        }
    }, config.checkInterval);
    
    // 6. Header-based detection
    if (document.querySelector('meta[name="X-Session-Widget-Available"]') || 
        document.querySelector('meta[name="X-Widget-Auto-Load"]')) {
        console.log('📡 Widget headers detected, loading immediately');
        loadWidget();
    }
    
    // 7. Manual trigger function for console
    window.loadSessionWidget = function(force = false) {
        if (force) {
            retries = 0;
            loadAttempted = false;
        }
        return loadWidget();
    };
    
    console.log('🔧 Auto-loader installed. Manual trigger: loadSessionWidget()');
    
    // Cleanup after 2 minutes
    setTimeout(() => {
        clearInterval(intervalCheck);
        observer.disconnect();
        console.log('🧹 Auto-loader cleanup completed');
    }, 120000);
    
})(); 
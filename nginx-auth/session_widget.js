// Supabase Studio Session Management Widget
(function() {
    'use strict';
    
    // Prevent multiple instances
    if (window.sessionWidget && window.sessionWidget.isActive) {
        console.log('🔐 Session widget already active');
        return;
    }
    
    let sessionWidgetElement = null;
    let sessionInterval = null;
    
    // Global API
    window.sessionWidget = {
        isActive: false,
        element: null,
        destroy: function() {
            if (sessionInterval) {
                clearInterval(sessionInterval);
                sessionInterval = null;
            }
            if (sessionWidgetElement) {
                sessionWidgetElement.remove();
                sessionWidgetElement = null;
            }
            this.isActive = false;
            this.element = null;
            console.log('🔐 Session widget destroyed');
        }
    };
    
    function createSessionWidget() {
        // Create session widget container
        const widget = document.createElement('div');
        widget.id = 'supabase-session-widget';
        widget.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 2147483647;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 16px;
            border-radius: 10px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 250px;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.2);
        `;
        
        // Session info display
        const sessionInfo = document.createElement('div');
        sessionInfo.id = 'session-info';
        sessionInfo.style.cssText = 'flex: 1; font-size: 13px; line-height: 1.4;';
        
        // Logout button
        const logoutBtn = document.createElement('button');
        logoutBtn.innerHTML = '🚪 Logout';
        logoutBtn.style.cssText = `
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
            white-space: nowrap;
        `;
        
        logoutBtn.onmouseover = function() {
            this.style.background = 'rgba(255,255,255,0.25)';
            this.style.transform = 'translateY(-1px)';
        };
        
        logoutBtn.onmouseout = function() {
            this.style.background = 'rgba(255,255,255,0.15)';
            this.style.transform = 'translateY(0)';
        };
        
        logoutBtn.onclick = function() {
            if (confirm('🔐 Are you sure you want to logout?\n\nYour session will be terminated and you\'ll be redirected to the login page.')) {
                window.location.href = '/logout';
            }
        };
        
        widget.appendChild(sessionInfo);
        widget.appendChild(logoutBtn);
        
        return widget;
    }
    
    function updateSessionInfo() {
        if (!sessionWidgetElement) return;
        
        fetch('/session', {
            method: 'GET',
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            const sessionInfo = document.getElementById('session-info');
            if (!sessionInfo) return;
            
            if (data.authenticated) {
                const remainingMinutes = Math.floor(data.session_remaining / 60);
                const remainingSeconds = data.session_remaining % 60;
                
                let timeDisplay;
                if (remainingMinutes > 0) {
                    timeDisplay = `${remainingMinutes}m ${remainingSeconds}s`;
                } else {
                    timeDisplay = `${remainingSeconds}s`;
                }
                
                sessionInfo.innerHTML = `
                    <div style="font-weight: 600; margin-bottom: 2px;">👤 ${data.username}</div>
                    <div style="opacity: 0.9; font-size: 12px;">⏱️ ${timeDisplay} remaining</div>
                `;
                
                // Warning styles for low session time
                if (data.session_remaining <= 300) { // 5 minutes
                    sessionWidgetElement.style.background = 'linear-gradient(135deg, #ff6b6b, #ee5a6f)';
                    
                    if (data.session_remaining <= 60) { // 1 minute
                        sessionWidgetElement.style.animation = 'pulse 1s infinite';
                        if (!document.getElementById('pulse-style')) {
                            const style = document.createElement('style');
                            style.id = 'pulse-style';
                            style.textContent = `
                                @keyframes pulse {
                                    0% { transform: scale(1); box-shadow: 0 8px 25px rgba(0,0,0,0.2); }
                                    50% { transform: scale(1.02); box-shadow: 0 10px 30px rgba(255,0,0,0.4); }
                                    100% { transform: scale(1); box-shadow: 0 8px 25px rgba(0,0,0,0.2); }
                                }
                            `;
                            document.head.appendChild(style);
                        }
                    }
                } else {
                    // Reset to normal style
                    sessionWidgetElement.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
                    sessionWidgetElement.style.animation = 'none';
                }
            } else {
                sessionInfo.innerHTML = '<div style="color: #ffeb3b; font-weight: 600;">⚠️ Session expired</div>';
                setTimeout(() => {
                    window.location.href = '/auth';
                }, 2000);
            }
        })
        .catch(error => {
            console.error('Session check failed:', error);
            const sessionInfo = document.getElementById('session-info');
            if (sessionInfo) {
                sessionInfo.innerHTML = '<div style="color: #ffeb3b; font-size: 12px;">⚠️ Connection error</div>';
            }
        });
    }
    
    function initSessionWidget() {
        // Skip on auth pages
        if (window.location.pathname.includes('/auth')) {
            console.log('❌ Skipping widget on auth page');
            return;
        }
        
        // Wait for DOM
        if (!document.body) {
            setTimeout(initSessionWidget, 100);
            return;
        }
        
        // Remove existing widget
        const existing = document.getElementById('supabase-session-widget');
        if (existing) {
            existing.remove();
        }
        
        try {
            // Create and add widget
            sessionWidgetElement = createSessionWidget();
            document.body.appendChild(sessionWidgetElement);
            
            // Update global API
            window.sessionWidget.isActive = true;
            window.sessionWidget.element = sessionWidgetElement;
            
            // Start session monitoring
            updateSessionInfo(); // Initial update
            sessionInterval = setInterval(updateSessionInfo, 15000); // Update every 15 seconds
            
            console.log('🔐 Enhanced Supabase Studio Session Widget initialized');
            
        } catch (error) {
            console.error('❌ Error creating session widget:', error);
            window.sessionWidget.isActive = false;
        }
    }
    
    // Initialize with multiple triggers
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSessionWidget);
    } else {
        initSessionWidget();
    }
    
    // Fallback after delay
    setTimeout(initSessionWidget, 1000);
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (window.sessionWidget) {
            window.sessionWidget.destroy();
        }
    });
    
    console.log('🚀 Session widget auto-loader initialized');
})(); 
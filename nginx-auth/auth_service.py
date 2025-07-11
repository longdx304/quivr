from flask import Flask, request, jsonify, render_template_string, redirect, make_response
import hashlib
import hmac
import time
import os
from datetime import datetime

app = Flask(__name__)

# Configuration
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour default

# Simple session store (in production, use Redis or database)
sessions = {}

def create_session_token(username):
    """Create a secure session token"""
    timestamp = str(int(time.time()))
    data = f"{username}:{timestamp}"
    signature = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}:{signature}"

def verify_session_token(token):
    """Verify session token and check if it's still valid"""
    try:
        if not token:
            return False
            
        parts = token.split(':')
        if len(parts) != 3:
            return False
            
        username, timestamp, signature = parts
        data = f"{username}:{timestamp}"
        expected_sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return False
            
        # Check if session is expired
        session_time = int(timestamp)
        if time.time() - session_time > SESSION_TIMEOUT:
            return False
            
        return username
    except:
        return False

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Supabase Studio Authentication</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0; padding: 0; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
        }
        .login-container {
            background: white; padding: 40px; border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%; max-width: 400px; box-sizing: border-box;
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { 
            color: #333; margin: 0; font-size: 28px; font-weight: 600;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 500; }
        input[type="text"], input[type="password"] {
            width: 100%; padding: 12px; border: 2px solid #e1e5e9;
            border-radius: 8px; font-size: 16px; box-sizing: border-box;
            transition: border-color 0.3s ease;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none; border-color: #667eea;
        }
        .btn {
            width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; border: none; border-radius: 8px; font-size: 16px;
            font-weight: 600; cursor: pointer; transition: transform 0.2s ease;
        }
        .btn:hover { transform: translateY(-2px); }
        .error { 
            color: #dc3545; text-align: center; margin-top: 15px;
            padding: 10px; background: #f8d7da; border-radius: 6px;
        }
        .session-info {
            background: #d4edda; color: #155724; padding: 10px;
            border-radius: 6px; margin-bottom: 20px; text-align: center;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>🔐 Supabase Studio</h1>
            <p style="color: #666; margin: 0; font-size: 14px;">Secure Access Portal</p>
        </div>
        
        <div class="session-info">
            <strong>Session Timeout:</strong> {{ timeout }} minutes<br>
            <strong>Login Time:</strong> <span id="current-time"></span>
        </div>
        
        <form method="POST" action="/auth">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn">Sign In</button>
        </form>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
    
    <script>
        document.getElementById('current-time').textContent = new Date().toLocaleString();
    </script>
</body>
</html>
"""

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'GET':
        return render_template_string(LOGIN_PAGE, timeout=SESSION_TIMEOUT//60)
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Create session
        token = create_session_token(username)
        sessions[token] = {
            'username': username,
            'created_at': time.time(),
            'last_access': time.time()
        }
        
        # Set cookie and redirect
        response = make_response(redirect('/'))
        response.set_cookie(
            'session_token', 
            token, 
            max_age=SESSION_TIMEOUT,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        return response
    else:
        return render_template_string(LOGIN_PAGE, error="Invalid credentials", timeout=SESSION_TIMEOUT//60), 401

@app.route('/auth/verify')
def verify():
    """Endpoint for nginx auth_request"""
    token = request.cookies.get('session_token')
    username = verify_session_token(token)
    
    if username and token in sessions:
        # Update last access time
        sessions[token]['last_access'] = time.time()
        return '', 200
    else:
        # Clean up expired session
        if token and token in sessions:
            del sessions[token]
        return '', 401

@app.route('/auth/logout')
def logout():
    """Logout endpoint"""
    token = request.cookies.get('session_token')
    if token and token in sessions:
        del sessions[token]
    
    response = make_response(redirect('/auth'))
    response.set_cookie('session_token', '', expires=0)
    return response

@app.route('/auth/status')
def status():
    """Get session status"""
    token = request.cookies.get('session_token')
    username = verify_session_token(token)
    
    if username and token in sessions:
        session_data = sessions[token]
        remaining_time = SESSION_TIMEOUT - (time.time() - session_data['created_at'])
        return jsonify({
            'authenticated': True,
            'username': username,
            'session_remaining': max(0, int(remaining_time)),
            'created_at': datetime.fromtimestamp(session_data['created_at']).isoformat(),
            'last_access': datetime.fromtimestamp(session_data['last_access']).isoformat()
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/health')
def health():
    return 'Auth Service OK'

@app.route('/auto-loader.js')
def auto_loader():
    """Serve universal auto-loader script"""
    try:
        with open('/app/universal-widget-loader.js', 'r') as f:
            js_content = f.read()
    except FileNotFoundError:
        # Fallback simple auto-loader
        js_content = '''
(function(){
    if(window.sessionWidget && window.sessionWidget.isActive) return;
    console.log("🔄 Loading session widget...");
    fetch("/session-widget.js").then(r=>r.text()).then(eval).catch(console.error);
})();
        '''
    
    response = make_response(js_content)
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/session-widget.js')
def session_widget():
    """Serve session widget JavaScript"""
    js_content = '''
// Enhanced Supabase Studio Session Widget - Auto-loader
(function() {
    "use strict";
    
    let sessionWidget = null;
    let sessionInterval = null;
    
    // Prevent multiple widgets
    if (document.getElementById("supabase-session-widget")) {
        return;
    }
    
    // Auto-detect Supabase Studio environment
    function isSupabaseStudio() {
        return window.location.hostname === 'localhost' && 
               window.location.port === '54323' &&
               !window.location.pathname.includes('/auth');
    }
    
    // Auto-initialize if in Supabase Studio
    if (!isSupabaseStudio()) {
        console.log('Session widget: Not in Supabase Studio environment');
        return;
    }
    
    function createSessionWidget() {
        const widget = document.createElement("div");
        widget.id = "supabase-session-widget";
        widget.style.cssText = `
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            z-index: 2147483647 !important;
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
        
        const sessionInfo = document.createElement("div");
        sessionInfo.id = "session-info";
        sessionInfo.style.cssText = "flex: 1; font-size: 13px; line-height: 1.4;";
        
        const logoutBtn = document.createElement("button");
        logoutBtn.innerHTML = "🚪 Logout";
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
            this.style.background = "rgba(255,255,255,0.25)";
            this.style.transform = "translateY(-1px)";
        };
        
        logoutBtn.onmouseout = function() {
            this.style.background = "rgba(255,255,255,0.15)";
            this.style.transform = "translateY(0)";
        };
        
        logoutBtn.onclick = function() {
            if (confirm("🔐 Are you sure you want to logout?\\n\\nYour session will be terminated and you'll be redirected to the login page.")) {
                window.location.href = "/logout";
            }
        };
        
        widget.appendChild(sessionInfo);
        widget.appendChild(logoutBtn);
        return widget;
    }
    
    function updateSessionInfo() {
        if (!sessionWidget) return;
        
        fetch("/session", {
            method: "GET",
            credentials: "same-origin"
        })
        .then(response => response.json())
        .then(data => {
            const sessionInfo = document.getElementById("session-info");
            if (!sessionInfo) return;
            
            if (data.authenticated) {
                const remainingMinutes = Math.floor(data.session_remaining / 60);
                const remainingSeconds = data.session_remaining % 60;
                
                let timeDisplay;
                if (remainingMinutes > 0) {
                    timeDisplay = remainingMinutes + "m " + remainingSeconds + "s";
                } else {
                    timeDisplay = remainingSeconds + "s";
                }
                
                sessionInfo.innerHTML = 
                    "<div style=\\"font-weight: 600; margin-bottom: 2px;\\">👤 " + data.username + "</div>" +
                    "<div style=\\"opacity: 0.9; font-size: 12px;\\">⏱️ " + timeDisplay + " remaining</div>";
                
                // Warning styles for low session time
                if (data.session_remaining <= 300) { // 5 minutes
                    sessionWidget.style.background = "linear-gradient(135deg, #ff6b6b, #ee5a6f)";
                    
                    if (data.session_remaining <= 60) { // 1 minute
                        sessionWidget.style.animation = "pulse 1s infinite";
                        if (!document.getElementById("pulse-style")) {
                            const style = document.createElement("style");
                            style.id = "pulse-style";
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
                    sessionWidget.style.background = "linear-gradient(135deg, #667eea, #764ba2)";
                    sessionWidget.style.animation = "none";
                }
            } else {
                sessionInfo.innerHTML = "<div style=\\"color: #ffeb3b; font-weight: 600;\\">⚠️ Session expired</div>";
                setTimeout(() => {
                    window.location.href = "/auth";
                }, 2000);
            }
        })
        .catch(error => {
            console.error("Session check failed:", error);
            const sessionInfo = document.getElementById("session-info");
            if (sessionInfo) {
                sessionInfo.innerHTML = "<div style=\\"color: #ffeb3b; font-size: 12px;\\">⚠️ Connection error</div>";
            }
        });
    }
    
    function initSessionWidget() {
        console.log("🔄 initSessionWidget called, readyState:", document.readyState);
        
        // Don't add widget to login/auth pages
        if (window.location.pathname.includes("/auth")) {
            console.log("❌ Skipping widget on auth page");
            return;
        }
        
        // Skip if widget already exists
        if (document.getElementById("supabase-session-widget")) {
            console.log("✅ Widget already exists");
            return;
        }
        
        // Ensure body exists
        if (!document.body) {
            console.log("⏳ Body not ready, retrying in 100ms");
            setTimeout(initSessionWidget, 100);
            return;
        }
        
        try {
            // Create and add widget
            sessionWidget = createSessionWidget();
            document.body.appendChild(sessionWidget);
            console.log("✅ Session widget DOM element created and added");
            
            // Start session monitoring
            updateSessionInfo(); // Initial update
            sessionInterval = setInterval(updateSessionInfo, 15000); // Update every 15 seconds
            
            console.log("🔐 Enhanced Supabase Studio Session Widget initialized successfully");
            
            // Visual confirmation
            setTimeout(() => {
                const widget = document.getElementById("supabase-session-widget");
                if (widget) {
                    console.log("✅ Widget confirmed in DOM:", widget.getBoundingClientRect());
                } else {
                    console.error("❌ Widget missing from DOM after creation");
                }
            }, 500);
            
        } catch (error) {
            console.error("❌ Error creating session widget:", error);
        }
    }
    
    // Auto-initialize with multiple triggers
    initSessionWidget();
    
    // Fallback triggers to ensure loading
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSessionWidget);
    }
    
    // Additional fallback after delay
    setTimeout(initSessionWidget, 2000);
    
    // Try to load when Supabase Studio is fully ready
    const checkAndLoad = () => {
        if (document.querySelector('[data-testid="dashboard"]') || 
            document.querySelector('.supabase-ui') ||
            document.querySelector('#__next')) {
            initSessionWidget();
        } else {
            setTimeout(checkAndLoad, 1000);
        }
    };
    
    setTimeout(checkAndLoad, 500);
    
    // Cleanup on page unload
    window.addEventListener("beforeunload", function() {
        if (sessionInterval) {
            clearInterval(sessionInterval);
        }
    });
    
    console.log("🚀 Session widget auto-loader initialized");
})();
'''
    
    response = make_response(js_content)
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 
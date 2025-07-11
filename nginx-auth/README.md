# 🔐 Supabase Studio Authentication System

Secure authentication proxy for Supabase Studio with session management and **multiple widget loading options**.

## 🚀 **Quick Start**

1. **Start the system**:

```bash
docker-compose up --build -d nginx-auth-proxy
```

2. **Access Supabase Studio**: http://localhost:54323

   - **Username**: `admin`
   - **Password**: `admin123`

3. **Load session widget** (choose your preferred method):

### **Method 1: Simple Console Command** ⚡

```javascript
fetch("/session-widget.js")
  .then((r) => r.text())
  .then(eval);
```

### **Method 2: Universal Auto-Loader** 🔄

```javascript
fetch("/auto-loader.js")
  .then((r) => r.text())
  .then(eval);
```

### **Method 3: Quick Check & Load** 🎯

```javascript
if (!window.sessionWidget?.isActive)
  fetch("/session-widget.js")
    .then((r) => r.text())
    .then(eval);
```

Copy any command to browser console (`F12` → Console tab).

## 🔧 **System Architecture**

```
User → Port 54323 (Nginx + Auth) → Port 54325 (Supabase Studio)
                ↓
         Port 5000 (Flask Auth Service)
```

- **Port 54323**: Public access with authentication
- **Port 54325**: Internal Supabase Studio (protected)
- **Port 5000**: Flask authentication service

## 📋 **Features**

### ✅ **Authentication**

- Login required to access Supabase Studio
- Session-based authentication (60 minutes)
- Secure logout functionality

### ✅ **Session Widget** (bottom-right corner)

- Shows current user and remaining time
- Real-time countdown timer
- One-click logout button
- Visual warnings when session expires
- Duplicate protection with global API

### ✅ **Multiple Loading Options**

1. **Manual loading**: Simple console command
2. **Auto-loader**: Universal script with retry logic
3. **Global API**: `window.sessionWidget.isActive` check

### ✅ **Security**

- HMAC-signed session tokens
- Configurable session timeout
- Auto-logout on expiration
- Protected internal routes

## 🔗 **Endpoints**

| Endpoint             | Purpose                         |
| -------------------- | ------------------------------- |
| `/`                  | Supabase Studio (requires auth) |
| `/auth`              | Login page                      |
| `/auth/logout`       | Logout endpoint                 |
| `/session`           | Session status                  |
| `/session-widget.js` | Widget JavaScript               |
| `/auto-loader.js`    | Universal auto-loader           |
| `/health`            | Health check                    |

## ⚙️ **Configuration**

Environment variables in `docker-compose.yml`:

```yaml
environment:
  - SESSION_TIMEOUT=3600 # Session duration (seconds)
  - ADMIN_USERNAME=admin # Login username
  - ADMIN_PASSWORD=admin123 # Login password
```

## 🎯 **Usage**

### **Login**

1. Go to http://localhost:54323
2. Enter credentials: `admin` / `admin123`
3. Access Supabase Studio normally

### **Load Session Widget**

**Option A - Basic (fastest)**:

```javascript
fetch("/session-widget.js")
  .then((r) => r.text())
  .then(eval);
```

**Option B - Auto-loader (smarter)**:

```javascript
fetch("/auto-loader.js")
  .then((r) => r.text())
  .then(eval);
```

**Option C - With check**:

```javascript
if (!window.sessionWidget?.isActive)
  fetch("/session-widget.js")
    .then((r) => r.text())
    .then(eval);
```

Widget appears in **bottom-right corner** with:

- 👤 Username
- ⏱️ Session timer (real-time countdown)
- 🚪 Logout button

### **Widget Features**

- **Duplicate protection**: Won't create multiple widgets
- **Global API**: `window.sessionWidget.isActive`, `.destroy()`
- **Auto-cleanup**: Removes on logout/session expiry
- **Visual warnings**: Red color + pulse when < 1 minute
- **Smart positioning**: Bottom-right, high z-index

### **Logout**

- Click logout button in widget, OR
- Go to `/logout`, OR
- Wait for session to expire

## 🐛 **Troubleshooting**

### **Can't access Studio**

- Check containers: `docker-compose ps`
- Verify credentials: `admin` / `admin123`
- Check health: http://localhost:54323/health

### **Widget not working**

- Ensure you're on http://localhost:54323
- Check console for errors (`F12`)
- Try: `window.sessionWidget?.isActive` to check status
- Force reload: `window.sessionWidget?.destroy()` then load again

### **Session issues**

- Check session status: http://localhost:54323/session
- Clear browser cookies if needed
- Restart container: `docker-compose restart nginx-auth-proxy`

## 📂 **Files Structure**

```
nginx-auth/
├── Dockerfile                    # Multi-service container
├── nginx.conf                    # Nginx proxy configuration
├── auth_service.py               # Flask authentication service
├── session_widget.js             # Session management widget
├── universal-widget-loader.js    # Advanced auto-loader
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔄 **Start/Stop**

```bash
# Start
docker-compose up --build -d nginx-auth-proxy

# Stop
docker-compose down nginx-auth-proxy

# Restart
docker-compose restart nginx-auth-proxy

# View logs
docker-compose logs -f nginx-auth-proxy
```

## 🌟 **Benefits**

- ✅ **Secure**: No unauthenticated access to Supabase Studio
- ✅ **Simple**: One-command deployment
- ✅ **Flexible**: Multiple widget loading options
- ✅ **User-friendly**: Clear session management
- ✅ **Reliable**: Manual loading works 100% of the time
- ✅ **Smart**: Auto-loader with retry logic and duplicate protection

## 💡 **Tại sao Auto-inject không hoạt động?**

Nginx `sub_filter` không hoạt động với Supabase Studio vì:

1. **SPA (Single Page App)**: React app load động, không có `<head>` cố định
2. **Content-Type**: Một số responses không phải `text/html`
3. **Gzip/Compression**: Content bị nén, sub_filter không xử lý được
4. **CSP (Content Security Policy)**: Có thể block inline scripts

**Giải pháp**: Manual loading qua console **đơn giản và luôn hoạt động** ✅

---

**Ready to use!** 🚀 Access your secured Supabase Studio at http://localhost:54323

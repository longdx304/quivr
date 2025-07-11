FROM nginx:alpine

# Install Python, Flask and supervisord for running multiple services
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    supervisor \
    && python3 -m pip install --break-system-packages Flask==3.0.0 Werkzeug==3.0.1

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy Flask auth service and session widget
COPY auth_service.py /app/auth_service.py
COPY requirements.txt /app/requirements.txt
COPY session_widget.js /app/session_widget.js

# Create supervisord configuration
RUN echo '[supervisord]' > /etc/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisord.conf && \
    echo 'user=root' >> /etc/supervisord.conf && \
    echo '' >> /etc/supervisord.conf && \
    echo '[program:nginx]' >> /etc/supervisord.conf && \
    echo 'command=nginx -g "daemon off;"' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo '' >> /etc/supervisord.conf && \
    echo '[program:auth_service]' >> /etc/supervisord.conf && \
    echo 'command=python3 /app/auth_service.py' >> /etc/supervisord.conf && \
    echo 'directory=/app' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf

# Expose port 54323
EXPOSE 54323

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:54323/health || exit 1

# Start both nginx and auth service with supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"] 
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and Microsoft ODBC drivers
RUN apt-get update \
    && apt-get install -y \
        curl \
        apt-transport-https \
        gnupg \
        lsb-release \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y \
        msodbcsql18 \
        unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ETL source code
COPY . .

# Create directories for logs and reports
RUN mkdir -p etl_logs etl_reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port for potential web interface
EXPOSE 8080

# Default command - run scheduled ETL
CMD ["python", "etl_main.py", "--mode", "schedule"] 
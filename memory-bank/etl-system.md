# ETL System - Data Pipeline Architecture

## System Overview

The Quivr ETL (Extract, Transform, Load) pipeline provides enterprise-grade data synchronization from the operational Supabase PostgreSQL database to a SQL Server Data Warehouse for analytics and business intelligence.

### Architecture Flow
```
[Supabase PostgreSQL:54323] → [Python ETL Engine] → [SQL Server:1433/DataWarehouse]
            ↓                          ↓                       ↓
    Operational Data               Processing Layer         Analytics Data
    - users                        - Extractors             - Daily Activity
    - chats                        - Transformers           - User Summary
    - chat_history                 - Loaders                - Brain Usage
    - brains                       - Schedulers             - Performance Metrics
    - knowledge                    - Monitors               - Audit Trails
```

## File Structure

```
backend/etl/
├── config.py                    # Configuration management
├── database.py                  # Database connection classes
├── extractors.py               # Data extraction logic
├── etl_main.py                 # Main orchestrator
├── utils.py                    # Logging, notifications, health checks
├── requirements.txt            # Python dependencies
├── Dockerfile                  # ETL application container
├── docker-compose.etl.yml      # Complete stack deployment
├── env.template               # Environment configuration template
├── README.md                  # Comprehensive documentation
└── sql_scripts/
    └── create_warehouse_schema.sql  # Data warehouse schema
```

## Core Components

### 1. Configuration Management (`config.py`)

Uses Pydantic models for type-safe configuration with validation:

```python
class DatabaseConfig(BaseModel):
    supabase_url: str
    sqlserver_url: str
    connection_pool_size: int = 10
    
class ETLConfig(BaseModel):
    batch_size: int = 1000
    parallel_tables: int = 3
    incremental_interval_minutes: int = 60
    full_sync_time: str = "02:00"
    
class MonitoringConfig(BaseModel):
    email_to: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    health_check_port: int = 8001
```

**Key Features**:
- Environment variable validation at startup
- Type safety for all configuration parameters
- Optional monitoring configuration
- Secure handling of sensitive credentials

### 2. Database Connectivity (`database.py`)

Provides robust database connection management:

```python
class SupabaseConnection:
    def __init__(self, connection_url: str):
        self.engine = create_engine(
            connection_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
    
    def get_connection(self) -> Connection:
        return self.engine.connect()
    
    def execute_query(self, query: str) -> Result:
        with self.get_connection() as conn:
            return conn.execute(text(query))

class SQLServerConnection:
    # Similar implementation for SQL Server
```

**Features**:
- Connection pooling for performance
- Automatic connection health checks (`pool_pre_ping`)
- Error handling and retry logic
- Support for both read and write operations
- Transaction management

### 3. Data Extraction (`extractors.py`)

Implements different sync strategies based on table characteristics:

#### Incremental Sync Strategy
For high-frequency tables with timestamp columns:

```python
class IncrementalExtractor:
    def extract_incremental_data(self, table_name: str, timestamp_column: str) -> pd.DataFrame:
        last_sync = self.get_last_sync_timestamp(table_name)
        query = f"""
            SELECT * FROM {table_name} 
            WHERE {timestamp_column} > '{last_sync}'
            ORDER BY {timestamp_column}
        """
        return self.source_db.query_to_dataframe(query)
```

**Incremental Tables**:
- `chat_history` (by `message_time`)
- `chats` (by `creation_time`)
- `notifications` (by `datetime`)
- `user_daily_usage` (by `date`)

#### Full Sync Strategy
For reference tables that need complete refresh:

```python
class FullExtractor:
    def extract_full_data(self, table_name: str) -> pd.DataFrame:
        # Exclude sensitive columns
        safe_columns = self.get_safe_columns(table_name)
        query = f"SELECT {', '.join(safe_columns)} FROM {table_name}"
        return self.source_db.query_to_dataframe(query)
```

**Full Sync Tables**:
- `users`, `brains`, `knowledge`, `prompts`
- `api_keys` (metadata only), `user_settings`
- Relationship tables: `brains_users`, `brains_vectors`, `knowledge_vectors`

### 4. ETL Orchestrator (`etl_main.py`)

Main coordination engine with scheduling and parallel processing:

```python
class ETLOrchestrator:
    def __init__(self, config: ETLConfig):
        self.config = config
        self.extractor = TableExtractor(config)
        self.loader = DataLoader(config)
        self.monitor = ETLMonitor(config)
        
    def run_incremental_sync(self):
        """Run incremental sync for high-frequency tables"""
        with ThreadPoolExecutor(max_workers=self.config.parallel_tables) as executor:
            futures = []
            for table in self.config.incremental_tables:
                future = executor.submit(self.sync_table_incremental, table)
                futures.append(future)
            
            # Wait for all tables to complete
            for future in futures:
                result = future.result()
                self.monitor.record_sync_result(result)
    
    def run_full_sync(self):
        """Run full sync for reference tables"""
        # Similar implementation for full refresh
```

**Orchestration Features**:
- **Parallel Processing**: Multiple tables sync simultaneously
- **Scheduling**: Celery-based job scheduling
  - Incremental: Every 60 minutes
  - Full: Daily at 2 AM
- **Error Handling**: Continue with other tables if one fails
- **Progress Tracking**: Real-time status and metrics
- **Health Monitoring**: System status and performance tracking

### 5. Monitoring & Utilities (`utils.py`)

Comprehensive monitoring and notification system:

```python
class ETLMonitor:
    def __init__(self, config: MonitoringConfig):
        self.email_notifier = EmailNotifier(config) if config.email_to else None
        self.slack_notifier = SlackNotifier(config) if config.slack_webhook_url else None
        self.logger = self.setup_logging()
    
    def notify_completion(self, metrics: ETLMetrics):
        message = self.format_completion_message(metrics)
        
        if self.email_notifier:
            self.email_notifier.send_notification(message)
        
        if self.slack_notifier:
            self.slack_notifier.send_notification(message)
        
        self.logger.info("ETL completed", extra=metrics.to_dict())
    
    def notify_error(self, error: Exception, context: Dict):
        error_message = self.format_error_message(error, context)
        # Send alerts to all configured channels
```

**Monitoring Features**:
- **Structured Logging**: JSON format with correlation IDs
- **Email Notifications**: SMTP-based alerts for completion/errors
- **Slack Integration**: Real-time alerts to team channels
- **Health Checks**: HTTP endpoints for monitoring tools
- **Metrics Collection**: Processing times, row counts, error rates
- **Log Rotation**: Automatic log file management

## Data Warehouse Schema

### Table Design
The SQL Server schema mirrors the Supabase structure with optimizations for analytics:

```sql
-- Core user table
CREATE TABLE users (
    id UNIQUEIDENTIFIER PRIMARY KEY,
    email NVARCHAR(255) NOT NULL,
    created_at DATETIME2 NOT NULL,
    updated_at DATETIME2,
    -- Additional user fields
    INDEX IX_users_created_at (created_at),
    INDEX IX_users_email (email)
);

-- Chat history fact table (time-series data)
CREATE TABLE chat_history (
    message_id UNIQUEIDENTIFIER PRIMARY KEY,
    chat_id UNIQUEIDENTIFIER NOT NULL,
    user_message NTEXT,
    assistant NTEXT,
    message_time DATETIME2 NOT NULL,
    brain_id UNIQUEIDENTIFIER,
    -- Foreign key constraints
    INDEX IX_chat_history_time (message_time),
    INDEX IX_chat_history_chat_id (chat_id),
    INDEX IX_chat_history_brain_id (brain_id)
);
```

### Analytics Views
Pre-built views for common business intelligence scenarios:

```sql
-- Daily activity summary
CREATE VIEW daily_activity_summary AS
SELECT 
    CAST(message_time AS DATE) as activity_date,
    COUNT(*) as total_messages,
    COUNT(DISTINCT chat_id) as unique_chats,
    COUNT(DISTINCT user_id) as active_users,
    AVG(LEN(user_message)) as avg_message_length
FROM chat_history ch
JOIN chats c ON ch.chat_id = c.chat_id
GROUP BY CAST(message_time AS DATE);

-- Brain usage analytics
CREATE VIEW brain_usage_analytics AS
SELECT 
    b.name as brain_name,
    COUNT(ch.message_id) as total_interactions,
    COUNT(DISTINCT ch.chat_id) as unique_sessions,
    COUNT(DISTINCT c.user_id) as unique_users,
    MIN(ch.message_time) as first_use,
    MAX(ch.message_time) as last_use
FROM brains b
LEFT JOIN chat_history ch ON b.brain_id = ch.brain_id
LEFT JOIN chats c ON ch.chat_id = c.chat_id
GROUP BY b.brain_id, b.name;
```

## Deployment & Operations

### Docker Deployment

#### 1. Environment Setup
```bash
cd backend/etl
cp env.template .env
# Edit .env with your specific configuration
```

#### 2. Complete Stack Launch
```bash
docker-compose -f docker-compose.etl.yml up -d
```

This launches:
- **SQL Server 2022 Express**: Data warehouse database
- **ETL Application**: Python processing engine
- **Redis**: Task queue and caching
- **Networks**: Isolated internal communication

#### 3. Health Verification
```bash
# Check all services
docker-compose -f docker-compose.etl.yml ps

# Check ETL health
curl http://localhost:8001/health

# Check SQL Server connection
docker exec etl-sqlserver sqlcmd -S localhost -U sa -P YourPassword123 -Q "SELECT @@VERSION"
```

### Configuration Parameters

#### Database Connections
```bash
# Source database (Supabase)
SUPABASE_URL=postgresql://postgres:password@localhost:54323/postgres

# Target database (SQL Server)
SQLSERVER_URL=mssql+pyodbc://sa:YourPassword123@localhost:1433/DataWarehouse?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

#### Processing Settings
```bash
# Performance tuning
BATCH_SIZE=1000                    # Records per batch
PARALLEL_TABLES=3                  # Concurrent table processing
MAX_CONNECTIONS=10                 # Database connection pool size

# Scheduling
INCREMENTAL_INTERVAL_MINUTES=60    # Incremental sync frequency
FULL_SYNC_TIME=02:00              # Daily full sync time (24h format)
```

#### Monitoring Configuration
```bash
# Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=etl-system@yourcompany.com
EMAIL_TO=admin@yourcompany.com

# Slack integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
SLACK_CHANNEL=#data-pipeline

# Health monitoring
HEALTH_CHECK_PORT=8001
LOG_LEVEL=INFO
```

### Security Considerations

#### Data Protection
- **Sensitive Field Exclusion**: Automatic filtering of:
  - `api_key` fields
  - `embedding` vectors (large binary data)
  - Password hashes
  - Personal identification numbers

#### Access Control
```sql
-- Create dedicated ETL user with minimal permissions
CREATE LOGIN etl_user WITH PASSWORD = 'SecurePassword123!';
CREATE USER etl_user FOR LOGIN etl_user;

-- Grant only necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO etl_user;
GRANT CREATE TABLE ON DATABASE::DataWarehouse TO etl_user;
```

#### Network Security
- Docker internal networks for service communication
- Exposed ports only for necessary external access
- SSL/TLS encryption for database connections

### Operational Procedures

#### Daily Operations
1. **Morning Health Check**: Verify all services running
2. **Review Overnight Sync**: Check full sync completion
3. **Monitor Performance**: Review processing times and volumes
4. **Alert Review**: Address any notification alerts

#### Weekly Maintenance
1. **Log Rotation**: Archive and clean old log files
2. **Performance Review**: Analyze processing trends
3. **Disk Space**: Monitor SQL Server data and log growth
4. **Configuration Review**: Validate all settings

#### Monthly Reviews
1. **Capacity Planning**: Review growth trends and scaling needs
2. **Performance Optimization**: Tune batch sizes and parallelism
3. **Security Audit**: Review access logs and permissions
4. **Backup Validation**: Test data warehouse backup/restore

### Troubleshooting

#### Common Issues

1. **Connection Timeouts**
   ```bash
   # Check network connectivity
   docker exec etl-app ping sqlserver
   
   # Verify connection strings
   docker logs etl-app | grep "connection"
   ```

2. **Sync Failures**
   ```bash
   # Check ETL logs
   docker logs etl-app --tail 100
   
   # Verify source data availability
   docker exec etl-app python -c "from database import SupabaseConnection; conn = SupabaseConnection(); print(conn.test_connection())"
   ```

3. **Performance Issues**
   ```bash
   # Monitor resource usage
   docker stats etl-app etl-sqlserver
   
   # Check SQL Server performance
   docker exec etl-sqlserver sqlcmd -Q "SELECT * FROM sys.dm_exec_requests WHERE status = 'running'"
   ```

#### Log Analysis
```bash
# Follow real-time logs
docker logs etl-app -f

# Search for specific errors
docker logs etl-app 2>&1 | grep ERROR

# Export logs for analysis
docker logs etl-app > etl-analysis.log
```

This ETL system provides a robust, scalable foundation for enterprise data analytics while maintaining operational simplicity and comprehensive monitoring capabilities. 
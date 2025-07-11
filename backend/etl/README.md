# Quivr ETL Pipeline

A comprehensive ETL (Extract, Transform, Load) pipeline that synchronizes data from Supabase (PostgreSQL) to SQL Server Data Warehouse.

## 🏗️ Architecture Overview

```
[Supabase Local] → [ETL Pipeline] → [SQL Server DWH]
    (Port 54322)       (Python)         (Port 1433)
       ↓                   ↓                 ↓
   PostgreSQL        + Scheduling      + Analytics
   + Vector DB      + Error Handling   + Reporting
```

## 📋 Prerequisites

- Docker and Docker Compose
- Supabase local instance running on port 54322
- Python 3.11+ (for local development)
- 4GB+ RAM available for SQL Server

## 🚀 Quick Start

### 1. **Setup Environment**

```bash
# Navigate to ETL directory
cd backend/etl

# Copy environment template
cp env.template .env

# Edit .env with your configuration
nano .env
```

### 2. **Start SQL Server and ETL Pipeline**

```bash
# Start all services
docker compose -f docker-compose.etl.yml up -d

# Check service status
docker compose -f docker-compose.etl.yml ps

# View logs
docker compose -f docker-compose.etl.yml logs -f etl-app
```

### 3. **Verify Setup**

```bash
# Check SQL Server connection
docker exec -it etl-sqlserver-1 /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U sa -P 'YourPassword123!' \
  -Q "SELECT name FROM sys.databases"

# Check ETL application logs
docker compose -f docker-compose.etl.yml logs etl-app
```

## 🔧 Detailed Configuration

### Database Configuration

#### Supabase (Source)

```bash
SUPABASE_HOST=localhost
SUPABASE_PORT=54322  # Your Supabase local port
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
```

#### SQL Server (Target)

```bash
SQLSERVER_HOST=localhost
SQLSERVER_PORT=1433
SQLSERVER_DATABASE=DataWarehouse
SQLSERVER_USER=sa
SQLSERVER_PASSWORD=YourPassword123!
```

### ETL Configuration

#### Sync Tables

The pipeline synchronizes these tables by default:

- `users` - User accounts
- `brains` - AI brain configurations
- `knowledge` - Knowledge base files
- `user_settings` - User preferences
- `brains_users` - Brain access permissions
- `user_daily_usage` - Usage statistics

#### Incremental Sync

These tables support incremental synchronization:

- `user_daily_usage` - Based on `date`
- `knowledge` - Based on `id`

## 📊 Data Warehouse Schema

The SQL Server data warehouse uses the following schema:

```
DataWarehouse/
├── dwh/          # Main data tables
│   ├── users
│   ├── brains
│   ├── vectors
│   ├── knowledge
│   └── ...
├── etl/          # ETL control tables
│   ├── etl_control
│   └── etl_execution_log
└── views/        # Analytical views
    ├── v_daily_chat_activity
    ├── v_brain_usage_summary
    └── v_user_activity_summary
```

## 🕰️ Scheduling

The ETL pipeline runs on the following schedule:

- **Incremental Sync**: Every 60 minutes (configurable)
- **Full Sync**: Daily at 2:00 AM
- **Health Checks**: Every 30 seconds

### Manual Execution

```bash
# Run full sync for all tables
docker exec -it etl-etl-app-1 python etl_main.py --mode full

# Run incremental sync
docker exec -it etl-etl-app-1 python etl_main.py --mode incremental

# Run sync for specific tables
docker exec -it etl-etl-app-1 python etl_main.py --mode full --tables users brains chats
```

## 📈 Monitoring & Logging

### Log Files

```bash
# View ETL logs
docker exec -it etl-etl-app-1 tail -f etl_logs/etl_$(date +%Y-%m-%d).log

# View execution reports
docker exec -it etl-etl-app-1 ls -la etl_reports/
```

### Database Monitoring

```sql
-- Check ETL execution history
SELECT TOP 10 *
FROM etl.etl_execution_log
ORDER BY start_time DESC;

-- Check sync control status
SELECT * FROM etl.etl_control;

-- View daily chat activity
SELECT * FROM dwh.v_daily_chat_activity
ORDER BY date DESC;
```

### Health Checks

```bash
# Check application health
docker exec -it etl-etl-app-1 python -c "
from utils import get_database_health
import json
print(json.dumps(get_database_health(), indent=2))
"
```

## 🔔 Notifications

### Email Notifications

Configure email notifications by setting these environment variables:

```bash
ETL_SMTP_SERVER=smtp.gmail.com
ETL_SMTP_PORT=587
ETL_SMTP_USERNAME=your-email@gmail.com
ETL_SMTP_PASSWORD=your-app-password
ETL_FROM_EMAIL=your-email@gmail.com
ETL_TO_EMAILS=admin1@company.com,admin2@company.com
```

### Slack Notifications

Configure Slack notifications:

```bash
ETL_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. SQL Server Connection Failed

```bash
# Check if SQL Server is running
docker compose -f docker-compose.etl.yml ps sqlserver

# Test connection manually
docker exec -it etl-sqlserver-1 /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U sa -P 'YourPassword123!' -Q "SELECT 1"
```

#### 2. Supabase Connection Failed

```bash
# Check if Supabase is accessible from container
docker exec -it etl-etl-app-1 python -c "
import psycopg2
conn = psycopg2.connect(
    host='host.docker.internal',
    port=54322,
    database='postgres',
    user='postgres',
    password='postgres'
)
print('Supabase connection successful')
"
```

#### 3. ETL Application Not Starting

```bash
# Check application logs
docker compose -f docker-compose.etl.yml logs etl-app

# Check configuration
docker exec -it etl-etl-app-1 python -c "
from config import db_config, etl_config
print('DB Config loaded successfully')
print('ETL Config loaded successfully')
"
```

### Performance Tuning

#### Optimize Batch Size

```bash
# For large datasets, increase batch size
BATCH_SIZE=5000

# For limited memory, decrease batch size
BATCH_SIZE=500
```

#### Parallel Processing

```bash
# Increase parallel workers for faster sync
PARALLEL_WORKERS=8

# Increase connection pool for high concurrency
CONNECTION_POOL_SIZE=20
```

## 📁 File Structure

```
backend/etl/
├── config.py              # Configuration management
├── database.py             # Database connections
├── extractors.py           # Data extractors
├── etl_main.py             # Main ETL orchestrator
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── Dockerfile              # ETL app container
├── docker-compose.etl.yml  # Complete stack
├── env.template            # Environment template
├── sql_scripts/
│   └── create_warehouse_schema.sql
└── README.md               # This file
```

## 🔄 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv etl-env
source etl-env/bin/activate  # Linux/Mac
# or
etl-env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.template .env
# Edit .env with your local settings

# Run ETL locally
python etl_main.py --mode incremental --log-level DEBUG
```

### Testing

```bash
# Test configuration
python -c "from utils import validate_configuration; print(validate_configuration())"

# Test database connections
python -c "from utils import get_database_health; print(get_database_health())"

# Test single table sync
python etl_main.py --mode full --tables users --log-level DEBUG
```

## 📊 Analytics Queries

### Daily Activity Report

## 🔒 Security Considerations

1. **Sensitive Data**: API keys are automatically excluded from sync
2. **Embeddings**: Vector embeddings are excluded to reduce storage
3. **Passwords**: Use strong passwords for SQL Server
4. **Network**: Use VPN or private networks for production
5. **Encryption**: Consider encrypting data at rest and in transit

## 📞 Support

For issues or questions:

1. Check the logs: `docker compose -f docker-compose.etl.yml logs etl-app`
2. Verify configuration: Review your `.env` file
3. Test connections: Use the health check utilities
4. Check SQL Server: Verify SQL Server is accessible

## 🚀 Production Deployment

### Production Checklist

- [ ] Configure proper passwords
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy for SQL Server
- [ ] Set up log rotation
- [ ] Configure SSL/TLS for database connections
- [ ] Set up network security
- [ ] Test disaster recovery procedures

### Scaling Considerations

- Use SQL Server Standard/Enterprise for production
- Consider partitioning large tables
- Implement proper indexing strategy
- Monitor resource usage
- Set up read replicas for analytics

---

**Note**: This ETL pipeline is designed for the Quivr application architecture. Modify table configurations and transformations based on your specific requirements.

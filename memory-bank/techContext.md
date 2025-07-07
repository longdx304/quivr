# Technical Context - Quivr System Architecture

## Core Technology Stack

### RAG Processing System
- **Backend Framework**: FastAPI (Python 3.11+)
- **Document Processing**: LangChain + Megaparse for PDF processing
- **Vector Storage**: Supabase PostgreSQL with pgvector extension
- **Embeddings**: OpenAI text-embedding-3-large
- **Chunking**: Semantic splitting with embedding-based boundary detection
- **RAG Implementation**: LangGraph for conversation management

### ETL Data Pipeline
- **Source Database**: Supabase PostgreSQL (localhost:54323)
- **Target Database**: SQL Server 2022 Express (localhost:1433)
- **ETL Engine**: Python with SQLAlchemy, pandas, psycopg2, pyodbc
- **Orchestration**: Celery with Redis for task scheduling
- **Containerization**: Docker Compose with multi-service architecture
- **Monitoring**: Custom logging with email/Slack notifications

### Development Environment
- **OS**: macOS (darwin 24.2.0)
- **Shell**: Zsh
- **Workspace**: `/Users/namnguyen/Workspace/Dev/DOB/quivr`
- **Ports**: 
  - Frontend: 3000
  - Backend API: 5050
  - Supabase: 54323 (user specified)
  - SQL Server: 1433
  - ETL Health: 8001

## System Dependencies

### Core RAG Dependencies
```toml
# backend/core/pyproject.toml
dependencies = [
    "langchain-openai>=0.1.23",
    "scikit-learn>=1.3.0", 
    "numpy>=1.24.0",
    "megaparse",
    "pydantic",
    "fastapi",
    "uvicorn"
]
```

### ETL Pipeline Dependencies
```txt
# backend/etl/requirements.txt
sqlalchemy>=2.0.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
pyodbc>=4.0.39
celery[redis]>=5.3.0
pydantic>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0
```

### Docker Infrastructure

#### ETL Stack (`backend/etl/docker-compose.etl.yml`)
- **SQL Server 2022 Express**: Database container with persistence
- **ETL Application**: Python container with ODBC drivers
- **Redis**: Task queue and caching
- **Networking**: Isolated internal network for security

#### Main Application (`docker-compose.yml`)
- **Frontend**: Next.js application
- **Backend API**: FastAPI with Quivr core
- **Supabase**: PostgreSQL with extensions
- **Redis**: Caching and sessions

## Configuration Management

### Environment Variables

#### Core Application
```bash
# Database connections
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54323
NEXT_PUBLIC_BACKEND_URL=http://localhost:5050
NEXT_PUBLIC_FRONTEND_URL=http://localhost:3000

# Authentication
AUTHENTICATE=false
NEXT_PUBLIC_ENV=local

# RAG Enhancement
OPENAI_API_KEY=your_openai_api_key
```

#### ETL Pipeline
```bash
# Source and target databases
SUPABASE_URL=postgresql://postgres:password@localhost:54323/postgres
SQLSERVER_URL=mssql+pyodbc://sa:YourPassword123@localhost:1433/DataWarehouse

# Processing configuration
BATCH_SIZE=1000
PARALLEL_TABLES=3
INCREMENTAL_INTERVAL_MINUTES=60
FULL_SYNC_TIME=02:00

# Monitoring and alerts
EMAIL_TO=admin@yourcompany.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
```

## Architecture Patterns

### Semantic Chunking Architecture
```
Document Input → Megaparse Processor → Semantic Splitter
     ↓                 ↓                    ↓
  PDF/Text         Text Extraction      Embedding Analysis
     ↓                 ↓                    ↓
  Metadata         Chunk Generation      Boundary Detection
     ↓                 ↓                    ↓
Vector Storage ← Enhanced Chunks ← Semantic Boundaries
```

### ETL Processing Flow
```
Source Tables → Extractors → Transformers → Loaders → Target Tables
     ↓             ↓            ↓           ↓           ↓
 PostgreSQL   Batch Read   Data Clean   Bulk Insert  SQL Server
     ↓             ↓            ↓           ↓           ↓
 Incremental   Parallel     Validation   Error Handle Analytics
```

### Data Flow Integration
```
User Documents → RAG Processing → Vector Storage
                      ↓
                Chat Interactions
                      ↓
              Operational Database (Supabase)
                      ↓
                 ETL Pipeline
                      ↓
              Data Warehouse (SQL Server)
                      ↓
            Business Intelligence & Analytics
```

## Database Schemas

### Supabase PostgreSQL (Source)
- **Core Tables**: users, brains, chats, chat_history, knowledge
- **Vector Tables**: vectors, brains_vectors, knowledge_vectors
- **System Tables**: api_keys, user_settings, notifications, prompts
- **Analytics**: user_daily_usage
- **Extensions**: pgvector for embeddings, uuid-ossp

### SQL Server Data Warehouse (Target)
- **Fact Tables**: chat_history (time-series data)
- **Dimension Tables**: users, brains, knowledge
- **Reference Tables**: prompts, user_settings
- **Analytics Views**: 
  - daily_activity_summary
  - brain_usage_analytics
  - user_summary_stats
  - chat_performance_metrics

## Security Architecture

### Data Protection
- **Sensitive Field Exclusion**: API keys, embeddings, passwords
- **Access Control**: Database-level permissions
- **Network Isolation**: Docker internal networks
- **Audit Logging**: Complete data lineage tracking

### Authentication Flow
- **Development**: Bypassed (`AUTHENTICATE=false`)
- **Production**: Supabase Auth with multiple providers
- **API Security**: JWT tokens and rate limiting
- **Database**: Connection pooling with secure credentials

## Performance Considerations

### RAG System Optimization
- **Embedding Caching**: Batch processing of 50 texts
- **Vector Search**: pgvector with HNSW indexes
- **Chunk Size**: 600 characters optimized for context
- **Fallback Strategy**: Recursive chunking if embeddings fail

### ETL Performance
- **Parallel Processing**: 3 tables simultaneously
- **Batch Sizes**: 1000 records per batch
- **Connection Pooling**: Optimized database connections
- **Incremental Updates**: Timestamp-based change detection

### Resource Usage
- **Memory**: 2-4GB for ETL, 1-2GB for RAG
- **CPU**: 2-4 cores recommended
- **Storage**: 50GB+ for data warehouse
- **Network**: Local deployment, minimal bandwidth

## Monitoring & Observability

### Application Monitoring
- **Health Endpoints**: `/health` for all services
- **Structured Logging**: JSON format with rotation
- **Metrics Collection**: Processing times, error rates
- **Alerting**: Email and Slack notifications

### ETL Pipeline Monitoring
- **Execution Reports**: Detailed sync statistics
- **Data Quality**: Row count validation
- **Performance Metrics**: Throughput and latency
- **Error Handling**: Retry logic with exponential backoff

### Development Tools
- **Logging**: Real-time via `docker logs -f`
- **Health Checks**: HTTP endpoints for status
- **Database Access**: SSMS for SQL Server, pgAdmin for PostgreSQL
- **Debugging**: Structured logs with correlation IDs

## Deployment Architecture

### Local Development
- **Docker Compose**: Multi-service orchestration
- **Hot Reload**: Code changes reflected immediately
- **Port Mapping**: Services accessible on localhost
- **Volume Mounts**: Persistent data and logs

### Production Considerations
- **Container Registry**: For image deployment
- **Load Balancing**: Multiple container instances
- **Database Scaling**: Read replicas and connection pooling
- **Monitoring**: External monitoring services integration
- **Backup Strategy**: Automated database backups

## Integration Points

### Internal System Integration
- **RAG ↔ Database**: Vector storage and retrieval
- **ETL ↔ RAG Database**: Source data extraction
- **Frontend ↔ Backend**: REST API communication
- **Monitoring ↔ All Services**: Health and metrics collection

### External System Integration
- **OpenAI API**: Embeddings and language models
- **Email Services**: SMTP for notifications
- **Slack**: Webhook integration for alerts
- **File Storage**: Document upload and processing

This technical context provides the foundation for understanding how all components work together to deliver both enhanced RAG capabilities and comprehensive data analytics for the Quivr system. 
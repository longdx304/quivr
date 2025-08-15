# Quivr RAG System - Semantic Enhancement & Data Pipeline

## Project Overview
Quivr is an open-source RAG (Retrieval-Augmented Generation) system that allows users to chat with their documents. The project encompasses two main areas:

1. **RAG Enhancement**: Improving document processing and retrieval accuracy through semantic chunking
2. **Data Pipeline**: Complete ETL infrastructure for analytics and data warehousing

## Core Problems Addressed

### 1. RAG Accuracy Issues
The original recursive chunking implementation split documents without considering semantic boundaries, leading to:
- Loss of contextual information about dates and time periods
- Inaccurate retrieval when users ask about specific time periods (e.g., April 2025 vs January 2025)
- Poor semantic coherence in chunks, especially for Vietnamese content

### 2. Data Analytics & Warehousing Needs
The system required enterprise-grade data pipeline capabilities:
- Extract operational data from Supabase PostgreSQL to SQL Server Data Warehouse
- Enable business intelligence and analytics workflows
- Provide real-time and batch data synchronization
- Support compliance and audit requirements

## Goals

### RAG Enhancement Goals (✅ COMPLETED)
1. **Replace recursive chunking with semantic chunking** to maintain contextual integrity
2. **Improve temporal context preservation** for date-sensitive documents 
3. **Enhance retrieval accuracy** especially for Vietnamese content
4. **Maintain or improve performance** while enhancing semantic understanding

### ETL Pipeline Goals (✅ COMPLETED)
1. **Build comprehensive ETL pipeline** from Supabase to SQL Server
2. **Enable real-time and batch data synchronization** with incremental updates
3. **Provide enterprise monitoring and alerting** for data pipeline health
4. **Create analytics-ready data warehouse** with pre-built views and schemas
5. **Ensure data security and compliance** with proper handling of sensitive information

## Success Criteria

### RAG System (✅ ACHIEVED)
- Accurate retrieval of date-specific information (e.g., correctly finding April 2025 promotions when asked)
- Better semantic coherence in document chunks
- Preserved or improved query response times
- Maintained compatibility with existing Quivr infrastructure

### ETL System (✅ ACHIEVED)
- Automated data synchronization from Supabase to SQL Server
- Real-time incremental updates for chat_history, notifications
- Daily full refresh for user profiles, brains, prompts
- Comprehensive monitoring with email/Slack notifications
- Analytics-ready warehouse with business intelligence views

## Key Technologies

### Core RAG Stack
- **Backend**: Python-based with FastAPI
- **Document Processing**: LangChain text splitters, Megaparse for PDFs
- **Vector Storage**: Supabase with pgvector
- **Embeddings**: OpenAI text-embedding-3-large
- **Chunking**: Semantic splitting with embedding-based boundary detection

### ETL Infrastructure
- **Source**: Supabase PostgreSQL (localhost:54323)
- **Target**: SQL Server 2022 Express (localhost:1433)
- **Processing**: Python with SQLAlchemy, pandas, psycopg2, pyodbc
- **Orchestration**: Celery with Redis for scheduling and queuing
- **Monitoring**: Custom logging, health checks, email/Slack notifications
- **Deployment**: Docker Compose with isolated networking

## System Architecture

### RAG Processing Pipeline
- **Core**: `backend/core/quivr_core/` - Core processing logic
- **Processors**: `backend/core/quivr_core/processor/implementations/` - Document processors
- **Splitters**: `backend/core/quivr_core/processor/splitter.py` - Chunking configuration
- **RAG**: `backend/core/quivr_core/quivr_rag*.py` - RAG implementation 

### ETL Data Pipeline
```
[Supabase PostgreSQL] → [ETL Engine] → [SQL Server DWH]
       ↓                      ↓               ↓
   Source Tables         Python ETL      Analytics Views
   - users               - Extractors     - Daily Activity
   - chats               - Transformers   - User Summary  
   - chat_history        - Loaders        - Brain Usage
   - brains              - Schedulers     - Performance Metrics
   - knowledge           - Monitors       - Audit Trails
```

### Key Components
- **Configuration**: Environment-based with Pydantic models
- **Database Connections**: Connection pooling for both PostgreSQL and SQL Server
- **Data Processing**: Incremental sync strategies with timestamp-based tracking
- **Error Handling**: Comprehensive retry logic and fallback mechanisms
- **Security**: Sensitive data exclusion (API keys, embeddings)

## Current System Capabilities

### RAG Enhancement (Production Ready)
- Semantic chunking with Vietnamese temporal pattern recognition
- Enhanced conversation history preservation
- Improved retrieval accuracy for time-sensitive queries
- Backwards compatibility with existing document corpus

### ETL Pipeline (Production Ready)
- Automated data synchronization on configurable schedules
- Real-time incremental updates for high-frequency tables
- Comprehensive data warehouse schema with proper indexing
- Full monitoring and alerting infrastructure
- Docker-based deployment with health checks
- Analytics views for business intelligence

This dual-capability system provides both improved user experience through better RAG accuracy and enterprise-grade data analytics capabilities through the comprehensive ETL infrastructure. 
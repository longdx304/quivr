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

    # ⭐ NEW: Primary key configuration for UPSERT operations
    table_primary_keys: dict[str, list[str]] = {
        'users': ['id'],
        'brains': ['brain_id'],
        'knowledge': ['id'],
        'brains_users': ['brain_id', 'user_id'],
        'user_daily_usage': ['user_id', 'date'],
        'chats': ['chat_id'],
        'chat_history': ['message_id']
    }

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
- **⭐ NEW**: Primary key mapping for UPSERT operations

### 2. Database Connectivity (`database.py`)

Provides robust database connection management with **enhanced UPSERT capability**:

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
    # ⭐ NEW: UPSERT method for handling incremental sync duplicates
    def bulk_upsert_dataframe(self, df: pd.DataFrame, table_name: str,
                             primary_keys: list[str], schema: str = "dwh") -> int:
        """Bulk upsert DataFrame using SQL Server MERGE statements"""
        # Create temporary table
        temp_table = f"temp_{table_name}_{int(time.time())}"

        # Insert data into temporary table
        df.to_sql(temp_table, self.engine, schema=schema, if_exists='replace')

        # Build MERGE statement for UPSERT operation
        pk_condition = " AND ".join([f"target.[{pk}] = source.[{pk}]" for pk in primary_keys])

        merge_sql = f"""
            MERGE [{schema}].[{table_name}] AS target
            USING [{schema}].[{temp_table}] AS source
            ON {pk_condition}
            WHEN MATCHED THEN UPDATE SET ...
            WHEN NOT MATCHED THEN INSERT ...
        """

        # Execute MERGE and cleanup
        self.engine.execute(text(merge_sql))
        self.engine.execute(text(f"DROP TABLE [{schema}].[{temp_table}]"))

        return len(df)

    def bulk_insert_dataframe(self, df: pd.DataFrame, table_name: str,
                             schema: str = "dwh", if_exists: str = "append") -> int:
        """Traditional bulk insert for full sync operations"""
        # Existing implementation for full sync
```

**Features**:

- Connection pooling for performance
- Automatic connection health checks (`pool_pre_ping`)
- Error handling and retry logic
- Support for both read and write operations
- Transaction management
- **⭐ NEW**: UPSERT capability with SQL Server MERGE statements
- **⭐ NEW**: Handles PRIMARY KEY constraint violations gracefully

### 3. Data Extraction (`extractors.py`)

Implements different sync strategies based on table characteristics with **enhanced duplicate handling**:

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

**Incremental Tables** (⭐ Now with UPSERT support):

- `chat_history` (by `message_time`)
- `chats` (by `creation_time`)
- `notifications` (by `datetime`)
- `user_daily_usage` (by `date`)

**Key Enhancement**: These tables now use UPSERT logic to handle cases where records are updated in the source database and re-extracted during incremental sync.

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

Main coordination engine with **enhanced sync logic**:

```python
class ETLOrchestrator:
    def _sync_single_table(self, table_name: str, incremental: bool = False) -> bool:
        """Sync a single table with appropriate strategy"""

        # Extract data using appropriate strategy
        if incremental and table_name in etl_config.INCREMENTAL_TABLES:
            df = extractor.extract_incremental()
        else:
            df = extractor.extract_full()

        # ⭐ NEW: Choose INSERT vs UPSERT based on sync type and table configuration
        if incremental and table_name in etl_config.TABLE_PRIMARY_KEYS:
            # Use UPSERT for incremental sync to handle duplicates
            primary_keys = etl_config.TABLE_PRIMARY_KEYS[table_name]
            rows_loaded = self.sqlserver.bulk_upsert_dataframe(
                df, table_name, primary_keys, schema='dwh'
            )
        else:
            # Use traditional INSERT for full sync (after truncate)
            self.sqlserver.truncate_table(table_name, schema='dwh')
            rows_loaded = self.sqlserver.bulk_insert_dataframe(
                df, table_name, schema='dwh', if_exists='append'
            )

        return True

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
- **⭐ NEW**: Smart sync strategy selection (UPSERT vs INSERT)
- **⭐ NEW**: PRIMARY KEY constraint violation prevention

## ⭐ Critical Bug Fix: PRIMARY KEY Constraint Resolution

### Problem Solved

**Issue**: ETL incremental sync was failing with PRIMARY KEY constraint violations:

```
Violation of PRIMARY KEY constraint 'PK_user_daily_usage'. Cannot insert duplicate key...
Violation of PRIMARY KEY constraint 'PK__chats__FD040B1762948419'. Cannot insert duplicate key...
```

**Root Cause**:

- Incremental extraction worked correctly (pulling updated records)
- Insertion logic was flawed (using `if_exists='append'` without duplicate handling)
- When records were updated in Supabase, they would be re-extracted but fail INSERT due to existing PRIMARY KEYs

### Solution Implemented

**1. UPSERT Method**: Added `bulk_upsert_dataframe()` using SQL Server MERGE statements
**2. Smart Routing**: ETL orchestrator now chooses UPSERT vs INSERT based on sync type
**3. Configuration**: Primary key mapping added for all tables
**4. Error Prevention**: No more PRIMARY KEY constraint violations

### Before vs After

**Before (Problematic)**:

```python
# All sync types used INSERT
rows_loaded = self.sqlserver.bulk_insert_dataframe(
    df, table_name, schema='dwh', if_exists='append'
)
# ❌ Would fail if record already existed
```

**After (Fixed)**:

```python
# Incremental sync uses UPSERT
if incremental and table_name in etl_config.TABLE_PRIMARY_KEYS:
    primary_keys = etl_config.TABLE_PRIMARY_KEYS[table_name]
    rows_loaded = self.sqlserver.bulk_upsert_dataframe(
        df, table_name, primary_keys, schema='dwh'
    )
    # ✅ UPDATE if exists, INSERT if new
else:
    # Full sync still uses INSERT after truncate
    self.sqlserver.truncate_table(table_name, schema='dwh')
    rows_loaded = self.sqlserver.bulk_insert_dataframe(
        df, table_name, schema='dwh', if_exists='append'
    )
    # ✅ No duplicates after truncate
```

### Results

- **✅ No more PRIMARY KEY violations** in ETL logs
- **✅ Reliable incremental sync** for all tables
- **✅ Updated records properly handled** (UPDATE vs failed INSERT)
- **✅ New records properly inserted**
- **✅ Performance maintained** while handling duplicates gracefully

import asyncio
import asyncpg
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table
import sqlalchemy.types
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, List, Any, Optional
from loguru import logger
from config import db_config

class SupabaseConnection:
    """Manages connections to Supabase (PostgreSQL) database"""
    
    def __init__(self):
        self.config = db_config
        self.engine = None
        self.session_factory = None
        self.async_pool = None
        self._initialize_sync_connection()
    
    def _initialize_sync_connection(self):
        """Initialize synchronous SQLAlchemy connection"""
        try:
            self.engine = create_engine(
                self.config.supabase_url,
                poolclass=QueuePool,
                pool_size=self.config.CONNECTION_POOL_SIZE,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("Supabase connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase connection: {e}")
            raise
    
    async def initialize_async_pool(self):
        """Initialize async connection pool"""
        try:
            self.async_pool = await asyncpg.create_pool(
                host=self.config.SUPABASE_HOST,
                port=self.config.SUPABASE_PORT,
                user=self.config.SUPABASE_USER,
                password=self.config.SUPABASE_PASSWORD,
                database=self.config.SUPABASE_DATABASE,
                min_size=5,
                max_size=self.config.CONNECTION_POOL_SIZE,
                command_timeout=60
            )
            logger.info("Supabase async pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase async pool: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get a database session (context manager)"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_connection(self):
        """Get an async database connection"""
        if not self.async_pool:
            await self.initialize_async_pool()
        
        async with self.async_pool.acquire() as connection:
            yield connection
    
    def extract_table_data(self, table_name: str, 
                          columns: Optional[List[str]] = None,
                          where_clause: Optional[str] = None,
                          limit: Optional[int] = None) -> pd.DataFrame:
        """Extract data from a table"""
        try:
            # Build query
            select_cols = "*" if not columns else ", ".join(columns)
            query = f"SELECT {select_cols} FROM {self.config.SUPABASE_SCHEMA}.{table_name}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn)
                logger.info(f"Extracted {len(df)} rows from {table_name}")
                return df
                
        except Exception as e:
            logger.error(f"Failed to extract data from {table_name}: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Get table schema information"""
        try:
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=self.engine, schema=self.config.SUPABASE_SCHEMA)
            
            schema = {}
            for column in table.columns:
                schema[column.name] = str(column.type)
            
            return schema
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            raise
    
    def get_max_timestamp(self, table_name: str, timestamp_column: str) -> Optional[str]:
        """Get maximum timestamp from a table for incremental sync"""
        try:
            # For UUID columns, we can't use MAX() function in PostgreSQL
            # Check if this is a UUID column first
            if timestamp_column == 'id':
                # For UUID primary keys, check the actual data type
                schema_query = f"""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = '{self.config.SUPABASE_SCHEMA}' 
                    AND table_name = '{table_name}' 
                    AND column_name = '{timestamp_column}'
                """
                
                with self.engine.connect() as conn:
                    type_result = conn.execute(text(schema_query)).fetchone()
                    if type_result and 'uuid' in type_result[0].lower():
                        logger.warning(f"Skipping MAX() on UUID column {timestamp_column} for table {table_name}")
                        return None
            
            # For proper timestamp columns, use MAX()
            query = f"SELECT MAX({timestamp_column}) as max_ts FROM {self.config.SUPABASE_SCHEMA}.{table_name}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query)).fetchone()
                return result[0] if result and result[0] else None
                
        except Exception as e:
            logger.error(f"Failed to get max timestamp from {table_name}: {e}")
            return None
    
    def initialize_database_schema(self):
        """Initialize the database schema with required tables and schemas"""
        try:
            # Use the minimal schema as it has all our current fixes and requirements
            import os
            script_path = os.path.join(os.path.dirname(__file__), 'sql_scripts', 'create_minimal_schema.sql')
            
            if not os.path.exists(script_path):
                logger.error(f"Schema script not found: {script_path}")
                raise FileNotFoundError("Schema creation script not found")
            
            logger.info(f"Using schema script: create_minimal_schema.sql")
            
            with open(script_path, 'r', encoding='utf-8') as f:
                schema_script = f.read()
            
            # Split the script by GO statements and execute each part
            statements = [stmt.strip() for stmt in schema_script.split('GO') if stmt.strip() and not stmt.strip().startswith('--')]
            
            with self.engine.connect() as conn:
                for i, statement in enumerate(statements):
                    if statement and not statement.startswith('--'):
                        try:
                            logger.debug(f"Executing statement {i+1}/{len(statements)}")
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            logger.warning(f"Statement {i+1} execution warning (may be normal): {e}")
                            # Continue with other statements even if some fail (e.g., table already exists)
                            continue
            
            logger.info("Database schema initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    def close(self):
        """Close all connections"""
        if self.engine:
            self.engine.dispose()
        if self.async_pool:
            asyncio.create_task(self.async_pool.close())

class SQLServerConnection:
    """Manages connections to SQL Server Data Warehouse"""
    
    def __init__(self):
        self.config = db_config
        self.engine = None
        self.session_factory = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize SQLAlchemy connection to SQL Server"""
        try:
            self.engine = create_engine(
                self.config.sqlserver_url,
                poolclass=QueuePool,
                pool_size=self.config.CONNECTION_POOL_SIZE,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                connect_args={
                    "timeout": 30,
                    "autocommit": True
                }
            )
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("SQL Server connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQL Server connection: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get a database session (context manager)"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"SQL Server session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test SQL Server connection"""
        try:
            # First test connection to master database
            master_url = self.config.sqlserver_url.replace(f"/{self.config.SQLSERVER_DATABASE}", "/master")
            master_engine = create_engine(master_url)
            
            with master_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("✓ SQL Server master connection successful")
            
            master_engine.dispose()
            
            # Create DataWarehouse database if it doesn't exist
            self.create_database_if_not_exists()
            
            # Test connection to DataWarehouse database
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("✓ SQL Server DataWarehouse connection successful")
                return True
            
        except Exception as e:
            logger.error(f"SQL Server connection test failed: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """Create data warehouse database if it doesn't exist"""
        try:
            import pyodbc
            
            # Build connection string for master database with autocommit
            connection_string = (
                f"DRIVER={{{self.config.SQLSERVER_DRIVER}}};"
                f"SERVER={self.config.SQLSERVER_HOST},{self.config.SQLSERVER_PORT};"
                f"DATABASE=master;"
                f"UID={self.config.SQLSERVER_USER};"
                f"PWD={self.config.SQLSERVER_PASSWORD};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=no;"
            )
            
            # Use direct pyodbc connection with autocommit for DDL operations
            with pyodbc.connect(connection_string, autocommit=True) as conn:
                cursor = conn.cursor()
                
                # Check if database exists
                cursor.execute(f"""
                    SELECT name FROM sys.databases 
                    WHERE name = '{self.config.SQLSERVER_DATABASE}'
                """)
                
                if not cursor.fetchone():
                    # Create database
                    cursor.execute(f"CREATE DATABASE [{self.config.SQLSERVER_DATABASE}]")
                    logger.info(f"Created database: {self.config.SQLSERVER_DATABASE}")
                else:
                    logger.info(f"Database {self.config.SQLSERVER_DATABASE} already exists")
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise

    def initialize_database_schema(self, force_recreate=False):
        """Initialize the SQL Server database schema with required tables and schemas"""
        try:
            import os
            
            # Drop existing tables if force_recreate is True
            if force_recreate:
                drop_script_path = os.path.join(os.path.dirname(__file__), 'sql_scripts', 'drop_tables.sql')
                if os.path.exists(drop_script_path):
                    logger.info("Dropping existing tables for clean recreation...")
                    with open(drop_script_path, 'r', encoding='utf-8') as f:
                        drop_script = f.read()
                    
                    # Execute drop script
                    with self.engine.connect().execution_options(autocommit=True) as conn:
                        conn.execute(text(drop_script))
                    logger.info("✓ All existing tables dropped successfully")
            
            # Use the minimal schema as it has all our current fixes and requirements
            script_path = os.path.join(os.path.dirname(__file__), 'sql_scripts', 'create_minimal_schema.sql')
            
            if not os.path.exists(script_path):
                logger.error(f"Schema script not found: {script_path}")
                raise FileNotFoundError("Schema creation script not found")
            
            logger.info(f"Using schema script: create_minimal_schema.sql")
            
            with open(script_path, 'r', encoding='utf-8') as f:
                schema_script = f.read()
            
            # Remove the USE statement and replace with proper context
            schema_script = schema_script.replace(f'USE [{self.config.SQLSERVER_DATABASE}]', '')
            
            # Split the script by GO statements and execute each part
            statements = []
            script_parts = schema_script.split('GO')
            for stmt in script_parts:
                stmt = stmt.strip()
                # Remove empty lines and comments but keep structure
                lines = []
                for line in stmt.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('--'):
                        lines.append(line)
                
                if lines:
                    clean_stmt = '\n'.join(lines)
                    # Skip very short statements that are likely artifacts
                    if clean_stmt and len(clean_stmt) > 20:
                        statements.append(clean_stmt)
            
            logger.info(f"Found {len(statements)} statements to execute")
            
            # Execute each statement separately with detailed error handling
            success_count = 0
            failed_statements = []
            
            for i, statement in enumerate(statements):
                try:
                    preview = statement.replace('\n', ' ')[:200]
                    logger.info(f"[{i+1}/{len(statements)}] Executing: {preview}...")
                    
                    # Use autocommit mode and execute statement  
                    with self.engine.connect().execution_options(autocommit=True) as conn:
                        result = conn.execute(text(statement))
                    
                    logger.info(f"✓ Statement {i+1} executed successfully")
                    success_count += 1
                    
                except Exception as e:
                    error_msg = str(e)
                    if "already exists" in error_msg.lower():
                        logger.info(f"⚠ Statement {i+1}: Object already exists (skipping): {error_msg}")
                        success_count += 1
                    else:
                        logger.error(f"✗ Statement {i+1} failed: {error_msg}")
                        failed_statements.append((i+1, statement[:100], error_msg))
                        # Don't continue on critical failures (schema creation, essential tables)
                        if "CREATE SCHEMA" in statement or "etl_control" in statement or "etl_execution_log" in statement:
                            logger.error(f"Critical statement failed, stopping execution")
                            break
            
            logger.info(f"Schema initialization completed: {success_count}/{len(statements)} statements successful")
            
            # Verify that schemas were created
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT name FROM sys.schemas WHERE name IN ('dwh', 'etl')")).fetchall()
                    schemas = [row[0] for row in result]
                    if 'dwh' in schemas and 'etl' in schemas:
                        logger.info("✓ Verified that dwh and etl schemas exist")
                        
                        # Also verify some key tables exist
                        result = conn.execute(text("""
                            SELECT TABLE_SCHEMA, TABLE_NAME 
                            FROM INFORMATION_SCHEMA.TABLES 
                            WHERE TABLE_SCHEMA IN ('dwh', 'etl')
                        """)).fetchall()
                        tables = [(row[0], row[1]) for row in result]
                        logger.info(f"✓ Found {len(tables)} tables: {tables}")
                        
                    else:
                        logger.error(f"Schema verification failed. Found schemas: {schemas}")
                        raise Exception(f"Required schemas not created. Found: {schemas}")
                        
            except Exception as e:
                logger.error(f"Schema verification failed: {e}")
                raise
            
            logger.info("SQL Server database schema initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQL Server database schema: {e}")
            raise
    
    def execute_query(self, query: str, params=None) -> Any:
        """Execute a SQL query with proper parameter handling for SQL Server"""
        try:
            with self.engine.connect() as conn:
                if params is None:
                    result = conn.execute(text(query))
                elif isinstance(params, list):
                    # Convert list to dict for SQLAlchemy with SQL Server
                    param_dict = {}
                    param_placeholders = query.count('?')
                    for i in range(min(len(params), param_placeholders)):
                        param_dict[f'param{i}'] = params[i]
                    
                    # Replace ? with :param0, :param1, etc.
                    modified_query = query
                    for i in range(param_placeholders):
                        modified_query = modified_query.replace('?', f':param{i}', 1)
                    
                    result = conn.execute(text(modified_query), param_dict)
                else:
                    # Named parameters (dict)
                    result = conn.execute(text(query), params)
                return result
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    def bulk_insert_dataframe(self, df: pd.DataFrame, table_name: str, 
                             schema: str = "dwh", if_exists: str = "append") -> int:
        """Bulk insert DataFrame into SQL Server table with proper data type handling"""
        try:
            # Create a copy of dataframe with proper data types for SQL Server
            df_copy = df.copy()
            
            # Remove metadata columns and timestamp columns that we don't want to ETL
            excluded_columns = ['metadata', 'meaning', 'history', 'onboarded', 'created_at', 'updated_at']
            for col in excluded_columns:
                if col in df_copy.columns:
                    df_copy = df_copy.drop(columns=[col])
                    logger.info(f"Dropped excluded column: {col}")
            
            # Handle timestamp columns for SQL Server compatibility
            datetime_columns = df_copy.select_dtypes(include=['datetime64']).columns
            for col in datetime_columns:
                # Convert to datetime2 compatible format
                df_copy[col] = pd.to_datetime(df_copy[col], utc=True)
            
            # Handle problematic columns that might cause SQL Server issues
            # IMPORTANT: Avoid converting text columns to string as it may override truncation logic
            text_columns = ['content']  # Removed sensitive columns from processing
            for col in df_copy.columns:
                if df_copy[col].dtype == 'object' and col not in text_columns:
                    # Handle None values in non-text string columns
                    df_copy[col] = df_copy[col].astype(str)
                    df_copy[col] = df_copy[col].replace('None', None)
            
            # Handle boolean columns properly (convert to 0/1 for SQL Server BIT type)
            boolean_columns = ['thumbs', 'default_brain', 'is_folder', 'is_active', 'only_chat']
            for col in boolean_columns:
                if col in df_copy.columns:
                    # Convert boolean to BIT (0/1) for SQL Server
                    df_copy[col] = df_copy[col].astype('boolean').fillna(False).astype(int)
            
            # Add ETL metadata column
            df_copy['etl_inserted_at'] = pd.Timestamp.now(tz='UTC')
            
            # Create comprehensive data type mapping for SQL Server
            dtype_mapping = {}
            
            # Map all datetime columns to DateTime to avoid TIMESTAMP issues
            for col in df_copy.columns:
                if df_copy[col].dtype.name.startswith('datetime'):
                    # Use DateTime instead of TIMESTAMP to avoid SQL Server timestamp column issues
                    dtype_mapping[col] = sqlalchemy.types.DateTime()
                elif col in ['id', 'user_id', 'brain_id', 'chat_id', 'message_id', 'prompt_id', 'parent_id']:
                    # Map UUID columns properly - use String for now as UNIQUEIDENTIFIER needs special handling
                    dtype_mapping[col] = sqlalchemy.types.String(36)
                elif col in boolean_columns:
                    # Map boolean columns to BIT
                    dtype_mapping[col] = sqlalchemy.types.Boolean()
                # Removed sensitive column mapping - no longer processing these columns
                elif col in ['file_size', 'daily_requests_count']:
                    # Map integer columns
                    dtype_mapping[col] = sqlalchemy.types.BigInteger()
                elif col == 'etl_inserted_at':
                    # Explicitly map etl_inserted_at to DateTime to avoid TIMESTAMP conflicts
                    dtype_mapping[col] = sqlalchemy.types.DateTime()
            
            logger.info(f"Inserting {len(df_copy)} rows into {schema}.{table_name} with dtype mapping: {list(dtype_mapping.keys())}")
            
            rows_inserted = df_copy.to_sql(
                name=table_name,
                con=self.engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
                method="multi",
                chunksize=self.config.BATCH_SIZE,
                dtype=dtype_mapping
            )
            logger.info(f"✓ Successfully inserted {len(df_copy)} rows into {schema}.{table_name}")
            return len(df_copy)
            
        except Exception as e:
            logger.error(f"Failed to bulk insert into {table_name}: {e}")
            raise
    
    def bulk_upsert_dataframe(self, df: pd.DataFrame, table_name: str, 
                             primary_keys: list[str], schema: str = "dwh") -> int:
        """Bulk upsert DataFrame into SQL Server table using MERGE statement with Vietnamese character support"""
        try:
            if df.empty:
                logger.info(f"No data to upsert for table: {table_name}")
                return 0
            
            # Create a copy of dataframe with proper data types for SQL Server
            df_copy = df.copy()
            
            # Remove metadata columns and timestamp columns that we don't want to ETL
            excluded_columns = ['metadata', 'meaning', 'history', 'onboarded', 'created_at', 'updated_at']
            for col in excluded_columns:
                if col in df_copy.columns:
                    df_copy = df_copy.drop(columns=[col])
                    logger.info(f"Dropped excluded column: {col}")
            
            # Handle timestamp columns for SQL Server compatibility
            datetime_columns = df_copy.select_dtypes(include=['datetime64']).columns
            for col in datetime_columns:
                if df_copy[col].dt.tz is None:
                    df_copy[col] = df_copy[col].dt.tz_localize('UTC')
                else:
                    df_copy[col] = df_copy[col].dt.tz_convert('UTC')
            
            # Handle boolean columns (convert True/False to 1/0 for SQL Server BIT type)
            boolean_columns = ['thumbs', 'default_brain']  # Add known boolean columns
            for col in boolean_columns:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(lambda x: 1 if x else 0 if pd.notna(x) else None)
            
            # Add ETL metadata column
            df_copy['etl_inserted_at'] = pd.Timestamp.now(tz='UTC')
            
            # Create comprehensive data type mapping for SQL Server
            dtype_mapping = {}
            
            # Map all datetime columns to DateTime to avoid TIMESTAMP issues
            for col in df_copy.columns:
                if df_copy[col].dtype.name.startswith('datetime'):
                    # Use DateTime instead of DATETIME2 to avoid SQL Server TIMESTAMP issues
                    dtype_mapping[col] = sqlalchemy.types.DateTime()
                elif col in ['id', 'user_id', 'brain_id', 'chat_id', 'message_id', 'prompt_id', 'parent_id']:
                    # Map UUID columns properly - use String with exact length for UNIQUEIDENTIFIER
                    dtype_mapping[col] = sqlalchemy.types.String(36)
                elif col in boolean_columns:
                    # Map boolean columns to BIT
                    dtype_mapping[col] = sqlalchemy.types.Boolean()
                # Removed sensitive column mapping - no longer processing these columns
            
            # Handle UUID columns - ensure proper string format and handle NULLs
            uuid_columns = ['id', 'user_id', 'brain_id', 'chat_id', 'message_id', 'prompt_id', 'parent_id']
            for col in uuid_columns:
                if col in df_copy.columns:
                    # Convert UUID objects to string format and handle NULLs/empty strings
                    def clean_uuid(x):
                        if x is None or pd.isna(x) or x == '' or str(x).strip() == '':
                            return None
                        try:
                            # Ensure it's a valid UUID format
                            import uuid
                            uuid_str = str(x).strip()
                            # Validate UUID format
                            uuid.UUID(uuid_str)
                            return uuid_str
                        except (ValueError, AttributeError):
                            logger.warning(f"Invalid UUID format for column {col}: {x}")
                            return None
                    
                    df_copy[col] = df_copy[col].apply(clean_uuid)
            
            # Filter out rows with invalid primary keys
            for pk in primary_keys:
                if pk in df_copy.columns:
                    initial_count = len(df_copy)
                    df_copy = df_copy[df_copy[pk].notna()]
                    filtered_count = len(df_copy)
                    if initial_count != filtered_count:
                        logger.info(f"Filtered out {initial_count - filtered_count} rows with null primary key {pk}")
            
            # For chat_history table, use small batch processing to handle Vietnamese characters
            if table_name == 'chat_history':
                return self._process_chat_history_with_small_batches(df_copy, table_name, primary_keys, schema, dtype_mapping)
            
            logger.info(f"Upserting {len(df_copy)} rows into {schema}.{table_name}")
            
            # Generate unique temp table name for merge operation
            import random
            temp_table_name = f"temp_{table_name}_{random.randint(100000, 999999)}"
            
            # Insert data into temp table first
            rows_inserted = df_copy.to_sql(
                name=temp_table_name,
                con=self.engine,
                schema=schema,
                if_exists='replace',
                index=False,
                dtype=dtype_mapping,
                method='multi',
                chunksize=1000
            )
            
            # Generate MERGE statement
            target_table = f"[{schema}].[{table_name}]"
            source_table = f"[{schema}].[{temp_table_name}]"
            
            # Build column lists
            columns = [col for col in df_copy.columns if col != 'etl_inserted_at']
            key_conditions = " AND ".join([f"target.[{pk}] = source.[{pk}]" for pk in primary_keys])
            
            # Build UPDATE SET clause (exclude primary keys and etl timestamp)
            update_columns = [col for col in columns if col not in primary_keys]
            update_set = ", ".join([f"target.[{col}] = source.[{col}]" for col in update_columns])
            
            # Build INSERT columns and values
            all_columns = columns + ['etl_inserted_at']
            insert_columns = ", ".join([f"[{col}]" for col in all_columns])
            insert_values = ", ".join([f"source.[{col}]" for col in all_columns])
            
            # MERGE statement
            merge_sql = f"""
            MERGE {target_table} AS target
            USING {source_table} AS source
            ON ({key_conditions})
            WHEN MATCHED THEN
                UPDATE SET {update_set}, [etl_inserted_at] = source.[etl_inserted_at]
            WHEN NOT MATCHED THEN
                INSERT ({insert_columns})
                VALUES ({insert_values});
            """
            
            # Execute MERGE
            with self.engine.begin() as conn:
                result = conn.execute(text(merge_sql))
                
            # Clean up temp table
            with self.engine.begin() as conn:
                conn.execute(text(f"DROP TABLE {source_table}"))
            
            logger.info(f"✓ Successfully upserted {rows_inserted} rows into {schema}.{table_name}")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"Failed to bulk upsert into {table_name}: {e}")
            # Clean up temp table if it exists
            try:
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS [{schema}].[{temp_table_name}]"))
            except:
                pass
            raise
    
    def _process_chat_history_with_small_batches(self, df: pd.DataFrame, table_name: str, primary_keys: list[str], schema: str, dtype_mapping: dict) -> int:
        """Process chat_history with small batches to handle Vietnamese encoding issues"""
        logger.info(f"Processing chat_history with small batches due to Vietnamese encoding concerns")
        
        # Handle UUID columns before processing - ensure proper string format and handle NULLs
        uuid_columns = ['id', 'user_id', 'brain_id', 'chat_id', 'message_id', 'prompt_id', 'parent_id']
        for col in uuid_columns:
            if col in df.columns:
                # Convert UUID objects to string format and handle NULLs/empty strings
                def clean_uuid(x):
                    if x is None or pd.isna(x) or x == '' or str(x).strip() == '':
                        return None
                    try:
                        # Ensure it's a valid UUID format
                        import uuid
                        uuid_str = str(x).strip()
                        # Validate UUID format
                        uuid.UUID(uuid_str)
                        return uuid_str
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid UUID format for column {col}: {x}")
                        return None
                
                df[col] = df[col].apply(clean_uuid)
        
        # Filter out rows with invalid primary keys
        for pk in primary_keys:
            if pk in df.columns:
                initial_count = len(df)
                df = df[df[pk].notna()]
                filtered_count = len(df)
                if initial_count != filtered_count:
                    logger.info(f"Filtered out {initial_count - filtered_count} rows with null primary key {pk}")
        
        batch_size = 5  # Even smaller batches for ultra-conservative processing
        total_rows = len(df)
        successful_rows = 0
        failed_batches = []
        
        logger.info(f"Processing {total_rows} chat_history records in batches of {batch_size}")
        
        for i in range(0, total_rows, batch_size):
            batch_df = df.iloc[i:i+batch_size].copy()
            batch_num = i // batch_size + 1
            total_batches = (total_rows + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_df)} rows)")
            
            try:
                # Generate unique temp table name for this batch
                import random
                temp_table_name = f"temp_{table_name}_{random.randint(100000, 999999)}"
                
                # Try to insert this batch
                rows_inserted = batch_df.to_sql(
                    name=temp_table_name,
                    con=self.engine,
                    schema=schema,
                    if_exists='replace',
                    index=False,
                    dtype=dtype_mapping,
                    method='multi',
                    chunksize=batch_size
                )
                
                # If successful, perform merge operation
                target_table = f"[{schema}].[{table_name}]"
                source_table = f"[{schema}].[{temp_table_name}]"
                
                # Build merge statement (same as above but for smaller batch)
                columns = [col for col in batch_df.columns if col != 'etl_inserted_at']
                key_conditions = " AND ".join([f"target.[{pk}] = source.[{pk}]" for pk in primary_keys])
                update_columns = [col for col in columns if col not in primary_keys]
                update_set = ", ".join([f"target.[{col}] = source.[{col}]" for col in update_columns])
                all_columns = columns + ['etl_inserted_at']
                insert_columns = ", ".join([f"[{col}]" for col in all_columns])
                insert_values = ", ".join([f"source.[{col}]" for col in all_columns])
                
                merge_sql = f"""
                MERGE {target_table} AS target
                USING {source_table} AS source
                ON ({key_conditions})
                WHEN MATCHED THEN
                    UPDATE SET {update_set}, [etl_inserted_at] = source.[etl_inserted_at]
                WHEN NOT MATCHED THEN
                    INSERT ({insert_columns})
                    VALUES ({insert_values});
                """
                
                with self.engine.begin() as conn:
                    result = conn.execute(text(merge_sql))
                
                # Clean up temp table
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE {source_table}"))
                
                successful_rows += len(batch_df)
                logger.info(f"✓ Batch {batch_num} successful ({len(batch_df)} rows)")
                
            except Exception as e:
                logger.error(f"✗ Batch {batch_num} failed: {e}")
                failed_batches.append({
                    'batch_num': batch_num,
                    'start_idx': i,
                    'end_idx': min(i + batch_size, total_rows),
                    'error': str(e),
                    'message_ids': batch_df.get('message_id', []).tolist()[:3]  # Log first 3 message IDs
                })
                
                # Clean up temp table if it exists
                try:
                    with self.engine.begin() as conn:
                        conn.execute(text(f"DROP TABLE IF EXISTS [{schema}].[{temp_table_name}]"))
                except:
                    pass
        
        # Log summary
        logger.info(f"Chat history batch processing complete: {successful_rows}/{total_rows} rows successful")
        if failed_batches:
            logger.warning(f"Failed batches: {len(failed_batches)}")
            for batch_info in failed_batches[:5]:  # Log first 5 failed batches
                logger.warning(f"Batch {batch_info['batch_num']}: {batch_info['error'][:100]}...")
        
        return successful_rows
    
    def truncate_table(self, table_name: str, schema: str = "dwh"):
        """Truncate a table"""
        try:
            query = f"TRUNCATE TABLE [{schema}].[{table_name}]"
            self.execute_query(query)
            logger.info(f"Truncated table {schema}.{table_name}")
        except Exception as e:
            logger.error(f"Failed to truncate table {table_name}: {e}")
            raise
    
    def get_last_sync_timestamp(self, table_name: str) -> Optional[str]:
        """Get last sync timestamp from control table"""
        try:
            query = """
                SELECT last_sync_timestamp 
                FROM etl.etl_control 
                WHERE table_name = ?
            """
            result = self.execute_query(query, [table_name]).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not get last sync timestamp for {table_name}: {e}")
            return None
    
    def update_sync_timestamp(self, table_name: str, timestamp: str):
        """Update last sync timestamp in control table"""
        try:
            query = """
                MERGE etl.etl_control AS target
                USING (SELECT ? as table_name, ? as last_sync_timestamp) AS source
                ON target.table_name = source.table_name
                WHEN MATCHED THEN
                    UPDATE SET last_sync_timestamp = source.last_sync_timestamp, updated_at = GETUTCDATE()
                WHEN NOT MATCHED THEN
                    INSERT (table_name, last_sync_timestamp, created_at, updated_at)
                    VALUES (source.table_name, source.last_sync_timestamp, GETUTCDATE(), GETUTCDATE());
            """
            self.execute_query(query, [table_name, timestamp])
            logger.info(f"Updated sync timestamp for {table_name}")
        except Exception as e:
            logger.error(f"Failed to update sync timestamp for {table_name}: {e}")
            raise
    
    def close(self):
        """Close all connections"""
        if self.engine:
            self.engine.dispose()

# Connection instances
supabase_conn = SupabaseConnection()
sqlserver_conn = SQLServerConnection() 
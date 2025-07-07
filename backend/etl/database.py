import asyncio
import asyncpg
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, List, Any, Optional
from loguru import logger
from .config import db_config

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
            query = f"SELECT MAX({timestamp_column}) as max_ts FROM {self.config.SUPABASE_SCHEMA}.{table_name}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query)).fetchone()
                return result[0] if result and result[0] else None
                
        except Exception as e:
            logger.error(f"Failed to get max timestamp from {table_name}: {e}")
            return None
    
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
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("SQL Server connection test successful")
                return True
        except Exception as e:
            logger.error(f"SQL Server connection test failed: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """Create data warehouse database if it doesn't exist"""
        try:
            # Connect to master database first
            master_url = self.config.sqlserver_url.replace(f"/{self.config.SQLSERVER_DATABASE}", "/master")
            master_engine = create_engine(master_url)
            
            with master_engine.connect() as conn:
                # Check if database exists
                result = conn.execute(text(f"""
                    SELECT name FROM sys.databases 
                    WHERE name = '{self.config.SQLSERVER_DATABASE}'
                """))
                
                if not result.fetchone():
                    # Create database
                    conn.execute(text(f"CREATE DATABASE [{self.config.SQLSERVER_DATABASE}]"))
                    logger.info(f"Created database: {self.config.SQLSERVER_DATABASE}")
                else:
                    logger.info(f"Database {self.config.SQLSERVER_DATABASE} already exists")
            
            master_engine.dispose()
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute a SQL query"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                return result
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
    
    def bulk_insert_dataframe(self, df: pd.DataFrame, table_name: str, 
                             schema: str = "dbo", if_exists: str = "append") -> int:
        """Bulk insert DataFrame into SQL Server table"""
        try:
            rows_inserted = df.to_sql(
                name=table_name,
                con=self.engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
                method="multi",
                chunksize=self.config.BATCH_SIZE
            )
            logger.info(f"Inserted {len(df)} rows into {schema}.{table_name}")
            return len(df)
            
        except Exception as e:
            logger.error(f"Failed to bulk insert into {table_name}: {e}")
            raise
    
    def truncate_table(self, table_name: str, schema: str = "dbo"):
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
                FROM etl_control 
                WHERE table_name = :table_name
            """
            result = self.execute_query(query, {"table_name": table_name}).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not get last sync timestamp for {table_name}: {e}")
            return None
    
    def update_sync_timestamp(self, table_name: str, timestamp: str):
        """Update last sync timestamp in control table"""
        try:
            query = """
                MERGE etl_control AS target
                USING (SELECT :table_name as table_name, :timestamp as last_sync_timestamp) AS source
                ON target.table_name = source.table_name
                WHEN MATCHED THEN
                    UPDATE SET last_sync_timestamp = source.last_sync_timestamp, updated_at = GETUTCDATE()
                WHEN NOT MATCHED THEN
                    INSERT (table_name, last_sync_timestamp, created_at, updated_at)
                    VALUES (source.table_name, source.last_sync_timestamp, GETUTCDATE(), GETUTCDATE());
            """
            self.execute_query(query, {"table_name": table_name, "timestamp": timestamp})
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
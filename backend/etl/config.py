from pydantic_settings import BaseSettings
from pydantic import Field

class DatabaseConfig(BaseSettings):
    """Database configuration for both source and target"""
    
    # Supabase (Source) Configuration
    SUPABASE_HOST: str = Field(default="localhost", description="Supabase host")
    SUPABASE_PORT: int = Field(default=54322, description="Supabase port") 
    SUPABASE_DATABASE: str = Field(default="postgres", description="Supabase database name")
    SUPABASE_USER: str = Field(default="postgres", description="Supabase username")
    SUPABASE_PASSWORD: str = Field(default="postgres", description="Supabase password")
    SUPABASE_SCHEMA: str = Field(default="public", description="Supabase schema")
    
    # SQL Server (Target) Configuration  
    SQLSERVER_HOST: str = Field(default="localhost", description="SQL Server host")
    SQLSERVER_PORT: int = Field(default=1433, description="SQL Server port")
    SQLSERVER_DATABASE: str = Field(default="DataWarehouse", description="SQL Server database")
    SQLSERVER_USER: str = Field(default="sa", description="SQL Server username")
    SQLSERVER_PASSWORD: str = Field(default="YourPassword123", description="SQL Server password")
    SQLSERVER_DRIVER: str = Field(default="ODBC Driver 17 for SQL Server", description="SQL Server ODBC driver")
    
    # ETL Configuration
    BATCH_SIZE: int = Field(default=1000, description="Batch size for data processing")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SYNC_INTERVAL_MINUTES: int = Field(default=60, description="Sync interval in minutes")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    RETRY_DELAY: int = Field(default=5, description="Retry delay in seconds")
    
    # Performance Configuration
    PARALLEL_WORKERS: int = Field(default=4, description="Number of parallel workers")
    CONNECTION_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def supabase_url(self) -> str:
        """Generate Supabase connection URL"""
        return f"postgresql://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DATABASE}"
    
    @property
    def sqlserver_url(self) -> str:
        """Generate SQL Server connection URL"""
        return f"mssql+pyodbc://{self.SQLSERVER_USER}:{self.SQLSERVER_PASSWORD}@{self.SQLSERVER_HOST}:{self.SQLSERVER_PORT}/{self.SQLSERVER_DATABASE}?driver={self.SQLSERVER_DRIVER.replace(' ', '+')}"

class ETLConfig(BaseSettings):
    """ETL pipeline configuration"""
    
    # Table Configuration - Define which tables to sync
    SYNC_TABLES: list[str] = Field(
        default=[
            "users",
            "brains", 
            "chats",
            "chat_history",
            "vectors",
            "knowledge",
            "api_keys",
            "user_settings",
            "notifications",
            "prompts",
            "brains_users",
            "brains_vectors",
            "knowledge_vectors",
            "user_daily_usage"
        ],
        description="List of tables to synchronize"
    )
    
    # Incremental sync configuration
    INCREMENTAL_TABLES: dict[str, str] = Field(
        default={
            "chat_history": "message_time",
            "chats": "creation_time", 
            "notifications": "datetime",
            "user_daily_usage": "date",
            "vectors": "id",  # Use ID for change tracking
            "knowledge": "id"
        },
        description="Tables with incremental sync and their timestamp/ID columns"
    )
    
    # Data transformation rules
    EXCLUDE_COLUMNS: dict[str, list[str]] = Field(
        default={
            "api_keys": ["api_key"],  # Exclude sensitive data
            "users": [],  # Could exclude PII if needed
        },
        description="Columns to exclude from sync per table"
    )

# Global configuration instances
db_config = DatabaseConfig()
etl_config = ETLConfig() 
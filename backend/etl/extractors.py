import pandas as pd
from typing import Optional, Dict
from datetime import datetime
import json
from loguru import logger

from database import supabase_conn, sqlserver_conn
from config import etl_config

class BaseExtractor:
    """Base class for all table extractors"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.supabase = supabase_conn
        self.sqlserver = sqlserver_conn
        self.config = etl_config
    
    def extract_full(self) -> pd.DataFrame:
        """Extract all data from source table"""
        logger.info(f"Starting full extraction for {self.table_name}")
        
        # Get excluded columns
        exclude_cols = self.config.EXCLUDE_COLUMNS.get(self.table_name, [])
        
        # Get all columns except excluded ones
        schema = self.supabase.get_table_schema(self.table_name)
        columns = [col for col in schema.keys() if col not in exclude_cols]
        
        # Extract data
        df = self.supabase.extract_table_data(
            table_name=self.table_name,
            columns=columns
        )
        
        # Transform data
        df = self.transform_data(df)
        
        logger.info(f"Extracted {len(df)} rows from {self.table_name}")
        return df
    
    def extract_incremental(self, last_sync_timestamp: Optional[str] = None) -> pd.DataFrame:
        """Extract incremental data based on timestamp"""
        logger.info(f"Starting incremental extraction for {self.table_name}")
        
        if self.table_name not in self.config.INCREMENTAL_TABLES:
            logger.warning(f"Table {self.table_name} not configured for incremental sync, doing full sync")
            return self.extract_full()
        
        timestamp_column = self.config.INCREMENTAL_TABLES[self.table_name]
        
        # Get last sync timestamp from DWH if not provided
        if not last_sync_timestamp:
            last_sync_timestamp = self.sqlserver.get_last_sync_timestamp(self.table_name)
        
        # Build where clause for incremental sync
        where_clause = None
        if last_sync_timestamp:
            where_clause = f"{timestamp_column} > '{last_sync_timestamp}'"
            logger.info(f"Incremental sync since: {last_sync_timestamp}")
        else:
            logger.info("No previous sync timestamp found, doing full sync")
        
        # Get excluded columns
        exclude_cols = self.config.EXCLUDE_COLUMNS.get(self.table_name, [])
        
        # Get all columns except excluded ones
        schema = self.supabase.get_table_schema(self.table_name)
        columns = [col for col in schema.keys() if col not in exclude_cols]
        
        # Extract data
        df = self.supabase.extract_table_data(
            table_name=self.table_name,
            columns=columns,
            where_clause=where_clause
        )
        
        # Transform data
        df = self.transform_data(df)
        
        logger.info(f"Extracted {len(df)} rows from {self.table_name} (incremental)")
        return df
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data - override in subclasses for specific transformations"""
        if df.empty:
            return df
        
        # Add ETL metadata
        df['etl_inserted_at'] = datetime.utcnow()
        
        # Handle UUID columns
        df = self._convert_uuids(df)
        
        # Handle JSON columns
        df = self._convert_json_columns(df)
        
        # Handle boolean columns
        df = self._convert_booleans(df)
        
        return df
    
    def _convert_uuids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert UUID columns to proper format"""
        uuid_columns = [
            'id', 'user_id', 'brain_id', 'chat_id', 'message_id', 
            'vector_id', 'knowledge_id', 'prompt_id', 'key_id'
        ]
        
        for col in uuid_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        return df
    
    def _convert_json_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert JSON columns to string format for SQL Server"""
        json_columns = ['history', 'metadata', 'models', 'params', 'search_params', 'secrets']
        
        for col in json_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: json.dumps(x) if x is not None and not pd.isna(x) else None)
        
        return df
    
    def _convert_booleans(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert boolean columns to proper format"""
        boolean_columns = ['default_brain', 'is_active', 'only_chat']
        
        for col in boolean_columns:
            if col in df.columns:
                df[col] = df[col].astype('boolean').astype('Int64')  # Convert to nullable integer
        
        return df

class UserExtractor(BaseExtractor):
    """Extractor for users table"""
    
    def __init__(self):
        super().__init__('users')
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().transform_data(df)
        
        if df.empty:
            return df
        
        # Add created_at and updated_at columns if they don't exist
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.utcnow()
        if 'updated_at' not in df.columns:
            df['updated_at'] = datetime.utcnow()
        
        return df

class ChatHistoryExtractor(BaseExtractor):
    """Extractor for chat_history table with special handling for large text"""
    
    def __init__(self):
        super().__init__('chat_history')
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().transform_data(df)
        
        if df.empty:
            return df
        
        # Truncate very long messages to prevent SQL Server issues
        max_length = 50000  # Reasonable limit for NVARCHAR(MAX)
        
        if 'user_message' in df.columns:
            df['user_message'] = df['user_message'].apply(
                lambda x: x[:max_length] if isinstance(x, str) and len(x) > max_length else x
            )
        
        if 'assistant' in df.columns:
            df['assistant'] = df['assistant'].apply(
                lambda x: x[:max_length] if isinstance(x, str) and len(x) > max_length else x
            )
        
        return df

class VectorExtractor(BaseExtractor):
    """Extractor for vectors table (excluding actual embeddings)"""
    
    def __init__(self):
        super().__init__('vectors')
    
    def extract_full(self) -> pd.DataFrame:
        """Extract vectors metadata without embeddings"""
        logger.info(f"Starting full extraction for {self.table_name}")
        
        # Exclude embedding column and other sensitive data
        exclude_cols = ['embedding'] + self.config.EXCLUDE_COLUMNS.get(self.table_name, [])
        
        # Get all columns except excluded ones
        schema = self.supabase.get_table_schema(self.table_name)
        columns = [col for col in schema.keys() if col not in exclude_cols]
        
        # Extract data
        df = self.supabase.extract_table_data(
            table_name=self.table_name,
            columns=columns
        )
        
        # Transform data
        df = self.transform_data(df)
        
        logger.info(f"Extracted {len(df)} rows from {self.table_name}")
        return df
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().transform_data(df)
        
        if df.empty:
            return df
        
        # Add embedding metadata
        df['embedding_model'] = 'text-embedding-3-large'  # Default model
        df['embedding_dimensions'] = 3072  # Default dimensions
        
        # Truncate content if too long
        max_content_length = 10000
        if 'content' in df.columns:
            df['content'] = df['content'].apply(
                lambda x: x[:max_content_length] if isinstance(x, str) and len(x) > max_content_length else x
            )
        
        return df

class KnowledgeExtractor(BaseExtractor):
    """Extractor for knowledge table with file size estimation"""
    
    def __init__(self):
        super().__init__('knowledge')
    
    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().transform_data(df)
        
        if df.empty:
            return df
        
        # Add file size estimation (placeholder - could be enhanced with actual file size)
        df['file_size'] = 0
        
        # Add created_at if missing
        if 'created_at' not in df.columns:
            df['created_at'] = datetime.utcnow()
        
        return df

class ApiKeyExtractor(BaseExtractor):
    """Extractor for API keys (excluding sensitive api_key column)"""
    
    def __init__(self):
        super().__init__('api_keys')
    
    def extract_full(self) -> pd.DataFrame:
        """Extract API keys metadata without the actual key"""
        logger.info(f"Starting full extraction for {self.table_name}")
        
        # Always exclude the actual API key
        exclude_cols = ['api_key'] + self.config.EXCLUDE_COLUMNS.get(self.table_name, [])
        
        # Get all columns except excluded ones
        schema = self.supabase.get_table_schema(self.table_name)
        columns = [col for col in schema.keys() if col not in exclude_cols]
        
        # Extract data
        df = self.supabase.extract_table_data(
            table_name=self.table_name,
            columns=columns
        )
        
        # Transform data
        df = self.transform_data(df)
        
        logger.info(f"Extracted {len(df)} rows from {self.table_name}")
        return df

# Extractor factory
class ExtractorFactory:
    """Factory to create appropriate extractor for each table"""
    
    @staticmethod
    def create_extractor(table_name: str) -> BaseExtractor:
        """Create appropriate extractor based on table name"""
        
        extractors = {
            'users': UserExtractor,
            'chat_history': ChatHistoryExtractor,
            'vectors': VectorExtractor,
            'knowledge': KnowledgeExtractor,
            'api_keys': ApiKeyExtractor,
        }
        
        extractor_class = extractors.get(table_name, BaseExtractor)
        
        if extractor_class == BaseExtractor:
            return BaseExtractor(table_name)
        else:
            return extractor_class()

# Convenience function to get all extractors
def get_all_extractors() -> Dict[str, BaseExtractor]:
    """Get all configured extractors"""
    extractors = {}
    
    for table_name in etl_config.SYNC_TABLES:
        extractors[table_name] = ExtractorFactory.create_extractor(table_name)
    
    return extractors 
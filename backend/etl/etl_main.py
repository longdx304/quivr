#!/usr/bin/env python3
"""
Main ETL pipeline for Quivr Data Warehouse
Extracts data from Supabase and loads into SQL Server DWH
"""

import sys
import time
import traceback
import schedule
from datetime import datetime, timedelta
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from .config import db_config, etl_config
from .database import supabase_conn, sqlserver_conn
from .extractors import get_all_extractors
from .utils import setup_logging, send_notification

class ETLPipeline:
    """Main ETL Pipeline orchestrator"""
    
    def __init__(self):
        self.supabase = supabase_conn
        self.sqlserver = sqlserver_conn
        self.extractors = get_all_extractors()
        self.execution_id = None
        self.start_time = None
        self.stats = {
            'total_tables': 0,
            'successful_tables': 0,
            'failed_tables': 0,
            'total_records': 0,
            'execution_time': 0
        }
    
    def initialize(self) -> bool:
        """Initialize ETL pipeline"""
        try:
            logger.info("Initializing ETL Pipeline...")
            
            # Test connections
            if not self._test_connections():
                return False
            
            # Create database and schema if needed
            self._setup_target_database()
            
            logger.info("ETL Pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ETL pipeline: {e}")
            return False
    
    def _test_connections(self) -> bool:
        """Test database connections"""
        try:
            # Test Supabase connection
            with self.supabase.get_session() as session:
                session.execute("SELECT 1")
            logger.info("✓ Supabase connection successful")
            
            # Test SQL Server connection
            if not self.sqlserver.test_connection():
                logger.error("✗ SQL Server connection failed")
                return False
            logger.info("✓ SQL Server connection successful")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def _setup_target_database(self):
        """Setup target database and schema"""
        try:
            # Create database if it doesn't exist
            self.sqlserver.create_database_if_not_exists()
            
            # Run schema creation script
            with open('backend/etl/sql_scripts/create_warehouse_schema.sql', 'r') as f:
                schema_script = f.read()
            
            # Execute schema script in chunks
            statements = schema_script.split('GO')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    self.sqlserver.execute_query(statement)
            
            logger.info("Target database schema setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup target database: {e}")
            raise
    
    def run_full_sync(self, tables: Optional[List[str]] = None) -> bool:
        """Run full synchronization for all or specified tables"""
        try:
            self._start_execution()
            
            # Determine tables to sync
            sync_tables = tables or etl_config.SYNC_TABLES
            self.stats['total_tables'] = len(sync_tables)
            
            logger.info(f"Starting full sync for {len(sync_tables)} tables")
            
            # Sync tables in parallel
            success = self._sync_tables_parallel(sync_tables, incremental=False)
            
            # Finalize execution
            self._finish_execution(success)
            
            return success
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            self._finish_execution(False, str(e))
            return False
    
    def run_incremental_sync(self, tables: Optional[List[str]] = None) -> bool:
        """Run incremental synchronization for all or specified tables"""
        try:
            self._start_execution()
            
            # Determine tables to sync (only incremental tables)
            if tables:
                sync_tables = [t for t in tables if t in etl_config.INCREMENTAL_TABLES]
            else:
                sync_tables = list(etl_config.INCREMENTAL_TABLES.keys())
            
            # Add non-incremental tables for full sync
            non_incremental = [t for t in (tables or etl_config.SYNC_TABLES) 
                             if t not in etl_config.INCREMENTAL_TABLES]
            
            self.stats['total_tables'] = len(sync_tables) + len(non_incremental)
            
            logger.info(f"Starting incremental sync for {len(sync_tables)} tables")
            logger.info(f"Full sync for {len(non_incremental)} non-incremental tables")
            
            # Sync incremental tables
            success_incremental = self._sync_tables_parallel(sync_tables, incremental=True)
            
            # Sync non-incremental tables (full sync)
            success_full = True
            if non_incremental:
                success_full = self._sync_tables_parallel(non_incremental, incremental=False)
            
            success = success_incremental and success_full
            
            # Finalize execution
            self._finish_execution(success)
            
            return success
            
        except Exception as e:
            logger.error(f"Incremental sync failed: {e}")
            self._finish_execution(False, str(e))
            return False
    
    def _sync_tables_parallel(self, tables: List[str], incremental: bool = False) -> bool:
        """Sync tables in parallel"""
        success = True
        
        # Use thread pool for parallel processing
        max_workers = min(len(tables), db_config.PARALLEL_WORKERS)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all table sync tasks
            future_to_table = {
                executor.submit(self._sync_single_table, table, incremental): table
                for table in tables
            }
            
            # Process completed tasks
            for future in as_completed(future_to_table):
                table = future_to_table[future]
                try:
                    table_success = future.result()
                    if table_success:
                        self.stats['successful_tables'] += 1
                    else:
                        self.stats['failed_tables'] += 1
                        success = False
                        
                except Exception as e:
                    logger.error(f"Table {table} sync failed with exception: {e}")
                    self.stats['failed_tables'] += 1
                    success = False
        
        return success
    
    def _sync_single_table(self, table_name: str, incremental: bool = False) -> bool:
        """Sync a single table"""
        try:
            logger.info(f"Starting sync for table: {table_name}")
            table_start_time = time.time()
            
            # Get extractor for this table
            extractor = self.extractors.get(table_name)
            if not extractor:
                logger.error(f"No extractor found for table: {table_name}")
                return False
            
            # Extract data
            if incremental and table_name in etl_config.INCREMENTAL_TABLES:
                df = extractor.extract_incremental()
            else:
                df = extractor.extract_full()
            
            if df.empty:
                logger.info(f"No data to sync for table: {table_name}")
                self._log_table_execution(table_name, True, 0, time.time() - table_start_time)
                return True
            
            # Load data to SQL Server
            if incremental:
                # For incremental, append data
                rows_loaded = self.sqlserver.bulk_insert_dataframe(
                    df, table_name, schema='dwh', if_exists='append'
                )
            else:
                # For full sync, replace data
                self.sqlserver.truncate_table(table_name, schema='dwh')
                rows_loaded = self.sqlserver.bulk_insert_dataframe(
                    df, table_name, schema='dwh', if_exists='append'
                )
            
            # Update sync timestamp for incremental tables
            if table_name in etl_config.INCREMENTAL_TABLES:
                max_timestamp = self.supabase.get_max_timestamp(
                    table_name, etl_config.INCREMENTAL_TABLES[table_name]
                )
                if max_timestamp:
                    self.sqlserver.update_sync_timestamp(table_name, str(max_timestamp))
            
            execution_time = time.time() - table_start_time
            self.stats['total_records'] += len(df)
            
            logger.info(f"✓ Table {table_name} synced successfully: {len(df)} rows in {execution_time:.2f}s")
            self._log_table_execution(table_name, True, len(df), execution_time)
            
            return True
            
        except Exception as e:
            execution_time = time.time() - table_start_time if 'table_start_time' in locals() else 0
            logger.error(f"✗ Table {table_name} sync failed: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self._log_table_execution(table_name, False, 0, execution_time, str(e))
            return False
    
    def _start_execution(self):
        """Start execution tracking"""
        self.execution_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        self.start_time = time.time()
        self.stats = {
            'total_tables': 0,
            'successful_tables': 0,
            'failed_tables': 0,
            'total_records': 0,
            'execution_time': 0
        }
        logger.info(f"=== ETL Execution Started (ID: {self.execution_id}) ===")
    
    def _finish_execution(self, success: bool, error_message: str = None):
        """Finish execution tracking"""
        self.stats['execution_time'] = time.time() - self.start_time
        
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"=== ETL Execution Finished (ID: {self.execution_id}) ===")
        logger.info(f"Status: {status}")
        logger.info(f"Total Tables: {self.stats['total_tables']}")
        logger.info(f"Successful: {self.stats['successful_tables']}")
        logger.info(f"Failed: {self.stats['failed_tables']}")
        logger.info(f"Total Records: {self.stats['total_records']}")
        logger.info(f"Execution Time: {self.stats['execution_time']:.2f}s")
        
        # Log to database
        try:
            self._log_execution(success, error_message)
        except Exception as e:
            logger.error(f"Failed to log execution to database: {e}")
        
        # Send notification if configured
        try:
            send_notification(self.execution_id, success, self.stats, error_message)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
    
    def _log_execution(self, success: bool, error_message: str = None):
        """Log execution to database"""
        try:
            query = """
                INSERT INTO [etl].[etl_execution_log] 
                (execution_id, start_time, end_time, status, records_processed, 
                 error_message, execution_duration_seconds)
                VALUES (:execution_id, :start_time, :end_time, :status, 
                        :records_processed, :error_message, :duration)
            """
            
            params = {
                'execution_id': self.execution_id,
                'start_time': datetime.utcfromtimestamp(self.start_time),
                'end_time': datetime.utcnow(),
                'status': 'SUCCESS' if success else 'FAILED',
                'records_processed': self.stats['total_records'],
                'error_message': error_message,
                'duration': int(self.stats['execution_time'])
            }
            
            self.sqlserver.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
    
    def _log_table_execution(self, table_name: str, success: bool, 
                           records: int, duration: float, error: str = None):
        """Log individual table execution"""
        try:
            query = """
                INSERT INTO [etl].[etl_execution_log] 
                (execution_id, table_name, start_time, end_time, status, 
                 records_processed, error_message, execution_duration_seconds)
                VALUES (:execution_id, :table_name, :start_time, :end_time, 
                        :status, :records_processed, :error_message, :duration)
            """
            
            params = {
                'execution_id': self.execution_id,
                'table_name': table_name,
                'start_time': datetime.utcnow() - timedelta(seconds=duration),
                'end_time': datetime.utcnow(),
                'status': 'SUCCESS' if success else 'FAILED',
                'records_processed': records,
                'error_message': error,
                'duration': int(duration)
            }
            
            self.sqlserver.execute_query(query, params)
            
        except Exception as e:
            logger.warning(f"Failed to log table execution for {table_name}: {e}")

class ETLScheduler:
    """ETL Pipeline scheduler"""
    
    def __init__(self):
        self.pipeline = ETLPipeline()
        self.running = False
    
    def start_scheduler(self):
        """Start the ETL scheduler"""
        if not self.pipeline.initialize():
            logger.error("Failed to initialize ETL pipeline, exiting...")
            sys.exit(1)
        
        # Schedule incremental sync every hour
        schedule.every(etl_config.SYNC_INTERVAL_MINUTES).minutes.do(
            self._run_incremental_sync_safe
        )
        
        # Schedule full sync daily at 2 AM
        schedule.every().day.at("02:00").do(
            self._run_full_sync_safe
        )
        
        logger.info("ETL Scheduler started")
        logger.info(f"Incremental sync: every {etl_config.SYNC_INTERVAL_MINUTES} minutes")
        logger.info("Full sync: daily at 2:00 AM")
        
        self.running = True
        
        # Run initial incremental sync
        self._run_incremental_sync_safe()
        
        # Main scheduler loop
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def stop_scheduler(self):
        """Stop the ETL scheduler"""
        self.running = False
        logger.info("ETL Scheduler stopped")
    
    def _run_incremental_sync_safe(self):
        """Run incremental sync with error handling"""
        try:
            logger.info("Scheduled incremental sync starting...")
            self.pipeline.run_incremental_sync()
        except Exception as e:
            logger.error(f"Scheduled incremental sync failed: {e}")
    
    def _run_full_sync_safe(self):
        """Run full sync with error handling"""
        try:
            logger.info("Scheduled full sync starting...")
            self.pipeline.run_full_sync()
        except Exception as e:
            logger.error(f"Scheduled full sync failed: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quivr ETL Pipeline')
    parser.add_argument('--mode', choices=['full', 'incremental', 'schedule'], 
                       default='schedule', help='ETL mode to run')
    parser.add_argument('--tables', nargs='*', help='Specific tables to sync')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create pipeline
    pipeline = ETLPipeline()
    
    if not pipeline.initialize():
        logger.error("Failed to initialize ETL pipeline")
        sys.exit(1)
    
    # Run based on mode
    if args.mode == 'full':
        logger.info("Running full sync...")
        success = pipeline.run_full_sync(args.tables)
        sys.exit(0 if success else 1)
        
    elif args.mode == 'incremental':
        logger.info("Running incremental sync...")
        success = pipeline.run_incremental_sync(args.tables)
        sys.exit(0 if success else 1)
        
    elif args.mode == 'schedule':
        logger.info("Starting ETL scheduler...")
        scheduler = ETLScheduler()
        try:
            scheduler.start_scheduler()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
            scheduler.stop_scheduler()
        except Exception as e:
            logger.error(f"Scheduler failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main() 
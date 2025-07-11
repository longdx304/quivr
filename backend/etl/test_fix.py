#!/usr/bin/env python3
"""
Test script to verify ETL fix for duplicate primary key issues
"""

import sys
import logging
from etl_main import ETLPipeline

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_incremental_sync():
    """Test incremental sync with the new UPSERT logic"""
    try:
        logger.info("Testing ETL incremental sync fix...")
        
        # Create ETL pipeline
        pipeline = ETLPipeline()
        
        # Initialize pipeline
        if not pipeline.initialize():
            logger.error("Failed to initialize ETL pipeline")
            return False
        
        # Test incremental sync on a specific problematic table
        test_tables = ['chat_history', 'chats', 'knowledge', 'user_daily_usage']
        
        for table in test_tables:
            logger.info(f"Testing incremental sync for table: {table}")
            success = pipeline._sync_single_table(table, incremental=True)
            
            if success:
                logger.info(f"✓ Table {table} sync successful")
            else:
                logger.error(f"✗ Table {table} sync failed")
                return False
        
        logger.info("✓ All incremental sync tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting ETL fix verification...")
    
    success = test_incremental_sync()
    
    if success:
        logger.info("✓ ETL fix verification PASSED")
        sys.exit(0)
    else:
        logger.error("✗ ETL fix verification FAILED")
        sys.exit(1)

if __name__ == '__main__':
    main() 
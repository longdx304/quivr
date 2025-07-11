#!/usr/bin/env python3
"""
ETL System Test Script
Tests database connections and basic ETL functionality
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import db_config
from database import SupabaseConnection, SQLServerConnection

def test_environment_variables():
    """Test that environment variables are loaded correctly"""
    print("=== Environment Variable Test ===")
    print(f"SUPABASE_HOST: {db_config.SUPABASE_HOST}")
    print(f"SUPABASE_PORT: {db_config.SUPABASE_PORT}")
    print(f"SQLSERVER_HOST: {db_config.SQLSERVER_HOST}")
    print(f"SQLSERVER_DATABASE: {db_config.SQLSERVER_DATABASE}")
    print(f"BATCH_SIZE: {db_config.BATCH_SIZE}")
    print("")

def test_database_connections():
    """Test database connections"""
    print("=== Database Connection Test ===")
    
    # Test SQL Server connection
    try:
        print("Testing SQL Server connection...")
        sqlserver = SQLServerConnection()
        if sqlserver.test_connection():
            print("✓ SQL Server connection successful")
        else:
            print("✗ SQL Server connection failed")
            return False
    except Exception as e:
        print(f"✗ SQL Server connection error: {e}")
        return False
    
    # Test Supabase connection (optional)
    try:
        print("Testing Supabase connection...")
        supabase = SupabaseConnection()
        # Simple test query
        with supabase.engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Supabase connection successful")
    except Exception as e:
        print(f"⚠ Supabase connection warning (may be normal in container): {e}")
    
    print("")
    return True

def test_schema_initialization():
    """Test schema initialization"""
    print("=== Schema Initialization Test ===")
    
    try:
        sqlserver = SQLServerConnection()
        sqlserver.initialize_database_schema()
        print("✓ Schema initialization successful")
        return True
    except Exception as e:
        print(f"✗ Schema initialization failed: {e}")
        return False

def test_table_existence():
    """Test that required tables exist"""
    print("=== Table Existence Test ===")
    
    required_tables = [
        ('etl', 'etl_control'),
        ('etl', 'etl_execution_log'),
        ('dwh', 'users'),
        ('dwh', 'brains'),
        ('dwh', 'knowledge'),
        ('dwh', 'chats'),
        ('dwh', 'chat_history'),
        ('dwh', 'brains_users'),
        ('dwh', 'user_daily_usage')
    ]
    
    try:
        sqlserver = SQLServerConnection()
        missing_tables = []
        
        for schema, table in required_tables:
            try:
                query = f"""
                SELECT COUNT(*) as table_exists 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
                """
                result = sqlserver.execute_query(query).fetchone()
                if result[0] == 1:
                    print(f"✓ {schema}.{table} exists")
                else:
                    print(f"✗ {schema}.{table} missing")
                    missing_tables.append(f"{schema}.{table}")
            except Exception as e:
                print(f"? Error checking {schema}.{table}: {e}")
                missing_tables.append(f"{schema}.{table}")
        
        if missing_tables:
            print(f"\nMissing tables: {missing_tables}")
            return False
        else:
            print("\n✓ All required tables exist")
            return True
            
    except Exception as e:
        print(f"✗ Table existence check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting ETL System Tests...\n")
    
    # Import text here to avoid issues if sqlalchemy isn't available
    try:
        from sqlalchemy import text
        globals()['text'] = text
    except ImportError:
        print("SQLAlchemy not available - some tests may fail")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Database Connections", test_database_connections),  
        ("Schema Initialization", test_schema_initialization),
        ("Table Existence", test_table_existence)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
        print("-" * 50)
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("✓ All tests passed! ETL system is ready.")
        return 0
    else:
        print("✗ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main()) 
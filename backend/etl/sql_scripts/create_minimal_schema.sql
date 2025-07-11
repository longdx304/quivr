-- =============================================
-- Minimal Quivr Data Warehouse Schema for SQL Server
-- Essential schemas and tables for ETL system operation
-- =============================================

USE [DataWarehouse]
GO

-- Create essential schemas
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dwh')
BEGIN
    EXEC('CREATE SCHEMA [dwh]')
    PRINT 'Created schema: dwh'
END
ELSE
    PRINT 'Schema dwh already exists'
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'etl')
BEGIN
    EXEC('CREATE SCHEMA [etl]')
    PRINT 'Created schema: etl'
END
ELSE
    PRINT 'Schema etl already exists'
GO

-- =============================================
-- ETL Control Tables (Essential for ETL operation)
-- =============================================

-- ETL control table for tracking sync status
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'etl' AND TABLE_NAME = 'etl_control')
BEGIN
    CREATE TABLE [etl].[etl_control] (
        [table_name] NVARCHAR(100) PRIMARY KEY,
        [last_sync_timestamp] DATETIME2(7),
        [sync_status] NVARCHAR(20) DEFAULT 'ACTIVE',
        [record_count] BIGINT DEFAULT 0,
        [created_at] DATETIME2(7) DEFAULT GETUTCDATE(),
        [updated_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: etl.etl_control'
END
ELSE
    PRINT 'Table etl.etl_control already exists'
GO

-- ETL execution log
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'etl' AND TABLE_NAME = 'etl_execution_log')
BEGIN
    CREATE TABLE [etl].[etl_execution_log] (
        [id] BIGINT IDENTITY(1,1) PRIMARY KEY,
        [execution_id] NVARCHAR(50),
        [table_name] NVARCHAR(100),
        [start_time] DATETIME2(7) DEFAULT GETUTCDATE(),
        [end_time] DATETIME2(7),
        [status] NVARCHAR(20), -- SUCCESS, FAILED, RUNNING
        [records_processed] BIGINT DEFAULT 0,
        [error_message] NVARCHAR(MAX),
        [execution_duration_seconds] INT
    )
    PRINT 'Created table: etl.etl_execution_log'
END
ELSE
    PRINT 'Table etl.etl_execution_log already exists'
GO

-- =============================================
-- Essential Data Warehouse Tables
-- =============================================

-- Users table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'users')
BEGIN
    CREATE TABLE [dwh].[users] (
        [id] UNIQUEIDENTIFIER PRIMARY KEY,
        [email] NVARCHAR(255),
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: dwh.users'
END
ELSE
    PRINT 'Table dwh.users already exists'
GO

-- Brains table (with additional columns from Supabase, excluding metadata columns)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'brains')
BEGIN
    CREATE TABLE [dwh].[brains] (
        [brain_id] UNIQUEIDENTIFIER PRIMARY KEY,
        [name] NVARCHAR(255),
        [status] NVARCHAR(50),
        [model] NVARCHAR(100),
        [max_tokens] INT,
        [temperature] FLOAT,
        [description] NVARCHAR(MAX),
        [prompt_id] UNIQUEIDENTIFIER,
        [last_update] DATETIME2(7),
        [brain_type] NVARCHAR(20),
        [openai_api_key] NVARCHAR(255),
        [tags] NVARCHAR(MAX),
        [snippet_color] NVARCHAR(20),
        [snippet_emoji] NVARCHAR(10),
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: dwh.brains'
END
ELSE
    PRINT 'Table dwh.brains already exists'
GO

-- Knowledge table (with proper column structure for SQL Server)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'knowledge')
BEGIN
    CREATE TABLE [dwh].[knowledge] (
        [id] UNIQUEIDENTIFIER PRIMARY KEY,
        [file_name] NVARCHAR(500),
        [url] NVARCHAR(1000),
        [extension] NVARCHAR(50),
        [source] NVARCHAR(255),
        [source_link] NVARCHAR(1000),
        [status] NVARCHAR(50),
        [file_sha1] NVARCHAR(64),
        [created_at] DATETIME2(7),
        [file_size] BIGINT,
        [metadata] NVARCHAR(MAX),
        [updated_at] DATETIME2(7),
        [user_id] UNIQUEIDENTIFIER,
        [is_folder] BIT,
        [parent_id] UNIQUEIDENTIFIER,
        [brain_id] UNIQUEIDENTIFIER,
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: dwh.knowledge'
END
ELSE
    PRINT 'Table dwh.knowledge already exists'
GO

-- Brains users relationship table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'brains_users')
BEGIN
    CREATE TABLE [dwh].[brains_users] (
        [brain_id] UNIQUEIDENTIFIER,
        [user_id] UNIQUEIDENTIFIER,
        [rights] NVARCHAR(255),
        [default_brain] BIT,
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
        CONSTRAINT [PK_brains_users] PRIMARY KEY ([brain_id], [user_id])
    )
    PRINT 'Created table: dwh.brains_users'
END
ELSE
    PRINT 'Table dwh.brains_users already exists'
GO

-- User daily usage table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'user_daily_usage')
BEGIN
    CREATE TABLE [dwh].[user_daily_usage] (
        [user_id] UNIQUEIDENTIFIER,
        [email] NVARCHAR(255),
        [date] NVARCHAR(10),
        [daily_requests_count] INT,
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
        CONSTRAINT [PK_user_daily_usage] PRIMARY KEY ([user_id], [date])
    )
    PRINT 'Created table: dwh.user_daily_usage'
END
ELSE
    PRINT 'Table dwh.user_daily_usage already exists'
GO

-- Chats table (allowing NULL user_id for Zalo chats)
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'chats')
BEGIN
    CREATE TABLE [dwh].[chats] (
        [chat_id] UNIQUEIDENTIFIER PRIMARY KEY,
        [user_id] UNIQUEIDENTIFIER NULL, -- Allow NULL for Zalo chats
        [creation_time] DATETIME2(7),
        [chat_name] NVARCHAR(255),
        [zalo_user_id] NVARCHAR(255),
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: dwh.chats'
END
ELSE
    PRINT 'Table dwh.chats already exists'
GO

-- Chat history table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'chat_history')
BEGIN
    CREATE TABLE [dwh].[chat_history] (
        [message_id] UNIQUEIDENTIFIER PRIMARY KEY,
        [chat_id] UNIQUEIDENTIFIER NOT NULL,
        [user_message] NVARCHAR(MAX),
        [assistant] NVARCHAR(MAX),
        [message_time] DATETIME2(7),
        [brain_id] UNIQUEIDENTIFIER,
        [prompt_id] UNIQUEIDENTIFIER,
        [metadata] NVARCHAR(MAX),
        [thumbs] NVARCHAR(50),
        [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
    )
    PRINT 'Created table: dwh.chat_history'
END
ELSE
    PRINT 'Table dwh.chat_history already exists'
GO

PRINT 'Minimal schema creation completed successfully!' 
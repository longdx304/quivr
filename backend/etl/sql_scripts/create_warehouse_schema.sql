-- =============================================
-- Quivr Data Warehouse Schema for SQL Server
-- =============================================

USE [DataWarehouse]
GO

-- Create schemas
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dwh')
    EXEC('CREATE SCHEMA [dwh]')
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'etl')
    EXEC('CREATE SCHEMA [etl]')
GO

-- =============================================
-- ETL Control Tables
-- =============================================

-- ETL control table for tracking sync status
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='etl_control' AND xtype='U')
CREATE TABLE [etl].[etl_control] (
    [table_name] NVARCHAR(100) PRIMARY KEY,
    [last_sync_timestamp] DATETIME2(7),
    [sync_status] NVARCHAR(20) DEFAULT 'ACTIVE',
    [record_count] BIGINT DEFAULT 0,
    [created_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    [updated_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- ETL execution log
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='etl_execution_log' AND xtype='U')
CREATE TABLE [etl].[etl_execution_log] (
    [id] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [execution_id] UNIQUEIDENTIFIER DEFAULT NEWID(),
    [table_name] NVARCHAR(100),
    [start_time] DATETIME2(7) DEFAULT GETUTCDATE(),
    [end_time] DATETIME2(7),
    [status] NVARCHAR(20), -- SUCCESS, FAILED, RUNNING
    [records_processed] BIGINT DEFAULT 0,
    [error_message] NVARCHAR(MAX),
    [execution_duration_seconds] INT
)
GO

-- =============================================
-- Main Data Warehouse Tables
-- =============================================

-- Users table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE [dwh].[users] (
    [id] UNIQUEIDENTIFIER PRIMARY KEY,
    [email] NVARCHAR(255),
    [created_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    [updated_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Brains table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='brains' AND xtype='U')
CREATE TABLE [dwh].[brains] (
    [brain_id] UNIQUEIDENTIFIER PRIMARY KEY,
    [name] NVARCHAR(255),
    [status] NVARCHAR(50),
    [model] NVARCHAR(100),
    [max_tokens] INT,
    [temperature] FLOAT,
    [description] NVARCHAR(MAX),
    [prompt_id] UNIQUEIDENTIFIER,
    [retrieval_algorithm] NVARCHAR(100),
    [last_update] DATETIME2(7),
    [brain_type] NVARCHAR(20), -- doc, api, composite
    [created_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Chats table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chats' AND xtype='U')
CREATE TABLE [dwh].[chats] (
    [chat_id] UNIQUEIDENTIFIER PRIMARY KEY,
    [user_id] UNIQUEIDENTIFIER,
    [creation_time] DATETIME2(7),
    [chat_name] NVARCHAR(255),
    [history] NVARCHAR(MAX), -- JSON as NVARCHAR
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Chat history table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chat_history' AND xtype='U')
CREATE TABLE [dwh].[chat_history] (
    [message_id] UNIQUEIDENTIFIER PRIMARY KEY,
    [chat_id] UNIQUEIDENTIFIER NOT NULL,
    [user_message] NVARCHAR(MAX),
    [assistant] NVARCHAR(MAX),
    [message_time] DATETIME2(7),
    [brain_id] UNIQUEIDENTIFIER,
    [prompt_id] UNIQUEIDENTIFIER,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Vectors table (for embeddings metadata)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='vectors' AND xtype='U')
CREATE TABLE [dwh].[vectors] (
    [id] UNIQUEIDENTIFIER PRIMARY KEY,
    [content] NVARCHAR(MAX),
    [file_sha1] NVARCHAR(64),
    [metadata] NVARCHAR(MAX), -- JSON as NVARCHAR
    [embedding_model] NVARCHAR(100),
    [embedding_dimensions] INT,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Knowledge table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='knowledge' AND xtype='U')
CREATE TABLE [dwh].[knowledge] (
    [id] UNIQUEIDENTIFIER PRIMARY KEY,
    [file_name] NVARCHAR(500),
    [url] NVARCHAR(1000),
    [brain_id] UNIQUEIDENTIFIER NOT NULL,
    [extension] NVARCHAR(10) NOT NULL,
    [file_size] BIGINT,
    [created_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- API Keys table (excluding sensitive data)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='api_keys' AND xtype='U')
CREATE TABLE [dwh].[api_keys] (
    [key_id] UNIQUEIDENTIFIER PRIMARY KEY,
    [user_id] UNIQUEIDENTIFIER,
    [name] NVARCHAR(255),
    [days] INT,
    [only_chat] BIT,
    [creation_time] DATETIME2(7),
    [deleted_time] DATETIME2(7),
    [is_active] BIT,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- User settings table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_settings' AND xtype='U')
CREATE TABLE [dwh].[user_settings] (
    [user_id] UNIQUEIDENTIFIER PRIMARY KEY,
    [models] NVARCHAR(MAX), -- JSON as NVARCHAR
    [daily_chat_credit] INT,
    [max_brains] INT,
    [max_brain_size] INT,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Notifications table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='notifications' AND xtype='U')
CREATE TABLE [dwh].[notifications] (
    [id] UNIQUEIDENTIFIER PRIMARY KEY,
    [datetime] DATETIME2(7),
    [chat_id] UNIQUEIDENTIFIER,
    [message] NVARCHAR(MAX),
    [action] NVARCHAR(255),
    [status] NVARCHAR(255),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Prompts table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='prompts' AND xtype='U')
CREATE TABLE [dwh].[prompts] (
    [id] UNIQUEIDENTIFIER PRIMARY KEY,
    [title] NVARCHAR(255),
    [content] NVARCHAR(MAX),
    [status] NVARCHAR(255),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE()
)
GO

-- Brains users relationship table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='brains_users' AND xtype='U')
CREATE TABLE [dwh].[brains_users] (
    [brain_id] UNIQUEIDENTIFIER,
    [user_id] UNIQUEIDENTIFIER,
    [rights] NVARCHAR(255),
    [default_brain] BIT,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    CONSTRAINT [PK_brains_users] PRIMARY KEY ([brain_id], [user_id])
)
GO

-- Brains vectors relationship table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='brains_vectors' AND xtype='U')
CREATE TABLE [dwh].[brains_vectors] (
    [brain_id] UNIQUEIDENTIFIER,
    [vector_id] UNIQUEIDENTIFIER,
    [rights] NVARCHAR(255),
    [file_sha1] NVARCHAR(64),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    CONSTRAINT [PK_brains_vectors] PRIMARY KEY ([brain_id], [vector_id])
)
GO

-- Knowledge vectors relationship table  
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='knowledge_vectors' AND xtype='U')
CREATE TABLE [dwh].[knowledge_vectors] (
    [knowledge_id] UNIQUEIDENTIFIER,
    [vector_id] UNIQUEIDENTIFIER,
    [embedding_model] NVARCHAR(100),
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    CONSTRAINT [PK_knowledge_vectors] PRIMARY KEY ([knowledge_id], [vector_id], [embedding_model])
)
GO

-- User daily usage table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_daily_usage' AND xtype='U')
CREATE TABLE [dwh].[user_daily_usage] (
    [user_id] UNIQUEIDENTIFIER,
    [email] NVARCHAR(255),
    [date] NVARCHAR(10), -- Keeping as NVARCHAR to match source
    [daily_requests_count] INT,
    [etl_inserted_at] DATETIME2(7) DEFAULT GETUTCDATE(),
    CONSTRAINT [PK_user_daily_usage] PRIMARY KEY ([user_id], [date])
)
GO

-- =============================================
-- Performance Indexes
-- =============================================

-- Users indexes
CREATE NONCLUSTERED INDEX [IX_users_email] ON [dwh].[users] ([email])
CREATE NONCLUSTERED INDEX [IX_users_etl_inserted] ON [dwh].[users] ([etl_inserted_at])

-- Brains indexes
CREATE NONCLUSTERED INDEX [IX_brains_name] ON [dwh].[brains] ([name])
CREATE NONCLUSTERED INDEX [IX_brains_type] ON [dwh].[brains] ([brain_type])
CREATE NONCLUSTERED INDEX [IX_brains_last_update] ON [dwh].[brains] ([last_update])

-- Chats indexes
CREATE NONCLUSTERED INDEX [IX_chats_user_id] ON [dwh].[chats] ([user_id])
CREATE NONCLUSTERED INDEX [IX_chats_creation_time] ON [dwh].[chats] ([creation_time])

-- Chat history indexes
CREATE NONCLUSTERED INDEX [IX_chat_history_chat_id] ON [dwh].[chat_history] ([chat_id])
CREATE NONCLUSTERED INDEX [IX_chat_history_message_time] ON [dwh].[chat_history] ([message_time])
CREATE NONCLUSTERED INDEX [IX_chat_history_brain_id] ON [dwh].[chat_history] ([brain_id])

-- Vectors indexes
CREATE NONCLUSTERED INDEX [IX_vectors_file_sha1] ON [dwh].[vectors] ([file_sha1])

-- Knowledge indexes
CREATE NONCLUSTERED INDEX [IX_knowledge_brain_id] ON [dwh].[knowledge] ([brain_id])
CREATE NONCLUSTERED INDEX [IX_knowledge_extension] ON [dwh].[knowledge] ([extension])

-- Notifications indexes
CREATE NONCLUSTERED INDEX [IX_notifications_datetime] ON [dwh].[notifications] ([datetime])
CREATE NONCLUSTERED INDEX [IX_notifications_chat_id] ON [dwh].[notifications] ([chat_id])

-- User daily usage indexes
CREATE NONCLUSTERED INDEX [IX_user_daily_usage_date] ON [dwh].[user_daily_usage] ([date])
CREATE NONCLUSTERED INDEX [IX_user_daily_usage_email] ON [dwh].[user_daily_usage] ([email])

-- =============================================
-- Views for Analysis
-- =============================================

-- Daily chat activity view
CREATE OR ALTER VIEW [dwh].[v_daily_chat_activity] AS
SELECT 
    CAST([message_time] AS DATE) as [date],
    COUNT(*) as [total_messages],
    COUNT(DISTINCT [chat_id]) as [unique_chats],
    COUNT(DISTINCT ch.[user_id]) as [unique_users]
FROM [dwh].[chat_history] h
JOIN [dwh].[chats] ch ON h.[chat_id] = ch.[chat_id]
WHERE [message_time] IS NOT NULL
GROUP BY CAST([message_time] AS DATE)
GO

-- Brain usage summary view
CREATE OR ALTER VIEW [dwh].[v_brain_usage_summary] AS
SELECT 
    b.[brain_id],
    b.[name] as [brain_name],
    b.[brain_type],
    COUNT(DISTINCT bu.[user_id]) as [user_count],
    COUNT(DISTINCT ch.[message_id]) as [message_count],
    MAX(ch.[message_time]) as [last_used]
FROM [dwh].[brains] b
LEFT JOIN [dwh].[brains_users] bu ON b.[brain_id] = bu.[brain_id]
LEFT JOIN [dwh].[chat_history] ch ON b.[brain_id] = ch.[brain_id]
GROUP BY b.[brain_id], b.[name], b.[brain_type]
GO

-- User activity summary view
CREATE OR ALTER VIEW [dwh].[v_user_activity_summary] AS
SELECT 
    u.[id] as [user_id],
    u.[email],
    COUNT(DISTINCT c.[chat_id]) as [total_chats],
    COUNT(DISTINCT ch.[message_id]) as [total_messages],
    COUNT(DISTINCT bu.[brain_id]) as [brain_count],
    MAX(ch.[message_time]) as [last_activity]
FROM [dwh].[users] u
LEFT JOIN [dwh].[chats] c ON u.[id] = c.[user_id]
LEFT JOIN [dwh].[chat_history] ch ON c.[chat_id] = ch.[chat_id]
LEFT JOIN [dwh].[brains_users] bu ON u.[id] = bu.[user_id]
GROUP BY u.[id], u.[email]
GO

PRINT 'Data Warehouse schema created successfully!'
GO 
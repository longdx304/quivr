-- =============================================
-- Drop all existing tables to recreate with new schema  
-- =============================================

-- Drop data warehouse tables if they exist
IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'chat_history')
    DROP TABLE [dwh].[chat_history]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'chats')
    DROP TABLE [dwh].[chats]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'user_daily_usage')
    DROP TABLE [dwh].[user_daily_usage]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'brains_users')
    DROP TABLE [dwh].[brains_users]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'knowledge')
    DROP TABLE [dwh].[knowledge]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'brains')
    DROP TABLE [dwh].[brains]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'users')
    DROP TABLE [dwh].[users]

-- Drop ETL control tables if they exist
IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'etl' AND TABLE_NAME = 'etl_execution_log')
    DROP TABLE [etl].[etl_execution_log]

IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'etl' AND TABLE_NAME = 'etl_control')
    DROP TABLE [etl].[etl_control]

PRINT 'All tables dropped successfully!' 
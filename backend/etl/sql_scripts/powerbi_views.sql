-- =============================================
-- PowerBI Views và Stored Procedures
-- Tạo các view để trực quan hóa dữ liệu Quivr
-- =============================================

USE [DataWarehouse]
GO

-- =============================================
-- 1. VIEWS CHO DASHBOARD TỔNG QUAN
-- =============================================

-- View tổng quan hệ thống
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_system_overview')
    DROP VIEW [dwh].[v_system_overview]
GO

CREATE VIEW [dwh].[v_system_overview] AS
SELECT 
    (SELECT COUNT(*) FROM dwh.users) AS total_users,
    (SELECT COUNT(*) FROM dwh.brains) AS total_brains,
    (SELECT COUNT(*) FROM dwh.knowledge) AS total_documents,
    (SELECT COUNT(*) FROM dwh.chats) AS total_chats,
    (SELECT COUNT(*) FROM dwh.chat_history) AS total_messages,
    (SELECT COUNT(DISTINCT user_id) FROM dwh.user_daily_usage WHERE date = CONVERT(VARCHAR(10), GETDATE(), 120)) AS daily_active_users,
    (SELECT AVG(CAST(daily_requests_count AS FLOAT)) FROM dwh.user_daily_usage) AS avg_daily_requests
GO

-- View thống kê người dùng theo thời gian
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_user_growth')
    DROP VIEW [dwh].[v_user_growth]
GO

CREATE VIEW [dwh].[v_user_growth] AS
SELECT 
    CONVERT(DATE, etl_inserted_at) AS registration_date,
    COUNT(*) AS new_users,
    SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, etl_inserted_at)) AS cumulative_users
FROM dwh.users
WHERE etl_inserted_at IS NOT NULL
GROUP BY CONVERT(DATE, etl_inserted_at)
GO

-- =============================================
-- 2. VIEWS CHO DASHBOARD HOẠT ĐỘNG NGƯỜI DÙNG
-- =============================================

-- View hoạt động người dùng hàng ngày
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_daily_user_activity')
    DROP VIEW [dwh].[v_daily_user_activity]
GO

CREATE VIEW [dwh].[v_daily_user_activity] AS
SELECT 
    udu.date,
    COUNT(DISTINCT udu.user_id) AS active_users,
    SUM(udu.daily_requests_count) AS total_requests,
    AVG(CAST(udu.daily_requests_count AS FLOAT)) AS avg_requests_per_user,
    COUNT(DISTINCT c.chat_id) AS total_chats,
    COUNT(DISTINCT ch.message_id) AS total_messages
FROM dwh.user_daily_usage udu
LEFT JOIN dwh.chats c ON udu.user_id = c.user_id 
    AND CONVERT(DATE, c.creation_time) = udu.date
LEFT JOIN dwh.chat_history ch ON c.chat_id = ch.chat_id
GROUP BY udu.date
GO

-- View top users theo hoạt động
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_top_active_users')
    DROP VIEW [dwh].[v_top_active_users]
GO

CREATE VIEW [dwh].[v_top_active_users] AS
SELECT TOP 50
    u.email,
    COUNT(DISTINCT c.chat_id) AS total_chats,
    COUNT(DISTINCT ch.message_id) AS total_messages,
    SUM(udu.daily_requests_count) AS total_requests,
    MAX(udu.date) AS last_activity_date
FROM dwh.users u
LEFT JOIN dwh.chats c ON u.id = c.user_id
LEFT JOIN dwh.chat_history ch ON c.chat_id = ch.chat_id
LEFT JOIN dwh.user_daily_usage udu ON u.id = udu.user_id
GROUP BY u.id, u.email
ORDER BY total_requests DESC
GO

-- =============================================
-- 3. VIEWS CHO DASHBOARD BRAIN PERFORMANCE
-- =============================================

-- View hiệu suất brain
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_brain_performance')
    DROP VIEW [dwh].[v_brain_performance]
GO

CREATE VIEW [dwh].[v_brain_performance] AS
SELECT 
    b.brain_id,
    b.name AS brain_name,
    b.status,
    b.model,
    COUNT(DISTINCT c.chat_id) AS total_chats,
    COUNT(DISTINCT ch.message_id) AS total_messages,
    COUNT(DISTINCT k.id) AS total_documents,
    COUNT(DISTINCT bu.user_id) AS total_users,
    MAX(c.creation_time) AS last_used,
    CONVERT(DATE, b.last_update) AS created_date
FROM dwh.brains b
LEFT JOIN dwh.chats c ON b.brain_id = c.brain_id
LEFT JOIN dwh.chat_history ch ON c.chat_id = ch.chat_id
LEFT JOIN dwh.knowledge k ON b.brain_id = k.brain_id
LEFT JOIN dwh.brains_users bu ON b.brain_id = bu.brain_id
GROUP BY b.brain_id, b.name, b.status, b.model, b.last_update
GO

-- View trend tạo brain theo thời gian
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_brain_creation_trend')
    DROP VIEW [dwh].[v_brain_creation_trend]
GO

CREATE VIEW [dwh].[v_brain_creation_trend] AS
SELECT 
    CONVERT(DATE, last_update) AS creation_date,
    COUNT(*) AS new_brains,
    SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, last_update)) AS cumulative_brains
FROM dwh.brains
WHERE last_update IS NOT NULL
GROUP BY CONVERT(DATE, last_update)
GO

-- =============================================
-- 4. VIEWS CHO DASHBOARD KNOWLEDGE BASE
-- =============================================

-- View thống kê knowledge base
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_knowledge_statistics')
    DROP VIEW [dwh].[v_knowledge_statistics]
GO

CREATE VIEW [dwh].[v_knowledge_statistics] AS
SELECT 
    k.extension,
    COUNT(*) AS document_count,
    SUM(CAST(k.file_size AS BIGINT)) AS total_size_bytes,
    AVG(CAST(k.file_size AS FLOAT)) AS avg_size_bytes,
    COUNT(DISTINCT k.brain_id) AS brains_using_extension,
    COUNT(DISTINCT k.user_id) AS users_uploading_extension
FROM dwh.knowledge k
WHERE k.extension IS NOT NULL
GROUP BY k.extension
GO

-- View documents per brain
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_documents_per_brain')
    DROP VIEW [dwh].[v_documents_per_brain]
GO

CREATE VIEW [dwh].[v_documents_per_brain] AS
SELECT 
    b.name AS brain_name,
    COUNT(k.id) AS document_count,
    SUM(CAST(k.file_size AS BIGINT)) AS total_size_bytes,
    COUNT(DISTINCT k.extension) AS file_types_count,
    MAX(k.created_at) AS last_document_added
FROM dwh.brains b
LEFT JOIN dwh.knowledge k ON b.brain_id = k.brain_id
GROUP BY b.brain_id, b.name
GO

-- =============================================
-- 5. VIEWS CHO DASHBOARD CHAT ANALYTICS
-- =============================================

-- View thống kê chat theo thời gian
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_chat_activity_trend')
    DROP VIEW [dwh].[v_chat_activity_trend]
GO

CREATE VIEW [dwh].[v_chat_activity_trend] AS
SELECT 
    CONVERT(DATE, c.creation_time) AS chat_date,
    COUNT(DISTINCT c.chat_id) AS new_chats,
    COUNT(DISTINCT ch.message_id) AS total_messages,
    COUNT(DISTINCT c.user_id) AS unique_users,
    AVG(CAST(ch.message_time - c.creation_time AS FLOAT)) AS avg_chat_duration_minutes
FROM dwh.chats c
LEFT JOIN dwh.chat_history ch ON c.chat_id = ch.chat_id
WHERE c.creation_time IS NOT NULL
GROUP BY CONVERT(DATE, c.creation_time)
GO

-- View chat performance theo brain
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_chat_performance_by_brain')
    DROP VIEW [dwh].[v_chat_performance_by_brain]
GO

CREATE VIEW [dwh].[v_chat_performance_by_brain] AS
SELECT 
    b.name AS brain_name,
    COUNT(DISTINCT c.chat_id) AS total_chats,
    COUNT(DISTINCT ch.message_id) AS total_messages,
    COUNT(DISTINCT c.user_id) AS unique_users,
    AVG(CAST(ch.message_time - c.creation_time AS FLOAT)) AS avg_chat_duration_minutes,
    COUNT(CASE WHEN ch.thumbs = 1 THEN 1 END) AS positive_feedback,
    COUNT(CASE WHEN ch.thumbs = 0 THEN 1 END) AS negative_feedback
FROM dwh.brains b
LEFT JOIN dwh.chats c ON b.brain_id = c.brain_id
LEFT JOIN dwh.chat_history ch ON c.chat_id = ch.chat_id
GROUP BY b.brain_id, b.name
GO

-- =============================================
-- 6. STORED PROCEDURES CHO POWERBI
-- =============================================

-- Stored procedure để lấy dữ liệu cho KPI dashboard
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_get_kpi_data')
    DROP PROCEDURE [dwh].[sp_get_kpi_data]
GO

CREATE PROCEDURE [dwh].[sp_get_kpi_data]
    @date_from DATE = NULL,
    @date_to DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @date_from IS NULL SET @date_from = DATEADD(DAY, -30, GETDATE())
    IF @date_to IS NULL SET @date_to = GETDATE()
    
    SELECT 
        'Total Users' AS metric_name,
        COUNT(*) AS metric_value,
        'Count' AS metric_type
    FROM dwh.users
    WHERE CONVERT(DATE, etl_inserted_at) BETWEEN @date_from AND @date_to
    
    UNION ALL
    
    SELECT 
        'Total Brains' AS metric_name,
        COUNT(*) AS metric_value,
        'Count' AS metric_type
    FROM dwh.brains
    WHERE CONVERT(DATE, last_update) BETWEEN @date_from AND @date_to
    
    UNION ALL
    
    SELECT 
        'Total Documents' AS metric_name,
        COUNT(*) AS metric_value,
        'Count' AS metric_type
    FROM dwh.knowledge
    WHERE CONVERT(DATE, created_at) BETWEEN @date_from AND @date_to
    
    UNION ALL
    
    SELECT 
        'Total Chats' AS metric_name,
        COUNT(*) AS metric_value,
        'Count' AS metric_type
    FROM dwh.chats
    WHERE CONVERT(DATE, creation_time) BETWEEN @date_from AND @date_to
    
    UNION ALL
    
    SELECT 
        'Daily Active Users' AS metric_name,
        COUNT(DISTINCT user_id) AS metric_value,
        'Count' AS metric_type
    FROM dwh.user_daily_usage
    WHERE date BETWEEN CONVERT(VARCHAR(10), @date_from, 120) AND CONVERT(VARCHAR(10), @date_to, 120)
END
GO

-- Stored procedure để lấy trend data
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_get_trend_data')
    DROP PROCEDURE [dwh].[sp_get_trend_data]
GO

CREATE PROCEDURE [dwh].[sp_get_trend_data]
    @trend_type VARCHAR(50), -- 'users', 'brains', 'chats', 'documents'
    @date_from DATE = NULL,
    @date_to DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @date_from IS NULL SET @date_from = DATEADD(DAY, -90, GETDATE())
    IF @date_to IS NULL SET @date_to = GETDATE()
    
    IF @trend_type = 'users'
    BEGIN
        SELECT 
            CONVERT(DATE, etl_inserted_at) AS date,
            COUNT(*) AS new_count,
            SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, etl_inserted_at)) AS cumulative_count
        FROM dwh.users
        WHERE CONVERT(DATE, etl_inserted_at) BETWEEN @date_from AND @date_to
        GROUP BY CONVERT(DATE, etl_inserted_at)
        ORDER BY date
    END
    ELSE IF @trend_type = 'brains'
    BEGIN
        SELECT 
            CONVERT(DATE, last_update) AS date,
            COUNT(*) AS new_count,
            SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, last_update)) AS cumulative_count
        FROM dwh.brains
        WHERE CONVERT(DATE, last_update) BETWEEN @date_from AND @date_to
        GROUP BY CONVERT(DATE, last_update)
        ORDER BY date
    END
    ELSE IF @trend_type = 'chats'
    BEGIN
        SELECT 
            CONVERT(DATE, creation_time) AS date,
            COUNT(*) AS new_count,
            SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, creation_time)) AS cumulative_count
        FROM dwh.chats
        WHERE CONVERT(DATE, creation_time) BETWEEN @date_from AND @date_to
        GROUP BY CONVERT(DATE, creation_time)
        ORDER BY date
    END
    ELSE IF @trend_type = 'documents'
    BEGIN
        SELECT 
            CONVERT(DATE, created_at) AS date,
            COUNT(*) AS new_count,
            SUM(COUNT(*)) OVER (ORDER BY CONVERT(DATE, created_at)) AS cumulative_count
        FROM dwh.knowledge
        WHERE CONVERT(DATE, created_at) BETWEEN @date_from AND @date_to
        GROUP BY CONVERT(DATE, created_at)
        ORDER BY date
    END
END
GO

-- =============================================
-- 7. INDEXES CHO PERFORMANCE
-- =============================================

-- Indexes cho các cột thường được query
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_etl_inserted_at')
    CREATE INDEX IX_users_etl_inserted_at ON dwh.users(etl_inserted_at)
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_brains_last_update')
    CREATE INDEX IX_brains_last_update ON dwh.brains(last_update)
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_chats_creation_time')
    CREATE INDEX IX_chats_creation_time ON dwh.chats(creation_time)
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_knowledge_created_at')
    CREATE INDEX IX_knowledge_created_at ON dwh.knowledge(created_at)
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_user_daily_usage_date')
    CREATE INDEX IX_user_daily_usage_date ON dwh.user_daily_usage(date)
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_chat_history_message_time')
    CREATE INDEX IX_chat_history_message_time ON dwh.chat_history(message_time)
GO

-- =============================================
-- 8. TEST QUERIES
-- =============================================

-- Test các views đã tạo
PRINT 'Testing PowerBI Views...'

-- Test system overview
SELECT TOP 5 * FROM dwh.v_system_overview

-- Test user growth
SELECT TOP 10 * FROM dwh.v_user_growth ORDER BY registration_date DESC

-- Test daily activity
SELECT TOP 10 * FROM dwh.v_daily_user_activity ORDER BY date DESC

-- Test brain performance
SELECT TOP 10 * FROM dwh.v_brain_performance ORDER BY total_chats DESC

-- Test stored procedures
EXEC dwh.sp_get_kpi_data @date_from = '2024-01-01', @date_to = '2024-12-31'
EXEC dwh.sp_get_trend_data @trend_type = 'users', @date_from = '2024-01-01', @date_to = '2024-12-31'

PRINT 'PowerBI Views and Stored Procedures created successfully!'
GO 
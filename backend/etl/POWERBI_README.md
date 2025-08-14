# 🚀 Quivr PowerBI Analytics Setup

Hướng dẫn hoàn chỉnh để thiết lập trực quan hóa dữ liệu Quivr trên PowerBI.

## 📋 Tổng quan

Hệ thống ETL của Quivr đã được thiết kế để đồng bộ dữ liệu từ Supabase sang SQL Server Data Warehouse, sẵn sàng cho việc phân tích và trực quan hóa trên PowerBI.

## 🏗️ Kiến trúc

```
[Quivr App] → [Supabase] → [ETL Pipeline] → [SQL Server DWH] → [PowerBI]
```

## 🚀 Quick Start

### Bước 1: Khởi động ETL Pipeline

```bash
# Di chuyển vào thư mục ETL
cd backend/etl

# Khởi động SQL Server và ETL
docker compose -f docker-compose.etl.yml build --no-cache
docker compose -f docker-compose.etl.yml up -d

# Kiểm tra trạng thái
docker compose -f docker-compose.etl.yml ps
```

### Bước 2: Tạo PowerBI Views

```powershell
# Chạy script setup PowerBI
.\powerbi_setup.ps1
# với commandline
powershell -ExecutionPolicy Bypass -File powerbi_setup.ps1
```

### Bước 3: Kết nối PowerBI Desktop

1. Mở PowerBI Desktop
2. **Get Data** → **SQL Server**
3. Nhập thông tin kết nối:
   - **Server**: `localhost,1433`
   - **Database**: `DataWarehouse`
   - **Authentication**: Database
   - **Username**: `sa`
   - **Password**: `YourPassword123!`

## 📊 Các Dashboard có sẵn

### 1. Dashboard Tổng quan hệ thống

- **Metrics**: Tổng số users, brains, documents, chats
- **Views**: `dwh.v_system_overview`
- **Visualizations**: Cards, line charts, pie charts

### 2. Dashboard Hoạt động người dùng

- **Metrics**: DAU, average requests, top users
- **Views**: `dwh.v_daily_user_activity`, `dwh.v_top_active_users`
- **Visualizations**: Line charts, bar charts, heatmaps

### 3. Dashboard Brain Performance

- **Metrics**: Most used brains, creation trends, knowledge per brain
- **Views**: `dwh.v_brain_performance`, `dwh.v_brain_creation_trend`
- **Visualizations**: Bar charts, line charts, scatter plots

### 4. Dashboard Knowledge Base

- **Metrics**: Documents by type, size statistics, upload trends
- **Views**: `dwh.v_knowledge_statistics`, `dwh.v_documents_per_brain`
- **Visualizations**: Pie charts, bar charts, tables

### 5. Dashboard Chat Analytics

- **Metrics**: Chat activity, message volume, user engagement
- **Views**: `dwh.v_chat_activity_trend`, `dwh.v_chat_performance_by_brain`
- **Visualizations**: Line charts, area charts, tables

## 🔧 Cấu hình chi tiết

### SQL Server Connection

```sql
-- Test connection
sqlcmd -S localhost,1433 -U sa -P 'YourPassword123!' -Q "SELECT @@VERSION"

-- Check data
SELECT COUNT(*) FROM dwh.users;
SELECT COUNT(*) FROM dwh.brains;
SELECT COUNT(*) FROM dwh.chats;
```

### PowerBI Views

Các view đã được tạo sẵn:

```sql
-- System overview
SELECT * FROM dwh.v_system_overview

-- User growth trend
SELECT * FROM dwh.v_user_growth ORDER BY registration_date DESC

-- Daily activity
SELECT * FROM dwh.v_daily_user_activity ORDER BY date DESC

-- Brain performance
SELECT * FROM dwh.v_brain_performance ORDER BY total_chats DESC
```

### Stored Procedures

```sql
-- KPI data
EXEC dwh.sp_get_kpi_data @date_from = '2024-01-01', @date_to = '2024-12-31'

-- Trend data
EXEC dwh.sp_get_trend_data @trend_type = 'users', @date_from = '2024-01-01', @date_to = '2024-12-31'
```

## 📈 DAX Measures mẫu

### KPI Measures

```dax
// Total Users
Total Users = COUNTROWS(Users)

// Total Brains
Total Brains = COUNTROWS(Brains)

// Daily Active Users
Daily Active Users =
CALCULATE(
    DISTINCTCOUNT(User_Daily_Usage[user_id]),
    User_Daily_Usage[date] = TODAY()
)

// Average Daily Requests
Average Daily Requests =
AVERAGE(User_Daily_Usage[daily_requests_count])
```

### Trend Measures

```dax
// User Growth Trend
User Growth Trend =
CALCULATE(
    COUNTROWS(Users),
    DATESYTD(Users[etl_inserted_at])
)

// Chat Activity Trend
Chat Activity Trend =
CALCULATE(
    COUNTROWS(Chats),
    DATESYTD(Chats[Creation_Date])
)
```

### Performance Measures

```dax
// Brain Usage Rate
Brain Usage Rate =
DIVIDE(
    COUNTROWS(RELATEDTABLE(Chats)),
    COUNTROWS(Brains),
    0
)

// User Engagement Score
User Engagement Score =
VAR UserChats = COUNTROWS(RELATEDTABLE(Chats))
VAR UserUsage = SUM(RELATEDTABLE(User_Daily_Usage)[daily_requests_count])
RETURN
    UserChats * 0.6 + UserUsage * 0.4
```

## 🔄 Tự động hóa Refresh

### Cấu hình Schedule Refresh

1. **Publish** report lên PowerBI Service
2. Cấu hình **Schedule refresh**:
   - **Frequency**: Daily
   - **Time**: 3:00 AM (sau khi ETL chạy xong)
   - **Gateway**: Cấu hình gateway nếu cần

### Incremental Refresh

```dax
// Incremental refresh policy
Incremental Refresh =
CALCULATE(
    COUNTROWS(Chats),
    Chats[Creation_Date] >= TODAY() - 7
)
```

## 🛠️ Troubleshooting

### Kết nối SQL Server thất bại

```bash
# Kiểm tra SQL Server đang chạy
docker compose -f docker-compose.etl.yml ps

# Kiểm tra logs
docker compose -f docker-compose.etl.yml logs sqlserver

# Test kết nối
sqlcmd -S localhost,1433 -U sa -P 'YourPassword123!'
```

### Dữ liệu không hiển thị

```sql
-- Kiểm tra ETL logs
SELECT TOP 10 * FROM etl.etl_execution_log ORDER BY start_time DESC

-- Kiểm tra dữ liệu
SELECT COUNT(*) FROM dwh.users;
SELECT COUNT(*) FROM dwh.brains;
SELECT COUNT(*) FROM dwh.chats;

-- Kiểm tra views
SELECT * FROM dwh.v_system_overview
```

### Performance issues

```sql
-- Kiểm tra indexes
SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID('dwh.chats')

-- Tạo indexes nếu cần
CREATE INDEX IX_chats_creation_time ON dwh.chats(creation_time)
CREATE INDEX IX_user_daily_usage_date ON dwh.user_daily_usage(date)
```

## 📁 File Structure

```
backend/etl/
├── powerbi_setup.ps1               # Script setup PowerBI (gộp tất cả chức năng)
├── sql_scripts/
│   ├── powerbi_views.sql           # Views và stored procedures
│   └── create_minimal_schema.sql   # Schema cơ bản
├── powerbi_setup_guide.md          # Hướng dẫn chi tiết
└── POWERBI_README.md               # File này
```

## 🎯 Best Practices

### 1. Data Model Design

- Sử dụng relationships đúng cách
- Tạo calculated columns cho date fields
- Sử dụng measures thay vì calculated columns cho aggregations

### 2. Performance Optimization

- Sử dụng DirectQuery cho dữ liệu lớn
- Tạo indexes cho các cột thường query
- Sử dụng incremental refresh

### 3. Security

- Sử dụng Row Level Security (RLS) nếu cần
- Cấu hình proper permissions
- Audit access logs

### 4. Monitoring

- Monitor ETL execution logs
- Track PowerBI refresh performance
- Set up alerts cho failures

## 📞 Hỗ trợ

### Logs và Monitoring

```bash
# ETL logs
docker compose -f docker-compose.etl.yml logs etl-app

# SQL Server logs
docker compose -f docker-compose.etl.yml logs sqlserver

# Health check
docker exec -it etl-etl-app-1 python -c "
from utils import get_database_health
import json
print(json.dumps(get_database_health(), indent=2))
"
```

### Common Commands

```bash
# Restart ETL
docker compose -f docker-compose.etl.yml restart etl-app

# Check data sync
docker exec -it etl-etl-app-1 python etl_main.py --mode incremental

# Backup SQL Server
docker exec -it etl-sqlserver-1 /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U sa -P 'YourPassword123!' \
  -Q "BACKUP DATABASE DataWarehouse TO DISK = '/var/opt/mssql/backup/dwh_backup.bak'"
```

## 🚀 Production Deployment

### Checklist

- [ ] Configure proper passwords
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Set up log rotation
- [ ] Configure SSL/TLS
- [ ] Set up network security
- [ ] Test disaster recovery

### Scaling Considerations

- Use SQL Server Standard/Enterprise
- Consider partitioning large tables
- Implement proper indexing strategy
- Monitor resource usage
- Set up read replicas for analytics

---

**Lưu ý**: Đảm bảo ETL pipeline đang chạy và sync dữ liệu thường xuyên để có dữ liệu mới nhất trong PowerBI.

**Hỗ trợ**: Nếu gặp vấn đề, kiểm tra logs và documentation trong thư mục `backend/etl/`.

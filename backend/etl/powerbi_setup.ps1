# =============================================
# PowerBI Setup Script for Quivr ETL
# Gộp tất cả chức năng vào 1 file
# =============================================

param(
    [string]$SqlServerHost = "localhost",
    [int]$SqlServerPort = 1433,
    [string]$Database = "DataWarehouse",
    [string]$Username = "sa",
    [string]$Password = "YourPassword123!",
    [switch]$CreateViews = $true
)

Write-Host "Quivr PowerBI Setup Script" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# =============================================
# 1. Kiểm tra ETL và SQL Server
# =============================================

Write-Host "`nChecking ETL and SQL Server status..." -ForegroundColor Yellow

try {
    $dockerStatus = docker compose -f docker-compose.etl.yml ps --format json | ConvertFrom-Json
    
    $sqlServerRunning = $false
    $etlRunning = $false
    
    foreach ($service in $dockerStatus) {
        if ($service.Service -eq "sqlserver" -and $service.Status -like "*Up*") {
            $sqlServerRunning = $true
            Write-Host "SQL Server: Running" -ForegroundColor Green
        }
        if ($service.Service -eq "etl-app" -and $service.Status -like "*Up*") {
            $etlRunning = $true
            Write-Host "ETL App: Running" -ForegroundColor Green
        }
    }
    
    if (-not $sqlServerRunning) {
        Write-Host "SQL Server: Not running" -ForegroundColor Red
    }
    if (-not $etlRunning) {
        Write-Host "ETL App: Not running" -ForegroundColor Red
    }
}
catch {
    Write-Host "Error checking Docker services: $($_.Exception.Message)" -ForegroundColor Red
}

# =============================================
# 2. Tạo PowerBI Views (nếu được yêu cầu)
# =============================================

if ($CreateViews) {
    Write-Host "`nCreating PowerBI Views..." -ForegroundColor Yellow
    
    # Tìm container name
    $containerName = ""
    try {
        $containers = docker ps --format "table {{.Names}}" | Select-String "sqlserver"
        if ($containers) {
            $containerName = $containers[0].ToString().Trim()
        }
    }
    catch {
        Write-Host "Error finding SQL Server container" -ForegroundColor Red
    }
    
    if ($containerName) {
        $sqlFile = "sql_scripts/powerbi_views.sql"
        
        # Copy file SQL vào container
        Write-Host "Copying SQL script to container..." -ForegroundColor Yellow
        docker cp $sqlFile "$containerName`:/tmp/powerbi_views.sql"
        
        # Chạy script SQL
        Write-Host "Running PowerBI Views script..." -ForegroundColor Yellow
        docker exec $containerName /opt/mssql-tools18/bin/sqlcmd -S localhost -U $Username -P $Password -C -i /tmp/powerbi_views.sql
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PowerBI Views created successfully!" -ForegroundColor Green
        } else {
            Write-Host "Error creating PowerBI Views!" -ForegroundColor Red
        }
    } else {
        Write-Host "SQL Server container not found. Please run manually:" -ForegroundColor Yellow
        Write-Host "1. Open SQL Server Management Studio" -ForegroundColor Yellow
        Write-Host "2. Connect to: $SqlServerHost,$SqlServerPort" -ForegroundColor Yellow
        Write-Host "3. Run: sql_scripts/powerbi_views.sql" -ForegroundColor Yellow
    }
}

# =============================================
# 3. Hiển thị thông tin kết nối PowerBI
# =============================================

Write-Host "`nPowerBI Connection Information:" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

$connectionInfo = @"
Server: $SqlServerHost,$SqlServerPort
Database: $Database
Authentication: Database
Username: $Username
Password: $Password

Connection String:
Server=$SqlServerHost,$SqlServerPort;Database=$Database;User Id=$Username;Password=$Password;TrustServerCertificate=true;
"@

Write-Host $connectionInfo -ForegroundColor Cyan

# =============================================
# 4. Chuẩn bị và mở Power BI Data Source (.pbids / .pbit)
# =============================================

try {
    $pbitSrc = Join-Path -Path (Get-Location) -ChildPath "Quivr_Analytics.pbit"
    $pbidsSrc = Join-Path -Path (Get-Location) -ChildPath "Quivr_Analytics.pbids"

    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $desktopPbit = Join-Path -Path $desktopDir -ChildPath "Quivr_Analytics.pbit"
    $desktopPbids = Join-Path -Path $desktopDir -ChildPath "Quivr_Analytics.pbids"

    $fileToCopy = $null
    $destPath = $null

    if (Test-Path $pbitSrc) {
        $fileToCopy = $pbitSrc
        $destPath = $desktopPbit
        Write-Host "Found Quivr_Analytics.pbit template. Using .pbit." -ForegroundColor Green
    } elseif (Test-Path $pbidsSrc) {
        $fileToCopy = $pbidsSrc
        $destPath = $desktopPbids
        Write-Host "Template (.pbit) not found. Using Quivr_Analytics.pbids as data source." -ForegroundColor Yellow
    }

    if ($fileToCopy) {
        Copy-Item -Path $fileToCopy -Destination $destPath -Force
        Write-Host "Copied to Desktop: $destPath" -ForegroundColor Green

        # Thử mở bằng Power BI Desktop nếu có cài đặt
        $possiblePaths = @(
            "$Env:ProgramFiles\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
            "$Env:ProgramFiles\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_*\PBIDesktop.exe",
            "$Env:LOCALAPPDATA\Microsoft\WindowsApps\PBIDesktop.exe"
        )

        $pbiExe = $possiblePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($pbiExe) {
            Start-Process -FilePath $pbiExe -ArgumentList "`"$destPath`""
            Write-Host "Launching Power BI Desktop with $([System.IO.Path]::GetFileName($destPath))..." -ForegroundColor Green
        } else {
            Write-Host "Power BI Desktop not found in default locations. Open the file manually from Desktop." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Neither Quivr_Analytics.pbit nor Quivr_Analytics.pbids found in the script directory." -ForegroundColor Red
    }
}
catch {
    Write-Host "Failed to prepare/open Power BI file: $($_.Exception.Message)" -ForegroundColor Red
}

# =============================================
# 5. Hiển thị hướng dẫn sử dụng
# =============================================

Write-Host "`nPowerBI Setup Guide:" -ForegroundColor Yellow
Write-Host "===================" -ForegroundColor Yellow

Write-Host @"

## Cách kết nối PowerBI:

1. Mở PowerBI Desktop
2. Get Data → SQL Server
3. Nhập thông tin kết nối như trên

## Tables cần import:
- dwh.users
- dwh.brains  
- dwh.knowledge
- dwh.chats
- dwh.chat_history
- dwh.user_daily_usage
- dwh.brains_users

## Views có sẵn:
- dwh.v_system_overview
- dwh.v_user_growth
- dwh.v_daily_user_activity
- dwh.v_brain_performance
- dwh.v_knowledge_statistics
- dwh.v_chat_activity_trend

## DAX Measures mẫu:
```
Total Users = COUNTROWS(Users)
Total Brains = COUNTROWS(Brains)
Daily Active Users = CALCULATE(DISTINCTCOUNT(User_Daily_Usage[user_id]), User_Daily_Usage[date] = TODAY())
```

"@ -ForegroundColor Cyan

# =============================================
# 6. Summary
# =============================================

Write-Host "`nPowerBI Setup Complete!" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

Write-Host @"

Next Steps:
1. Open PowerBI Desktop
2. Connect using the connection string above
3. Import the recommended tables and views
4. Set up relationships between tables
5. Create your first dashboard

Support:
- Check logs: docker compose -f docker-compose.etl.yml logs etl-app
- Check SQL Server: docker compose -f docker-compose.etl.yml logs sqlserver
- View data: SELECT TOP 10 * FROM dwh.users

"@ -ForegroundColor Cyan

Write-Host "`nHappy visualizing!" -ForegroundColor Green

 
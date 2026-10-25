<#
.SYNOPSIS
    Kiểm tra toàn diện trạng thái hệ thống Quản lý Chi tiêu Cá nhân & Gia đình.
.DESCRIPTION
    Script kiểm tra kết nối Docker Engine, container PostgreSQL 18, Backend liveness/readiness,
    trạng thái frontend Vite, cấu hình URL và Alembic migration revision.
    Tuyệt đối không in mật khẩu hay secrets.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   KIỂM TRA TRẠNG THÁI HỆ THỐNG QUẢN LÝ CHI TIÊU (HEALTH CHECK)  " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Kiểm tra Workspace
$currentPath = (Get-Location).Path
if (-not (Test-Path "$currentPath\backend\app\main.py")) {
    Write-Host "[!] CẢNH BÁO: Script không chạy từ thư mục gốc dự án!" -ForegroundColor Red
    Write-Host "    Vui lòng cd về thư mục chứa backend và frontend." -ForegroundColor Yellow
    exit 1
}
Write-Host "[✓] Thư mục dự án: $currentPath" -ForegroundColor Green

# 2. Kiểm tra Docker & PostgreSQL Container
Write-Host "`n[1/5] Kiểm tra hạ tầng Docker & PostgreSQL..." -ForegroundColor Yellow
$dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
if ($null -eq $dockerCmd) {
    Write-Host "[-] Docker CLI chưa được cài đặt hoặc không nằm trong PATH." -ForegroundColor DarkYellow
} else {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Docker Engine chưa bật hoặc không phản hồi." -ForegroundColor DarkYellow
    } else {
        Write-Host "[✓] Docker Engine đang hoạt động bình thường." -ForegroundColor Green
        
        $pgContainer = docker ps --filter "name=expense_tracker_db" --format "{{.Names}} - {{.Status}}" 2>&1
        if ($pgContainer -match "expense_tracker_db") {
            Write-Host "[✓] Container PostgreSQL 18 đang chạy: $pgContainer" -ForegroundColor Green
        } else {
            Write-Host "[!] Container expense_tracker_db đang dừng hoặc chưa khởi tạo." -ForegroundColor Red
        }
    }
}

# 3. Kiểm tra cổng PostgreSQL 5434
$pgPortConn = Get-NetTCPConnection -LocalPort 5434 -State Listen -ErrorAction SilentlyContinue
if ($pgPortConn) {
    Write-Host "[✓] Cổng PostgreSQL 5434 đang lắng nghe kết nối." -ForegroundColor Green
} else {
    Write-Host "[-] Cổng 5434 chưa lắng nghe. Kiểm tra lại container database." -ForegroundColor Yellow
}

# 4. Kiểm tra Backend FastAPI trên cổng 8001
Write-Host "`n[2/5] Kiểm tra Backend FastAPI (Cổng 8001)..." -ForegroundColor Yellow
$backendPortConn = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($backendPortConn) {
    Write-Host "[✓] Tiến trình Backend đang lắng nghe tại 127.0.0.1:8001." -ForegroundColor Green
    
    # Kiểm tra Liveness
    try {
        $liveRes = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health/live" -Method Get -TimeoutSec 3
        if ($liveRes.status -eq "ok") {
            Write-Host "[✓] Backend Liveness check: 200 OK (Ứng dụng phản hồi tốt)" -ForegroundColor Green
        } else {
            Write-Host "[!] Liveness check trả về dữ liệu bất thường: $($liveRes | ConvertTo-Json -Compress)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[!] Không thể gọi endpoint /health/live: $_" -ForegroundColor Red
    }

    # Kiểm tra Readiness
    try {
        $readyRes = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health/ready" -Method Get -TimeoutSec 3
        if ($readyRes.status -eq "ok" -and $readyRes.database -eq "connected") {
            Write-Host "[✓] Backend Readiness check: 200 OK (Kết nối PostgreSQL 18 THÀNH CÔNG)" -ForegroundColor Green
        } else {
            Write-Host "[!] Readiness check báo database chưa sẵn sàng: $($readyRes | ConvertTo-Json -Compress)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[!] Backend Readiness check thất bại (PostgreSQL có thể đang ngắt): $_" -ForegroundColor Red
    }

    # Kiểm tra Route bảo vệ (401 là chuẩn)
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/notifications" -Method Get -TimeoutSec 3
        Write-Host "[?] Route bảo mật trả mã thành công bất thường." -ForegroundColor Yellow
    } catch [System.Net.WebException] {
        $statusCode = [int]$_.Exception.Response.StatusCode
        if ($statusCode -eq 401) {
            Write-Host "[✓] Route bảo mật (/api/v1/notifications): 401 Unauthorized (Bảo vệ phiên hoạt động chuẩn)" -ForegroundColor Green
        } else {
            Write-Host "[?] Route bảo mật trả mã HTTP: $statusCode" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[-] Kiểm tra route bảo mật: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[-] Backend chưa khởi chạy trên cổng 8001." -ForegroundColor Yellow
}

# 5. Kiểm tra Cổng 8000 (Tránh xung đột)
$port8000Conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000Conn) {
    Write-Host "[i] Ghi chú: Cổng 8000 đang được sử dụng bởi dịch vụ khác (đã cách ly an toàn, Backend dùng 8001)." -ForegroundColor Cyan
}

# 6. Kiểm tra Frontend Vite (Cổng 5173)
Write-Host "`n[3/5] Kiểm tra Frontend Vite (Cổng 5173)..." -ForegroundColor Yellow
$frontendPortConn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontendPortConn) {
    Write-Host "[✓] Frontend Vite đang chạy tại http://localhost:5173." -ForegroundColor Green
} else {
    Write-Host "[-] Frontend Vite chưa chạy trên cổng 5173." -ForegroundColor Yellow
}

# 7. Kiểm tra cấu hình API URL của Frontend
Write-Host "`n[4/5] Kiểm tra cấu hình Frontend API URL..." -ForegroundColor Yellow
$envPath = "$currentPath\frontend\.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath
    $apiUrlLine = $envContent | Where-Object { $_ -match "^VITE_API_BASE_URL=" }
    if ($apiUrlLine) {
        Write-Host "[✓] Cấu hình frontend/.env: $apiUrlLine" -ForegroundColor Green
        if ($apiUrlLine -match ":8001") {
            Write-Host "[✓] API URL trỏ chính xác vào cổng 8001 của Backend dự án Chi tiêu." -ForegroundColor Green
        } else {
            Write-Host "[!] CẢNH BÁO: API URL không trỏ vào cổng 8001!" -ForegroundColor Red
        }
    } else {
        Write-Host "[-] Không tìm thấy VITE_API_BASE_URL trong frontend/.env, dùng fallback localhost:8001." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "[-] Chưa có frontend/.env, hệ thống sẽ dùng fallback: http://localhost:8001/api/v1" -ForegroundColor DarkYellow
}

# 8. Kiểm tra Alembic Migration
Write-Host "`n[5/5] Kiểm tra phiên bản Alembic Migration..." -ForegroundColor Yellow
$pythonExe = "$currentPath\backend\.venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    $alembicCurrent = & $pythonExe -m alembic -c backend/alembic.ini current 2>&1
    $headRev = ($alembicCurrent | Select-String "\(head\)").Line
    if ($headRev) {
        Write-Host "[✓] Cơ sở dữ liệu đang ở phiên bản mới nhất: $headRev" -ForegroundColor Green
    } else {
        Write-Host "[!] Alembic current: $alembicCurrent" -ForegroundColor Yellow
    }
} else {
    Write-Host "[-] Không tìm thấy Python venv tại backend\.venv." -ForegroundColor Yellow
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "                  HOÀN TẤT KIỂM TRA TRẠNG THÁI                   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

<#
.SYNOPSIS
    Khởi chạy an toàn toàn bộ hệ thống Quản lý Chi tiêu Cá nhân & Gia đình phục vụ Demo.
.DESCRIPTION
    Script thực hiện:
    1. Kiểm tra Workspace & thư mục dự án
    2. Kiểm tra Docker CLI & Docker Engine
    3. Kiểm tra container PostgreSQL 18 (expense_tracker_db) và khởi động nếu đang dừng (không reset, không drop)
    4. Chờ cơ sở dữ liệu sẵn sàng (Port 5434)
    5. Kiểm tra cổng 8001 và khởi động Backend FastAPI (trong cửa sổ riêng hoặc tiến trình nền)
    6. Kiểm tra cổng 5173 và khởi động Frontend Vite (trong cửa sổ riêng)
    7. Chờ và kiểm tra Health Readiness HTTP 200
    8. In địa chỉ truy cập ứng dụng
#>

[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   KHỞI CHẠY HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN & GIA ĐÌNH        " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Xác nhận Workspace
$workspaceRoot = (Get-Location).Path
if (-not (Test-Path "$workspaceRoot\backend\app\main.py") -or -not (Test-Path "$workspaceRoot\frontend\package.json")) {
    Write-Host "[!] LỖI: Vui lòng chạy script từ thư mục gốc của dự án!" -ForegroundColor Red
    Write-Host "    Thư mục hiện tại: $workspaceRoot" -ForegroundColor Yellow
    exit 1
}
Write-Host "[1/6] Workspace hợp lệ: $workspaceRoot" -ForegroundColor Green

# 2. Kiểm tra Docker CLI & Docker Engine
Write-Host "`n[2/6] Kiểm tra Docker & Cơ sở dữ liệu PostgreSQL 18..." -ForegroundColor Yellow
$dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
if ($null -eq $dockerCmd) {
    Write-Host "[!] LỖI: Không tìm thấy lệnh 'docker'. Vui lòng cài đặt hoặc mở Docker Desktop." -ForegroundColor Red
    exit 1
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] LỖI: Docker Engine chưa được khởi động! Vui lòng bật Docker Desktop và thử lại." -ForegroundColor Red
    exit 1
}
Write-Host "[✓] Docker Engine đang hoạt động." -ForegroundColor Green

# 3. Kiểm tra hoặc bật container PostgreSQL của dự án (expense_tracker_db)
$pgRunning = docker ps --filter "name=expense_tracker_db" --filter "status=running" --format "{{.Names}}" 2>&1
if ($pgRunning -notmatch "expense_tracker_db") {
    Write-Host "[*] Khởi động service database từ docker-compose.yml (Không reset volume)..." -ForegroundColor Yellow
    docker compose up -d db
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] LỖI: Không thể khởi động container database!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[✓] Container PostgreSQL 18 ('expense_tracker_db') đã đang chạy." -ForegroundColor Green
}

# Chờ database sẵn sàng trên cổng 5434
Write-Host "[*] Kiểm tra kết nối tới cổng PostgreSQL 5434..." -ForegroundColor Yellow
$dbReady = $false
for ($i = 1; $i -le 15; $i++) {
    $conn = Get-NetTCPConnection -LocalPort 5434 -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $dbReady) {
    Write-Host "[!] LỖI: PostgreSQL không lắng nghe trên cổng 5434 sau 15 giây!" -ForegroundColor Red
    exit 1
}
Write-Host "[✓] Cơ sở dữ liệu PostgreSQL 18 sẵn sàng trên cổng 5434." -ForegroundColor Green

# 4. Kiểm tra và Khởi động Backend FastAPI (Cổng 8001)
Write-Host "`n[3/6] Kiểm tra cổng 8001 và khởi động Backend FastAPI..." -ForegroundColor Yellow
$port8001Conn = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue

if ($port8001Conn) {
    # Kiểm tra xem tiến trình đang nghe có phải là Backend của dự án này không
    try {
        $backendCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health/live" -Method Get -TimeoutSec 2
        if ($backendCheck.status -eq "ok") {
            Write-Host "[✓] Backend của dự án Chi tiêu đã đang chạy trên cổng 8001." -ForegroundColor Green
        } else {
            Write-Host "[!] Cổng 8001 đang được sử dụng bởi một ứng dụng khác không phải Backend này." -ForegroundColor Red
            Write-Host "    Vui lòng kiểm tra lại tiến trình đang dùng cổng 8001 trước khi tiếp tục." -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "[!] Cổng 8001 đang bận nhưng không phản hồi endpoint health." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[*] Đang khởi động Backend FastAPI trên cổng 8001..." -ForegroundColor Yellow
    $pythonExe = "$workspaceRoot\backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[!] LỖI: Không tìm thấy Python Virtualenv tại '$pythonExe'!" -ForegroundColor Red
        exit 1
    }
    
    $backendArgs = "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001"
    Start-Process -FilePath $pythonExe -ArgumentList $backendArgs -WorkingDirectory $workspaceRoot
    
    # Chờ Backend khởi động và kiểm tra readiness
    $backendReady = $false
    for ($i = 1; $i -le 15; $i++) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health/ready" -Method Get -TimeoutSec 2
            if ($health.status -eq "ok" -and $health.database -eq "connected") {
                $backendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $backendReady) {
        Write-Host "[!] LỖI: Backend không khởi động thành công trên cổng 8001 sau 15 giây!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[✓] Backend FastAPI đã khởi động và kết nối database thành công!" -ForegroundColor Green
}

# 5. Kiểm tra và Khởi động Frontend Vite (Cổng 5173)
Write-Host "`n[4/6] Kiểm tra cổng 5173 và khởi động Frontend React Vite..." -ForegroundColor Yellow
$port5173Conn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

if ($port5173Conn) {
    Write-Host "[✓] Frontend Vite đã đang chạy trên cổng 5173." -ForegroundColor Green
} else {
    Write-Host "[*] Đang khởi động Frontend dev server tại http://localhost:5173..." -ForegroundColor Yellow
    $frontendDir = "$workspaceRoot\frontend"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $frontendDir
    
    # Chờ Frontend mở cổng 5173
    $frontendReady = $false
    for ($i = 1; $i -le 15; $i++) {
        $conn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
        if ($conn) {
            $frontendReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $frontendReady) {
        Write-Host "[!] CẢNH BÁO: Frontend chưa mở cổng 5173 sau 15 giây. Vui lòng kiểm tra cửa sổ terminal Frontend." -ForegroundColor Yellow
    } else {
        Write-Host "[✓] Frontend Vite đã sẵn sàng trên cổng 5173!" -ForegroundColor Green
    }
}

# 6. Kiểm tra lại toàn diện trạng thái hệ thống
Write-Host "`n[5/6] Xác minh toàn diện các URL dịch vụ..." -ForegroundColor Yellow
try {
    $readyRes = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health/ready" -Method Get -TimeoutSec 3
    Write-Host "[✓] Backend Readiness: HTTP 200 OK (PostgreSQL: $($readyRes.database))" -ForegroundColor Green
} catch {
    Write-Host "[!] Kiểm tra Backend Readiness thất bại: $_" -ForegroundColor Red
}

# 7. Hiển thị thông tin trình diễn
Write-Host "`n[6/6] SẴN SÀNG TRÌNH DIỄN!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  ĐỊA CHỈ TRUY CẬP HỆ THỐNG:" -ForegroundColor Yellow
Write-Host "  - Ứng dụng Frontend (React):   http://localhost:5173" -ForegroundColor White
Write-Host "  - API Backend Swagger Docs:    http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host "  - API Health Check:            http://127.0.0.1:8001/health/ready" -ForegroundColor White
Write-Host "  - Cơ sở dữ liệu PostgreSQL:   127.0.0.1:5434 (Database: expense_tracker)" -ForegroundColor White
Write-Host ""
Write-Host "  TÀI KHOẢN DEMO SẴN CÓ (Khởi tạo qua scripts/seed_demo_data.py):" -ForegroundColor Yellow
Write-Host "  - Email:    demo@expensetracker-demo.com" -ForegroundColor White
Write-Host "  - Mật khẩu: DemoPassword123@" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Lưu ý an toàn: Để dừng hệ thống, đóng các cửa sổ terminal hoặc dừng tiến trình tương ứng."
Write-Host "Không chạy 'docker compose down -v' để tránh mất dữ liệu đã cấu hình." -ForegroundColor DarkGray

if (-not $NoBrowser) {
    Write-Host "`n[*] Đang mở trình duyệt tới trang chủ ứng dụng..." -ForegroundColor Cyan
    Start-Process "http://localhost:5173"
}

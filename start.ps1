# Enterprise LLM Platform - Start Script
Write-Host "=== Enterprise LLM Platform ===" -ForegroundColor Cyan

$PYTHON = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if (-not (Test-Path $PYTHON)) {
    $PYTHON = "python"
}

# Kill existing
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force 2>$null
Get-Process node -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -eq ""} | Stop-Process -Force 2>$null
Start-Sleep -Seconds 2

# Start Backend
Write-Host "[1/2] Starting Backend (port 8080)..." -ForegroundColor Yellow
Start-Process -FilePath $PYTHON -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080" -NoNewWindow
Start-Sleep -Seconds 4

# Health check
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 5
    Write-Host "  Backend OK: mode=$($health.mode), model=$($health.model)" -ForegroundColor Green
} catch {
    Write-Host "  Backend FAILED to start!" -ForegroundColor Red
    exit 1
}

# Start Frontend
Write-Host "[2/2] Starting Frontend (port 3000)..." -ForegroundColor Yellow
Push-Location platform
Start-Process -FilePath "npx" -ArgumentList "vite", "--host" -NoNewWindow
Pop-Location
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== All Running ===" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8080" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8080/docs" -ForegroundColor Cyan
Write-Host "  Logs:     Get-Content logs\server_$(Get-Date -Format 'yyyy-MM-dd').log -Wait -Tail 30" -ForegroundColor Gray

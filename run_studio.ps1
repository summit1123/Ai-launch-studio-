# AI Launch Studio Unified Runner (Windows PowerShell)
# This script starts both Backend (Uvicorn) and Frontend (Vite)
# Logs from both services are displayed in this window.

$PROJECT_ROOT = Join-Path $PSScriptRoot ""
$BACKEND_DIR = Join-Path $PROJECT_ROOT "backend"
$FRONTEND_DIR = Join-Path $PROJECT_ROOT "frontend"

# Find conda ai_env Python path directly (no activation needed)
$CONDA_BASE = (conda info --base).Trim()
$PYTHON_EXE = Join-Path $CONDA_BASE "envs\ai_env\python.exe"

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "❌ ai_env conda environment not found at: $PYTHON_EXE" -ForegroundColor Red
    Write-Host "   Run: conda create -n ai_env python=3.12 -y" -ForegroundColor Yellow
    exit 1
}

# Log file paths
$backendLog = Join-Path $BACKEND_DIR "backend_live.log"
$frontendLog = Join-Path $FRONTEND_DIR "frontend_live.log"

# Clear old logs
"" | Set-Content $backendLog
"" | Set-Content $frontendLog

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  🚀 AI Launch Studio                  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Python: $PYTHON_EXE" -ForegroundColor DarkGray
Write-Host ""

# 1. Start Backend (using cmd to merge stderr into stdout via 2>&1)
Write-Host "📡 Starting Backend (Port 8090)..." -ForegroundColor Yellow
$backendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "`"$PYTHON_EXE`" -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload 2>&1" `
    -WorkingDirectory $BACKEND_DIR `
    -RedirectStandardOutput $backendLog `
    -WindowStyle Hidden `
    -PassThru

# 2. Start Frontend
Write-Host "💻 Starting Frontend (Port 5050)..." -ForegroundColor Yellow
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev 2>&1" `
    -WorkingDirectory $FRONTEND_DIR `
    -RedirectStandardOutput $frontendLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host ""
Write-Host "------------------------------------------------" -ForegroundColor Gray
Write-Host "✅ Both services starting!" -ForegroundColor Green
Write-Host "   - Backend:  http://localhost:8090" -ForegroundColor White
Write-Host "   - Frontend: http://localhost:5050" -ForegroundColor White
Write-Host "------------------------------------------------" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop both services." -ForegroundColor Magenta
Write-Host ""

# Tail log files using background jobs
$tailBackend = Start-Job -ScriptBlock {
    param($logFile)
    Get-Content $logFile -Wait -Tail 0
} -ArgumentList $backendLog

$tailFrontend = Start-Job -ScriptBlock {
    param($logFile)
    Get-Content $logFile -Wait -Tail 0
} -ArgumentList $frontendLog

# Stream logs from both jobs with color-coded tags
try {
    while ($true) {
        $bOut = Receive-Job -Job $tailBackend -ErrorAction SilentlyContinue
        if ($bOut) {
            foreach ($line in $bOut) {
                Write-Host "[Backend]  $line" -ForegroundColor Green
            }
        }

        $fOut = Receive-Job -Job $tailFrontend -ErrorAction SilentlyContinue
        if ($fOut) {
            foreach ($line in $fOut) {
                Write-Host "[Frontend] $line" -ForegroundColor Cyan
            }
        }

        # Check if processes died
        if ($backendProc.HasExited -and $frontendProc.HasExited) {
            Write-Host ""
            Write-Host "⚠️  Both processes have exited." -ForegroundColor Yellow
            break
        }

        Start-Sleep -Milliseconds 300
    }
}
finally {
    # Cleanup on Ctrl+C or exit
    Write-Host ""
    Write-Host "🛑 Shutting down services..." -ForegroundColor Red

    Stop-Job -Job $tailBackend -ErrorAction SilentlyContinue
    Stop-Job -Job $tailFrontend -ErrorAction SilentlyContinue
    Remove-Job -Job $tailBackend -Force -ErrorAction SilentlyContinue
    Remove-Job -Job $tailFrontend -Force -ErrorAction SilentlyContinue

    if (-not $backendProc.HasExited) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }

    Write-Host "✅ All services stopped." -ForegroundColor Green
}

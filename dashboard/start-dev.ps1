# start-dev.ps1
# Starts the Vite dashboard AND keeps port-forward alive automatically.
# Usage: .\dashboard\start-dev.ps1   (from project root)

$namespace = "autoscaler"
$service   = "svc/api-server-service"
$localPort = 8000
$remotePort= 8000

Write-Host "[start-dev] Starting Vite dashboard + auto-restart port-forward..." -ForegroundColor Cyan

# Launch Vite in background
$vite = Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev" -WorkingDirectory $PSScriptRoot -PassThru

Write-Host "[start-dev] Vite started (PID $($vite.Id)). Dashboard: http://localhost:5173" -ForegroundColor Green
Write-Host "[start-dev] Press Ctrl+C to stop everything.`n" -ForegroundColor Yellow

try {
    while ($true) {
        Write-Host "[port-forward] Connecting $service -> localhost:$localPort ..." -ForegroundColor Cyan
        # Run port-forward in the foreground; when it drops, we loop and restart
        kubectl port-forward -n $namespace $service "${localPort}:${remotePort}"
        Write-Host "[port-forward] Disconnected. Reconnecting in 2 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`n[start-dev] Stopping Vite..." -ForegroundColor Yellow
    Stop-Process -Id $vite.Id -ErrorAction SilentlyContinue
}

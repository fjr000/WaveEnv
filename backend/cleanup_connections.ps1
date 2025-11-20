# Cleanup script for unclosed connections on port 8000
# This script will help identify and optionally clean up connections

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Connection Cleanup Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check connections on port 8000
Write-Host "Checking connections on port 8000..." -ForegroundColor Green
Write-Host ""

# Get all connections on port 8000
$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

if ($connections) {
    Write-Host "All connections on port 8000:" -ForegroundColor Yellow
    $connections | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    Write-Host ""
    
    # Group by state
    $byState = $connections | Group-Object State
    
    Write-Host "Connections by state:" -ForegroundColor Yellow
    foreach ($group in $byState) {
        Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor White
    }
    Write-Host ""
    
    # Find abnormal states
    $abnormalStates = @("CloseWait", "FinWait2", "TimeWait")
    $abnormalConnections = $connections | Where-Object { $abnormalStates -contains $_.State }
    
    if ($abnormalConnections) {
        Write-Host "Abnormal connections found:" -ForegroundColor Red
        $abnormalConnections | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
        Write-Host ""
        
        # Get unique PIDs
        $pids = $abnormalConnections | Select-Object -Unique -ExpandProperty OwningProcess
        
        Write-Host "Process IDs to clean: $($pids -join ', ')" -ForegroundColor Yellow
        Write-Host ""
        
        $response = Read-Host "Do you want to kill these processes? (yes/no)"
        if ($response -eq "yes" -or $response -eq "y") {
            foreach ($pid in $pids) {
                Write-Host "Killing PID $pid..." -NoNewline
                try {
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Host " OK" -ForegroundColor Green
                } catch {
                    Write-Host " FAILED: $_" -ForegroundColor Red
                }
            }
            Write-Host ""
            Write-Host "Cleanup complete." -ForegroundColor Green
        } else {
            Write-Host "Cancelled." -ForegroundColor Yellow
        }
    } else {
        Write-Host "No abnormal connections found." -ForegroundColor Green
    }
} else {
    Write-Host "No connections found on port 8000." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan


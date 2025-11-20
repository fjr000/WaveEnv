# Streamlit 前端启动脚本 (PowerShell)
# 确保在 jobs 环境下运行

# 设置输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "正在启动 Streamlit 前端..." -ForegroundColor Green
Write-Host ""

# 检查是否在 frontend 目录
if (-not (Test-Path "app.py")) {
    Write-Host "错误: 请在 frontend 目录下运行此脚本" -ForegroundColor Red
    exit 1
}

# 尝试多个端口，找到可用的（从8888开始，通常不太可能被占用）
$ports = @(8888, 8889, 8890, 8501, 8502, 8503)
$portFound = $false
$selectedPort = $null

foreach ($testPort in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $testPort -ErrorAction SilentlyContinue
    if (-not $connection) {
        $selectedPort = $testPort
        $portFound = $true
        break
    }
}

if ($portFound) {
    Write-Host "使用端口 $selectedPort 启动 Streamlit..." -ForegroundColor Green
    Write-Host "访问地址: http://localhost:$selectedPort" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "提示: 如果启动失败，可能是权限问题，请尝试:" -ForegroundColor Yellow
    Write-Host "  1. 以管理员身份运行 PowerShell" -ForegroundColor Yellow
    Write-Host "  2. 检查防火墙设置" -ForegroundColor Yellow
    Write-Host "  3. 手动关闭占用端口的程序" -ForegroundColor Yellow
    Write-Host ""
    streamlit run app.py --server.headless true --server.port $selectedPort --server.address localhost
} else {
    Write-Host "错误: 无法找到可用端口" -ForegroundColor Red
    Write-Host "已尝试的端口: $($ports -join ', ')" -ForegroundColor Yellow
    Write-Host "请关闭占用端口的程序或手动指定端口" -ForegroundColor Yellow
    exit 1
}




$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$venvDir = Join-Path $backendDir 'venv'
$pythonExecutable = Join-Path $venvDir 'Scripts\python.exe'
$backendEnv = Join-Path $backendDir '.env'
$backendEnvExample = Join-Path $backendDir '.env.example'

if (-not (Test-Path $backendEnv)) {
    if (Test-Path $backendEnvExample) {
        Copy-Item $backendEnvExample $backendEnv
        Write-Host 'Created backend/.env from .env.example'
    }
}

if (-not (Test-Path $pythonExecutable)) {
    Write-Host 'Creating Python virtual environment for backend...'
    py -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create the backend Python virtual environment.'
    }
}

$backendCommand = @"
`$ErrorActionPreference = 'Stop'
Set-Location '$backendDir'
& '$pythonExecutable' -m pip install -r requirements.txt
if (`$LASTEXITCODE -ne 0) {
    throw 'Backend dependency installation failed.'
}

`$generationMode = & '$pythonExecutable' -c "from config import Config; print(Config.GENERATION_MODE)"
if (`$LASTEXITCODE -ne 0) {
    throw 'Could not read GENERATION_MODE from backend/.env.'
}
if (`$generationMode -eq 'local') {
    Write-Host 'Installing local image-generation dependencies...'
    & '$pythonExecutable' -m pip install -r requirements-local.txt
    if (`$LASTEXITCODE -ne 0) {
        throw 'Local image-generation dependency installation failed.'
    }
}

& '$pythonExecutable' app.py
"@

if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Write-Host 'Installing frontend dependencies...'
    $installResult = & npm --prefix $frontendDir install
    if ($LASTEXITCODE -ne 0) {
        throw 'npm install failed in frontend.'
    }
}

Write-Host 'Starting backend...'
$backendEncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendCommand))
Start-Process powershell -WorkingDirectory $backendDir -ArgumentList '-NoExit','-EncodedCommand', $backendEncodedCommand

Write-Host 'Starting frontend...'
$frontendCommand = @"
`$ErrorActionPreference = 'Stop'
Set-Location '$frontendDir'
npm run dev
"@
$frontendEncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendCommand))
Start-Process powershell -WorkingDirectory $frontendDir -ArgumentList '-NoExit','-EncodedCommand', $frontendEncodedCommand

Write-Host ''
Write-Host 'Both services are starting.'
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Backend: http://127.0.0.1:5000/api/health'

# Lance API + frontend Nur (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$ffmpegBin = Join-Path $env:LOCALAPPDATA "ffmpeg\ffmpeg-8.0-essentials_build\bin"
if (Test-Path (Join-Path $ffmpegBin "ffmpeg.exe")) {
    $env:Path = "$ffmpegBin;$env:Path"
}

Write-Host "[Nur] Backend  -> http://127.0.0.1:8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; `$env:Path = '$ffmpegBin;' + `$env:Path; python run_server.py"

Write-Host "[Nur] Frontend -> http://localhost:5173"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "Ouvre http://localhost:5173"
Write-Host "Optionnel: `$env:PEXELS_API_KEY = 'ta_cle' avant de lancer pour la recherche."

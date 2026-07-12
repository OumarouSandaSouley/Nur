@echo off
REM Lance API + frontend Nur (Windows)
setlocal
cd /d "%~dp0"

set "FFMPEG_BIN=%LOCALAPPDATA%\ffmpeg\ffmpeg-8.0-essentials_build\bin"
if exist "%FFMPEG_BIN%\ffmpeg.exe" set "PATH=%FFMPEG_BIN%;%PATH%"

echo [Nur] Backend  -> http://127.0.0.1:8000
start "Nur-API" cmd /k "cd /d "%~dp0" && set PATH=%FFMPEG_BIN%;%PATH% && python run_server.py"

echo [Nur] Frontend -> http://localhost:5173
start "Nur-UI" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Ouvre http://localhost:5173 dans ton navigateur.
echo Ferme les deux fenetres Nur-API / Nur-UI pour arreter.
pause

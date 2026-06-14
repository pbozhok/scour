@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."

netstat -ano | findstr "LISTENING" | findstr ":8001" >nul 2>&1
if %errorlevel% neq 0 (
    start "Scour Server" /d "%PROJECT_ROOT%" /min cmd /k "venv\Scripts\uvicorn web.backend.main:app --host 0.0.0.0 --port 8001"
    timeout /t 2 /nobreak >nul
)

start "" http://localhost:8001
endlocal

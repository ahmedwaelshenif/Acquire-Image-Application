@echo off
setlocal
cd /d "%~dp0"
if exist "check image\app\main.py" cd /d "check image"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :setup_failed
)

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist ".deepface" set "DEEPFACE_HOME=%CD%\.deepface"

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, deepface, insightface, onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python packages. This can take several minutes...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :setup_failed
)

echo ========================================================
echo Starting Face Liveness and Quality Server...
echo Directory: %CD%
echo Opening http://127.0.0.1:8000/
echo ========================================================

start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "$ProgressPreference='SilentlyContinue'; for ($i=0; $i -lt 60; $i++) { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 1; if ($r.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:8000/'; exit 0 } } catch {}; Start-Sleep -Seconds 1 }"
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
if errorlevel 1 goto :startup_failed
goto :eof

:setup_failed
echo.
echo Setup failed. Ensure Python 3 and internet access are available, then review the messages above.
pause
exit /b 1

:startup_failed
echo.
echo The service stopped with an error. Review the messages above.
pause
exit /b 1

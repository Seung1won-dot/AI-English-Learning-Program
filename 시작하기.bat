@echo off
rem English World launcher - double click to start studying.
rem Opens the app in your browser and also allows phone access on the same Wi-Fi.
cd /d "%~dp0"

set HOST=0.0.0.0
set PORT=5000

rem Open the browser after the server has had 2 seconds to start.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:%PORT%"

".venv\Scripts\python.exe" app.py

pause

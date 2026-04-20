@echo off
echo === MyStock Start ===

echo [1/3] Kiwoom Server...
start "Kiwoom" cmd /k "C:\Python311-32\python.exe c:\MyStock\kiwoom_server\kiwoom_server.py"
timeout /t 15 /nobreak > nul

echo [2/3] FastAPI Server...
start "FastAPI" cmd /k "c:\MyStock\myEnv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir c:\MyStock\backend"
timeout /t 3 /nobreak > nul

echo [3/3] Cloudflare Tunnel...
start "Cloudflare" cmd /k "C:\Users\dsic7\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe tunnel --url http://localhost:8000"

echo.
echo Local:  http://localhost:8000
echo External URL: Check Cloudflare window
echo.
pause
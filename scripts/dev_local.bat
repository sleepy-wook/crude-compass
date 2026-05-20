@echo off
chcp 65001 >nul
REM Crude Compass Local Dev - launches backend + frontend in 2 cmd windows.
REM Backend: http://localhost:8000 (uvicorn auto-reload on .py save)
REM Frontend: http://localhost:5173 (vite HMR on .tsx save)

echo === Crude Compass Local Dev ===
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Two cmd windows will spawn. Close with Ctrl+C in each.
echo.

REM Use Python 3.12 explicitly (uvicorn deps installed there per pyproject.toml)
start "Crude Compass Backend" cmd /k "cd /d %~dp0..\backend && set PYTHONIOENCODING=utf-8 && py -3.12 -m uvicorn app.main:app --reload --port 8000"

REM Wait for backend port to bind
timeout /t 3 /nobreak >nul

start "Crude Compass Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo Done. Open http://localhost:5173

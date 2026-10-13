@echo off
title AgentFlow Platform
cd /d "%~dp0"
echo Starting AgentFlow...
start "" ".venv\Scripts\streamlit.exe" run app.py --server.port 8503
timeout /t 3 /nobreak >nul
start "" "http://localhost:8503"
echo.
echo Server is running. Close this window to stop.
pause

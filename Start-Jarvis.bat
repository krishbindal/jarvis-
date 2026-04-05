@echo off
setlocal
cd /d "c:\Users\krish\Desktop\Jarvis-Test"
cls
echo [SYSTEM] Initializing JARVIS-X Master Startup...
echo [SYSTEM] Starting n8n Nervous System (Docker)...
docker compose up -d
timeout /t 5 /nobreak > nul
echo [SYSTEM] Launching JARVIS-X Brain...
python main.py --auto-start
echo [SYSTEM] JARVIS-X is now active.
pause

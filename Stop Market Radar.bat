@echo off
echo Stopping ARC-NEXUS Market Radar...

rem Kill backend listener only (port 8002)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8002" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

rem Kill Vite dev server listener only (port 5175)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5175" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Done.
pause
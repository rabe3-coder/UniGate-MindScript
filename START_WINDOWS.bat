@echo off
setlocal
cd /d "%~dp0"
echo ======================================================
echo UniGate - Mind Script eng.rabe3
 echo Student sign-up + protected staff accounts + SQLite
 echo Address: http://127.0.0.1:8765
 echo Admin / 3 Affairs accounts: SETUP_STAFF_WINDOWS.bat
 echo NO hardcoded public admin credentials
 echo ======================================================
where py >nul 2>nul
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8765"
  py -3 server.py
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  start "" "http://127.0.0.1:8765"
  python server.py
  goto end
)
echo ERROR: Python 3.10+ was not found.
echo Install Python and enable Add to PATH.
pause
:end
endlocal

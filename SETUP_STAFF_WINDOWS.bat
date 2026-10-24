@echo off
setlocal
cd /d "%~dp0"
echo ======================================================
echo UniGate - First-time administrator / staff configuration
echo Only run on your own computer, after stopping the web server.
echo You will set one admin and exactly three affairs accounts.
echo ======================================================
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 manage_staff.py setup
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python manage_staff.py setup
  goto end
)
echo Python not found. Install Python 3.10+ and enable Add to PATH.
:end
echo.
pause
endlocal

@echo off
cd /d "%~dp0"

echo ============================================
echo   Initial refresh (this may take a minute)...
echo ============================================
python collector.py
python chart_tracker.py
python build_site_data.py

echo.
echo ============================================
echo   Starting server... Browser will open shortly.
echo   Use the Refresh button on the page anytime
echo   you want new data. Keep this window open.
echo   Press Ctrl+C here to stop the server.
echo ============================================
python local_server.py

pause

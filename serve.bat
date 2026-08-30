@echo off
REM OceanIQ - serve this folder over HTTP so index.html can fetch mock-data.json.
REM Browsers block fetch() on file:// URLs, so opening index.html directly will
REM show the "DATA SOURCE UNREACHABLE" panel. Run this instead.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:8000/index.html
  python -m http.server 8000
  goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:8000/index.html
  py -m http.server 8000
  goto :eof
)

where npx >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:8000/index.html
  npx --yes http-server -p 8000 -c-1
  goto :eof
)

echo No python or npx found on PATH. Serve this folder with any static file server
echo and open http://localhost:8000/index.html
pause

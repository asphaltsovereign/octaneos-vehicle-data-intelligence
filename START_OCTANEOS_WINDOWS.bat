@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  python -m venv "backend\.venv" || exit /b 1
)

call "backend\.venv\Scripts\activate.bat" || exit /b 1
python -m pip install -r "backend\requirements.txt" || exit /b 1

pushd "frontend"
if not exist "node_modules" call npm ci || exit /b 1
call npm run build || exit /b 1
popd

start "" "http://127.0.0.1:8000"
pushd "backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd

@echo off
REM Inicia la API (puerto 8000) y el dashboard (puerto 8501).
setlocal
set "RAIZ=%~dp0"
set "PY=python"
if exist "%RAIZ%.venv\Scripts\python.exe" set "PY=%RAIZ%.venv\Scripts\python.exe"

start "API ETL" /D "%RAIZ%" cmd /k ""%PY%" -m uvicorn api.main:app --port 8000"
cd /d "%RAIZ%App"
REM echo. responde con Enter la pregunta del correo que Streamlit hace la primera vez
echo.| "%PY%" -m streamlit run app.py

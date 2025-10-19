@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
pythonw run_gui.pyw
endlocal

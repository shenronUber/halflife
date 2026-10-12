@echo off
cd /d "%~dp0"
set "VF_PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if exist "%VF_PYTHON%" (
  "%VF_PYTHON%" "vector-fields\weapon-workshop\survolteur-2026-10-12\runtime.py"
) else (
  python "vector-fields\weapon-workshop\survolteur-2026-10-12\runtime.py"
)
if errorlevel 1 pause


@echo off
cd /d "%~dp0"
python "vector-fields\weapon-workshop\absoute-2026-10-12\runtime.py"
if errorlevel 1 pause

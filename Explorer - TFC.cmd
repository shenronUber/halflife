@echo off
cd /d "%~dp0"
python "vector-fields\explore.py"
if errorlevel 1 pause

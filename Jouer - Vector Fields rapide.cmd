@echo off
cd /d "%~dp0"
python "vector-fields\build_release.py" --launch-only
if errorlevel 1 pause

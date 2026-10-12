@echo off
cd /d "%~dp0"
python "vector-fields\weapon-workshop\fitted-2026-10-11\play_fitted.py"
if errorlevel 1 pause

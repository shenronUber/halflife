@echo off
cd /d "%~dp0"
python "vector-fields\play_wallrun.py"
if errorlevel 1 pause

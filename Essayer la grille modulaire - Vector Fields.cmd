@echo off
cd /d "%~dp0"
python "vector-fields\play_modular.py" %*
if errorlevel 1 pause

@echo off
cd /d "%~dp0"
python "vector-fields\play.py" --visual-lab
if errorlevel 1 pause

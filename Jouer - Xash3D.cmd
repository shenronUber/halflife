@echo off
cd /d "%~dp0"
python "weapon-lab\play.py" --engine xash
if errorlevel 1 pause

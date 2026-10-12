@echo off
cd /d "%~dp0"
python vector-fields\play_headgear.py --devtest --helmet riot
if errorlevel 1 pause

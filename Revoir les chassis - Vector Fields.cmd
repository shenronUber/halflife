@echo off
cd /d "%~dp0"
python "vector-fields\chassis-workshop\identity-2026-10-11\play_chassis.py"
if errorlevel 1 pause

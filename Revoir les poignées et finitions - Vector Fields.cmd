@echo off
cd /d "%~dp0"
python "vector-fields\weapon-workshop\finish-2026-10-11\test_native.py" --play
if errorlevel 1 pause

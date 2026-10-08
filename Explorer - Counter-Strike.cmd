@echo off
cd /d "%~dp0"
python "vector-fields\explore_cs.py"
if errorlevel 1 pause

@echo off
cd /d "%~dp0..\.."
python "vector-fields\play_personas.py"
if errorlevel 1 pause

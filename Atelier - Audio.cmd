@echo off
cd /d "%~dp0"
python "vector-fields\audio_workshop.py" preview --open
if errorlevel 1 pause

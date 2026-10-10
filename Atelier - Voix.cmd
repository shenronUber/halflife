@echo off
cd /d "%~dp0"
python vector-fields\voice_workshop.py preview
if errorlevel 1 (
  pause
  exit /b 1
)
start "" "%~dp0vector-fields\assets\audio\operators\listen.html"

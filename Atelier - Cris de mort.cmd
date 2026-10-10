@echo off
cd /d "%~dp0"
python vector-fields\death_voice_workshop.py preview
if errorlevel 1 (
  pause
  exit /b 1
)
start "" "%~dp0vector-fields\assets\audio\operator-deaths\listen.html"

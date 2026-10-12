@echo off
cd /d "%~dp0"
if not exist "vector-fields\generated\headgear-audio\listen.html" (
  python vector-fields\headgear_audio.py build
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
start "" "%~dp0vector-fields\generated\headgear-audio\listen.html"

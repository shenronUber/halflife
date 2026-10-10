@echo off
cd /d "%~dp0"
python vector-fields\build_death_sounds.py --ensure
if errorlevel 1 goto failed
start "" "vector-fields\generated\death-sfx\listen.html"
exit /b 0
:failed
pause
exit /b 1

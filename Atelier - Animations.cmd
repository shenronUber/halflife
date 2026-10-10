@echo off
cd /d "%~dp0"
if "%~1"=="" (
  python vector-fields\inspect_animations.py --cached
) else (
  python vector-fields\inspect_animations.py --rebuild --recipe "%~1"
)
if errorlevel 1 goto failed
python vector-fields\inspect_first_person.py
if errorlevel 1 goto failed
start "" "%CD%\vector-fields\build\animation-inspector.html"
exit /b 0
:failed
pause
exit /b 1

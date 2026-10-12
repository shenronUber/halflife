@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0vector-fields\animation-workshop\open-blender.ps1" -Franchissements
if errorlevel 1 pause

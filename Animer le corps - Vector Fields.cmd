@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0vector-fields\animation-workshop\open-fragmotion.ps1" -View third-person
if errorlevel 1 pause

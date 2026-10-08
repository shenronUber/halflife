@echo off
cd /d "%~dp0..\.."
python vector-fields\play_expeditions.py
if errorlevel 1 pause

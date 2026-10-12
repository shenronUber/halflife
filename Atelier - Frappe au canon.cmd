@echo off
cd /d "%~dp0"
python vector-fields/play_weapon_melee.py
if errorlevel 1 pause

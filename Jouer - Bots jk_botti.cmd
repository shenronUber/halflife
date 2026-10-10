@echo off
cd /d "%~dp0"
python vector-fields\bots\jk_botti_lab.py play %*
if errorlevel 1 pause

@echo off
cd /d "%~dp0"
python vector-fields\traversal_editor.py apply
if errorlevel 1 pause

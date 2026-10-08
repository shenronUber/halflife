@echo off
cd /d "%~dp0..\..\runtime\xash3d"
start "" xash3d.exe -rodir "F:\SteamLibrary\steamapps\common\Half-Life" -game vf_skins -windowed -width 1280 -height 720 -console -nointro +exec lab_controls.cfg +map vf_range

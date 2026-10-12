@echo off
cd /d "%~dp0"
echo Vector Fields - inspection de l'arme
echo I : regarder les deux cotes. F11 : changer l'assemblage.
echo Session temporaire independante, nettoyee a la fermeture du jeu.
python vector-fields\play_weapon_inspect.py
if errorlevel 1 pause

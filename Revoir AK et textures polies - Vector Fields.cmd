@echo off
cd /d "%~dp0"
echo Vector Fields - AK MW3 et textures polies
echo Moteur temporaire independant. Fermer le jeu pour nettoyer la session.
echo 1 M40 / 2 AK / 3 Ossuaire / 4 Roncier
echo 5 M40 forge / 6 AK forge / 7 8 9 0 poignées A B C D
python vector-fields\weapon-workshop\polish-2026-10-11\test_native.py --play
if errorlevel 1 pause

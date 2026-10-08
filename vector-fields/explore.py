"""Choose an imported TFC map for a local exploration session."""
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
maps=sorted(p.stem for p in Path('F:/SteamLibrary/steamapps/common/Half-Life/tfc/maps').glob('*.bsp'))
if not maps:raise SystemExit('TFC maps not found in the configured Steam library.')
print('Vector Fields - cartes TFC (exploration, sans objectifs de match)\n')
for i,name in enumerate(maps,1):print(f'{i:2}. {name}')
while True:
    choice=input('\nNumero de la carte (Entree = 2fort) : ').strip()
    if not choice:choice='1'
    if choice.isdigit() and 1<=int(choice)<=len(maps):break
    print('Choisir un numero de la liste.')
raise SystemExit(subprocess.call([sys.executable,str(root/'play.py'),'--map','vf_tfc_'+maps[int(choice)-1]]))

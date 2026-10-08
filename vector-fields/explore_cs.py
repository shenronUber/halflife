"""Choose an installed Counter-Strike map for exploration in Vector Fields."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
maps=sorted(p.stem for p in Path('F:/SteamLibrary/steamapps/common/Half-Life/cstrike/maps').glob('*.bsp'))
if not maps:raise SystemExit('Counter-Strike maps not installed.')
print('Vector Fields - Counter-Strike / exploration\n')
for i,name in enumerate(maps,1):print(f'{i:2}. {name}')
while True:
 choice=input('\nNumero (Entree = de_dust2) : ').strip()
 if not choice:choice=str(maps.index('de_dust2')+1 if 'de_dust2' in maps else 1)
 if choice.isdigit() and 1<=int(choice)<=len(maps):break
raise SystemExit(subprocess.call([sys.executable,str(root/'play.py'),'--visual-lab','--map','vf_cs_'+maps[int(choice)-1]]))

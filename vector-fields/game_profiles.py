"""One map registry for preparation, release packaging and public launchers."""
from pathlib import Path
import importlib,inspect,shutil,re
MAPS={
 'vf_range':dict(title='Combat et parcours',source='test-room',builder='build_test_room',public=True),
 'vf_modular':dict(title='Grille modulaire',source='modular-range',builder='build_modular_range',public=True,arrival='vf_modular_start'),
 'vf_tiles':dict(title='Modules jouables',source='tile-laboratory',builder='build_tile_laboratory',public=True,arrival='vf_tiles_start'),
 'vf_traversal':dict(title='Parcours de regression',source='traversal-range',builder='build_traversal_range',public=False),
 'vf_fx_range':dict(title='Atelier des effets',source='weapon-fx/range',builder='build_weapon_fx_range',public=False),
}

def arrival_config(name,reference=False):
 return MAPS.get(name,{}).get('arrival','vf_reference_start'if reference else'vf_start')

VARIANTS=[('Laboratoire ferme A','Cabinets, couloir bas et galerie. Duels avec couvertures rapprochees.'),
 ('Laboratoire ferme B','Cloisons decalees et traversees laterales. Meme parcours, autre lecture des tirs.'),
 ('Chantier ouvert A','Machines, abris partiels et ciel visible. Contournement des couvertures.'),
 ('Chantier ouvert B','Conteneurs decales et facade partielle. Lignes de tir plus longues.'),
 ('Galeries A','Deux niveaux relies par des escaliers. Prendre la hauteur ou passer dessous.'),
 ('Galeries B','Galerie raccourcie et couvertures hautes. Angles verticaux et replis.'),
 ('Conduits A','Volume ferme, chicanes et passage bas. Glissade et flanc lateral.'),
 ('Conduits B','Chicanes decalees et couvertures compactes. Sorties de conduits a surveiller.')]

def menu_text():
 descriptions={'vf_range':'Combat, cibles et parcours dans la salle de test.',
  'vf_modular':'Grille simple au-dessus des nuages. Mono, domino, I et L avec raccords aleatoires.',
  'vf_tiles':'Huit variantes melangees par module : ferme, ouvert, galeries et conduits. Nouvelle combinaison a chaque lancement.',
  'vf_traversal':'Parcours de reference pour tester les mouvements.',
  'vf_fx_range':'Salle de reference pour les effets des armes.'}
 rows=[]
 for name,row in MAPS.items():
  cfg=arrival_config(name)
  rows.append('|'.join([name,'-1',row['title'],descriptions.get(name,row['title']),cfg]))
 for i,(title,description)in enumerate(VARIANTS):rows.append('|'.join(['vf_tiles',str(i),title,description,'vf_tiles_start']))
 return '\n'.join(rows)+'\n'

def build_menu():
 path=Path(__file__).resolve().parent/'generated/map-menu/maps.txt';path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(menu_text(),encoding='ascii');return path
def prepare_maps(mod):
 for name,row in MAPS.items():
  build=importlib.import_module(row['builder']).build
  result=build(**({'ensure':True}if 'ensure'in inspect.signature(build).parameters else{}))
  path=Path(result)if result is not None else Path(__file__).resolve().parent/'generated'/row['source']/(name+'.bsp')
  shutil.copy2(path,Path(mod)/'maps'/(name+'.bsp'))
def write_controls(mod):
 mod=Path(mod)
 (mod/'vf').mkdir(exist_ok=True);shutil.copy2(build_menu(),mod/'vf/maps.txt')
 # Imported exploration maps and installed custom BSPs also use this menu.
 # Keep this runtime inventory separate from the canonical local map catalog.
 extras=[]
 for path in sorted((mod/'maps').glob('*.bsp')):
  name=path.stem.lower()
  if name in MAPS or not re.fullmatch('[a-z0-9_]{1,60}',name):continue
  group='CS'if name.startswith('vf_cs_')else'TFC'if name.startswith('vf_tfc_')else'Autre'
  short=name.removeprefix('vf_cs_').removeprefix('vf_tfc_').replace('_',' ')
  extras.append('|'.join([name,'-1',group+' / '+short,'Exploration de la carte. Les objectifs CS/TFC ne sont pas actives.','vf_explore_start']))
 (mod/'vf/maps-extra.txt').write_text('\n'.join(extras)+('\n'if extras else''),encoding='ascii')
 (mod/'vf_explore_start.cfg').write_text('exec vf_voice_behavior.cfg\nwait 180\nsv_cheats 1\ncmd give item_suit\ncmd give weapon_9mmAR\ncmd give ammo_9mmbox\nweapon_9mmAR\nwait 30\n',encoding='ascii')
 # Map changes preserve the selected loadout. No prototype-only DLL or preset.
 (mod/'vf_modular_start.cfg').write_text('wait 180\nsv_cheats 1\ncmd give item_suit\ncmd give weapon_9mmAR\ncmd give ammo_9mmbox\nweapon_9mmAR\nwait 30\ncmd vf_modular_info\n',encoding='ascii')
 (mod/'modular_play.cfg').write_text((mod/'vf_modular_start.cfg').read_text(),encoding='ascii')
 (mod/'vf_tiles_start.cfg').write_text((mod/'vf_modular_start.cfg').read_text()+'echo "CYAN wallrun / VIOLET glissade / JAUNE corniche / VERT acces"\n',encoding='ascii')
 (mod/'vf_reference_start.cfg').write_text('exec vf_voice_behavior.cfg\nwait 180\nweapon_9mmAR\nvf_reference 0\nwait 30\nvf_commit\n',encoding='ascii')
 controls=mod/'lab_controls.cfg'
 keys='F4|F5|F9|F10|F12|HOME'
 lines=[line for line in controls.read_text(encoding='ascii').splitlines()if not re.match(r'\s*bind\s+"?(?:'+keys+r')"?\s',line,re.I)
        and not re.match(r'\s*bind\s+.*\b(?:map|changelevel)\s',line,re.I)
        and not line.startswith('alias vf_tiles_')]
 controls.write_text('\n'.join(lines)+'\n',encoding='ascii')
 with controls.open('a',encoding='ascii')as f:
  f.write('\nbind F4 "vf_maps"\n'
          'bind END "vf_effect_clear"\n'
          'unbind F9\nunbind HOME\n'
          'bind F5 "cmd vf_modular_info"\n'
          'bind F10 "cam_command 1"\nbind F12 "cam_command 2"\n')
  for variant in range(8):
   f.write(f'alias vf_tiles_v{variant} "vf_tiles_variant {variant}; vf_modular_seed 6; map vf_tiles; exec vf_tiles_start.cfg"\n')
  for name,variant in [('closed',0),('open',2),('levels',4),('ducts',6)]:f.write(f'alias vf_tiles_{name} vf_tiles_v{variant}\n')
  f.write('alias vf_tiles_mix "vf_tiles_variant -1; vf_modular_seed 0; map vf_tiles; exec vf_tiles_start.cfg"\n')


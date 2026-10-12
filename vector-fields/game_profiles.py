"""One map registry for preparation, release packaging and public launchers."""
from pathlib import Path
import importlib,inspect,shutil
MAPS={
 'vf_range':dict(title='Combat et parcours',source='test-room',builder='build_test_room',public=True),
 'vf_modular':dict(title='Grille modulaire',source='modular-range',builder='build_modular_range',public=True),
 'vf_traversal':dict(title='Parcours de regression',source='traversal-range',builder='build_traversal_range',public=False),
 'vf_fx_range':dict(title='Atelier des effets',source='weapon-fx/range',builder='build_weapon_fx_range',public=False),
}
def prepare_maps(mod):
 for name,row in MAPS.items():
  build=importlib.import_module(row['builder']).build
  result=build(**({'ensure':True}if 'ensure'in inspect.signature(build).parameters else{}))
  path=Path(result)if result is not None else Path(__file__).resolve().parent/'generated'/row['source']/(name+'.bsp')
  shutil.copy2(path,Path(mod)/'maps'/(name+'.bsp'))
def write_controls(mod):
 mod=Path(mod)
 # Map changes preserve the selected loadout. No prototype-only DLL or preset.
 (mod/'vf_modular_start.cfg').write_text('wait 180\nsv_cheats 1\ncmd give item_suit\ncmd give weapon_9mmAR\ncmd give ammo_9mmbox\nweapon_9mmAR\nwait 30\ncmd vf_modular_info\n',encoding='ascii')
 (mod/'modular_play.cfg').write_text((mod/'vf_modular_start.cfg').read_text(),encoding='ascii')
 (mod/'vf_reference_start.cfg').write_text('exec vf_voice_behavior.cfg\nwait 180\nweapon_9mmAR\nvf_reference 0\nwait 30\nvf_commit\n',encoding='ascii')
 with (mod/'lab_controls.cfg').open('a',encoding='ascii')as f:
  f.write('\nbind F4 "map vf_range; exec vf_start.cfg"\n'
          'bind END "vf_effect_clear"\n'
          'bind F9 "vf_modular_seed 0; map vf_modular; exec vf_modular_start.cfg"\n'
          'bind F5 "cmd vf_modular_info"\n'
          'bind F10 "cam_command 1"\nbind F12 "cam_command 2"\n')


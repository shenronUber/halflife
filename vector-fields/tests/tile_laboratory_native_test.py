"""Playable interiors, actual traversal, seeded reload and the one-button map menu."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from slide_feet_bundle import prepare_slide_feet
from native_workspace import private_copy,port
from build_tile_laboratory import build,geometry
from build_atmosphere import deploy as atmosphere
from build_modular_ambience import deploy as ambience
from game_profiles import write_controls,menu_text
from release import startup
OUT=ROOT/'docs/validation/tile-laboratory'

def expected(seed):
 import cpp_tests
 exe=ROOT/'build/policy-tests/tile_rooms/tile_rooms.exe'
 if not exe.exists():
  old=cpp_tests.TESTS
  try:
   cpp_tests.TESTS={'tile_rooms':old['tile_rooms']};assert cpp_tests.run()==0
  finally:cpp_tests.TESTS=old
 return json.loads(subprocess.check_output([str(exe),'--dump',str(seed)],text=True))

def run():
 live=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
 sdk=Path(os.environ.get('VF_RELEASE_SDK',ROOT/'build'))
 engine,mod=prepare_slide_feet('tile-laboratory',server=sdk/'server/hl.dll',client=sdk/'client/client.dll',engine_binaries=live)
 private_copy(build(ensure=True),mod/'maps/vf_tiles.bsp');atmosphere(mod);ambience(mod)
 (mod/'lab_controls.cfg').write_text('bind F4 "map vf_range"\nbind F9 "map vf_modular"\n')
 write_controls(mod)
 extra=live/'vf_visual/vf/maps-extra.txt'
 if extra.exists():private_copy(extra,mod/'vf/maps-extra.txt')
 entry_count=len(menu_text().splitlines())+len((mod/'vf/maps-extra.txt').read_text().splitlines())
 controls=(mod/'lab_controls.cfg').read_text();assert 'bind F4 "vf_maps"'in controls
 assert not re.search(r'^bind .*\b(?:map|changelevel)\s',controls,re.M)
 g=geometry();offset=-g['extent']//2
 lines=['wait 150','gl_vsync 0','host_framerate .0166667','fps_max 60','developer 1','con_notifytime 0',
  'sv_cheats 1','cmd give item_suit','cmd give weapon_9mmAR','weapon_9mmAR','wait 25',
  'vf_reference 0','wait 20','vf_commit','wait 30','vf_character','vf_character','wait 10']
 def add(*args):lines.extend(args)
 def probe(label):add('echo TILE_'+label,'cmd vf_traversal_info','wait 2')
 def place(x,y,z,yaw=0,vx=0,vy=0):
  add('-forward','-back','-jump','-duck','wait 8',f'cmd vf_traversal_place {offset+x} {offset+y} {z} {yaw} {vx} {vy} 0','wait 4',f'vf_traversal_look {yaw} 0')
 for v in range(8):
  add(f'vf_tiles_variant {v}','vf_modular_seed 42','map vf_tiles','wait 150','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR','wait 20',f'echo TILE_VARIANT_{v}','cmd vf_tiles_info','cmd vf_tiles_check','vf_atmosphere_info')
  place(480,592,36,330);add('vf_traversal_look 330 -7','wait 8',f'screenshot scrshots/variant_{v}.png','wait 3')
  place(224,320,36);probe(f'V{v}_SLIDE_SET');add('+forward','wait 8','+duck','wait 8');probe(f'V{v}_SLIDE')
  add('wait 35','-duck','-forward','wait 10');probe(f'V{v}_SLIDE_EXIT')
  place(338,1040,54);add('+jump','wait 22','-jump','wait 20');probe(f'V{v}_HANG')
  add('+back','+jump','wait 3');probe(f'V{v}_BACK')
  add('-back','vf_traversal_look 180 0','wait 30');probe(f'V{v}_REHANG');add('-jump')
  place(810,862,128,300,320);add('+forward','+jump','wait 4','-jump','vf_traversal_look 0 0','wait 4');probe(f'V{v}_RUN')
  add('wait 60','-forward','wait 30');probe(f'V{v}_RUN_EXIT')
  place(144,512,36,270);add('+forward','wait 64','-forward','wait 5');probe(f'V{v}_STAIRS')
  if v in(4,5):
   end=496 if v==4 else 448
   place(1112,end+304,36,270);add('+forward','wait 64','-forward','wait 5');probe(f'V{v}_UPPER')
  if v==7:
   add('save tile_variant','wait 6','vf_tiles_variant 2','load tile_variant','wait 150','echo TILE_RESTORED','cmd vf_tiles_info','cmd vf_tiles_check','wait 20')
 # All junctions in the mixed kit; trace checks additionally inspect every candidate.
 add('vf_tiles_variant -1','vf_modular_seed 42','map vf_tiles','wait 150','echo TILE_MIX','cmd vf_tiles_info','cmd vf_tiles_check')
 layout=expected(42)
 for edge in g['edges']:
  e=edge['edge'];start=edge['start'];center=edge['center'];axis=edge['axis'];kind=layout['links'][e]
  add('-forward','-jump','-duck','wait 8')
  if kind in(0,1):
   x,y=(start-96,center)if axis=='x'else(center,start-96);yaw=0 if axis=='x'else 90;vx,vy=(320,0)if axis=='x'else(0,320)
   add(f'cmd vf_traversal_place {x} {y} 36.1 {yaw} {vx} {vy} 0','wait 4',f'vf_traversal_look {yaw} 0')
   probe(f'EDGE_{e}_SET');add('+forward','wait 150')
   probe(f'EDGE_{e}_CROSS');add('-forward','wait 8')
  else:
   for direction in(1,-1):
    u=start-96 if direction==1 else start+g['gap']+96;face=edge['wall_face']+18
    x,y=(u,face)if axis=='x'else(face,u);vx,vy=(320*direction,0)if axis=='x'else(0,320*direction)
    yaw=(0 if direction==1 else 180)if axis=='x'else(90 if direction==1 else 270)
    entry=(300 if direction==1 else 240)if axis=='x'else(150 if direction==1 else 210)
    add('-forward','-jump','wait 8',f'cmd vf_traversal_place {x} {y} 128 {entry} {vx} {vy} 0','wait 4',f'vf_traversal_look {entry} 0','+forward','+jump','wait 2','-jump',f'vf_traversal_look {yaw} 0','wait 28')
    probe(f'EDGE_{e}_{direction}_RUN');add('wait 55','-forward','wait 40');probe(f'EDGE_{e}_{direction}_LAND')
 add('-forward','-jump','vf_modular_seed 6','map vf_tiles','wait 150','echo TILE_SHOWCASE','cmd vf_tiles_info','cmd vf_tiles_check','wait 10','noclip','cmd vf_traversal_place 0 0 2800 90','wait 4','vf_traversal_look 90 89','default_fov 110','r_drawviewmodel 0','vf_first_person_body 0','wait 10','screenshot scrshots/mixed_overview.png','wait 3','noclip','default_fov 90','r_drawviewmodel 1','vf_first_person_body 1')
 # Exercise the visible menu using the same pointer routing as real clicks.
 place(640,640,36);add('wait 20')
 add('exec lab_controls.cfg','vf_maps','wait 12','screenshot scrshots/map_menu.png','wait 3')
 for i in range(entry_count-1):add('vf_ui_pointer 100 200 3','wait 1')
 add('screenshot scrshots/map_menu_scrolled.png','wait 3')
 for i in range(entry_count-1):add('vf_ui_pointer 100 200 2','wait 1')
 add('vf_ui_pointer 1200 60 1','wait 2','vf_ui_pointer 1200 60 0','wait 3','vf_maps','wait 5',
  'vf_ui_pointer 100 270 1','wait 2','vf_ui_pointer 100 270 0','wait 3',
  'vf_ui_pointer 1000 548 1','wait 2','vf_ui_pointer 1000 548 0','wait 3')
 # Client commands issued by HUD clicks append to the engine buffer. Let this
 # script finish, then continue from the selected map's real arrival config.
 with(mod/'vf_tiles_start.cfg').open('a')as f:f.write('exec tiles_menu_mix.cfg\n')
 (mod/'tiles_menu_mix.cfg').write_text('wait 15\necho TILE_MENU_MIX\ncmd vf_tiles_info\ncmd vf_tiles_check\ncmd vf_traversal_info\nvf_maps\nwait 5\nvf_ui_pointer 100 160 1\nwait 2\nvf_ui_pointer 100 160 0\nwait 3\nvf_ui_pointer 1000 548 1\nwait 2\nvf_ui_pointer 1000 548 0\nwait 3\n')
 (mod/'vf_start.cfg').write_text(startup()+'exec tiles_menu_range.cfg\n')
 (mod/'tiles_menu_range.cfg').write_text('wait 30\necho TILE_MENU_RANGE\ncmd vf_traversal_info\nwait 10\nquit\n')
 for i,start in enumerate(range(0,len(lines),70)):
  part=lines[start:start+70]
  if start+70<len(lines):part.append(f'exec tiles_{i+1:03}.cfg')
  (mod/f'tiles_{i:03}.cfg').write_text('\n'.join(part)+'\n',encoding='ascii')
 child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720','-nointro','-nowriteconfig','-dev','1','-log','tiles.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+map','vf_tiles','+exec','tiles_000.cfg'],cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 try:child.wait(timeout=300)
 finally:
  if child.poll()is None:child.terminate();child.wait(timeout=8)
 OUT.mkdir(parents=True,exist_ok=True);text=(engine/'tiles.log').read_text(errors='replace');shutil.copy2(engine/'tiles.log',OUT/'native.log')
 for p in(mod/'scrshots').glob('*.png'):shutil.copy2(p,OUT/p.name)
 cases={}
 for name,block in re.findall(r'TILE_([A-Z0-9_-]+)\s+(.*?)(?=TILE_|\Z)',text,re.S):
  block=block.split('Spawn Server:')[0]
  move=re.search(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+)',block)
  if move:cases[name]=dict(phase=int(move[1]),origin=list(map(float,move[2].split(','))))
  rooms=re.findall(r'VFTiles module=\d+ mask=\d+ form=\w+ room=(\d+) forced=(-?\d+)',block)
  if rooms:cases.setdefault(name,{}).update(rooms=rooms)
 checks=re.findall(r'VFModular check seed=(\d+) candidates=(\d+) mismatches=(\d+)',text)
 report=dict(passed=False,cases=cases,checks=checks,exit_code=child.returncode)
 (OUT/'native.json').write_text(json.dumps(report,indent=2))
 assert child.returncode==0 and not any(s in text for s in('Host_Error','Crash:','SV_Error'))
 assert len(checks)>=11 and all(n=='141'and errors=='0'for _,n,errors in checks),checks
 for v in range(8):
  assert cases[f'VARIANT_{v}']['rooms']and all(r==str(v)and forced==str(v)for r,forced in cases[f'VARIANT_{v}']['rooms'])
  assert cases[f'V{v}_SLIDE']['phase']==5,cases[f'V{v}_SLIDE']
  pos=cases[f'V{v}_SLIDE_SET']['origin'];assert abs(pos[0]-offset-224)<2 and abs(pos[1]-offset-320)<2,pos
  pos=cases[f'V{v}_SLIDE']['origin'];assert offset+264<pos[0]<offset+448 and abs(pos[1]-offset-320)<2,pos
  assert cases[f'V{v}_SLIDE_EXIT']['origin'][0]>offset+480
  assert cases[f'V{v}_HANG']['phase']==2,cases[f'V{v}_HANG']
  assert cases[f'V{v}_BACK']['phase']==7,cases[f'V{v}_BACK']
  assert cases[f'V{v}_REHANG']['phase']==2,cases[f'V{v}_REHANG']
  assert cases[f'V{v}_RUN']['phase']==8,cases[f'V{v}_RUN']
  assert cases[f'V{v}_RUN_EXIT']['phase']==0
  assert 227<cases[f'V{v}_STAIRS']['origin'][2]<230,cases[f'V{v}_STAIRS']
  if v in(4,5):
   row=cases[f'V{v}_UPPER'];assert 227<row['origin'][2]<230 and abs(row['origin'][0]-(offset+1112))<2,row
 assert all(r=='7'and forced=='7'for r,forced in cases['RESTORED']['rooms'])
 for edge in g['edges']:
  e=edge['edge'];axis=0 if edge['axis']=='x'else 1;start=edge['start']
  if layout['links'][e]in(0,1):
   assert abs(cases[f'EDGE_{e}_SET']['origin'][axis]-(start-96))<40,cases[f'EDGE_{e}_SET']
   assert cases[f'EDGE_{e}_CROSS']['origin'][axis]>start+g['gap']+25,cases[f'EDGE_{e}_CROSS']
  else:
   for direction in(1,-1):
    assert cases[f'EDGE_{e}_{direction}_RUN']['phase']==8,cases[f'EDGE_{e}_{direction}_RUN']
    row=cases[f'EDGE_{e}_{direction}_LAND'];assert row['phase']==0 and 35<row['origin'][2]<40,row
 assert 'VFMaps launch: map=vf_tiles variant=-1'in text and 'VFMaps launch: map=vf_range variant=-1'in text
 assert f'VFMaps catalog: {entry_count} entries'in text
 assert 'Spawn Server: vf_range'in text and 'VFAtmosphere active=1'in text
 report['passed']=True;(OUT/'native.json').write_text(json.dumps(report,indent=2))
 print('PASS native eight interiors, slide, ledge/back-jump, wallrun, stairs, all junctions, save/load and map menu',flush=True)

if __name__=='__main__':run()

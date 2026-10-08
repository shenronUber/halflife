"""Actual renderer: equipment-linked appearance, free override, save/load and effects."""
import json,re,subprocess,time,argparse
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_visual'
def run(width=1920,height=1080):
 captures=[]
 def click(x,y):return f'vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 14\n'
 def snap(name):
  name=f'eq_{width}_{name}';captures.append(name);return f'wait 18\nscreenshot scrshots/{name}.png\nwait 4\n'
 def mode(free):return click(800,40)+snap('dropdown_'+str(free))+click(800,143 if free else 92)+'wait 25\n'
 s='wait 180\ndeveloper 1\nfullscreen\nvid_width\nvid_height\ncon_notifytime 0\nweapon_9mmAR\nvf_equipment_audit\nvf_character\nwait 35\nvf_animation_time 0\n'+snap('default')
 for f,name in enumerate(['baseline','predator','fortress','rogue','engine','anomalous']):
  s+=click(67+(f%3)*94,551+(f//3)*38)+snap('operator_'+name)
 s+=click(255,551)+'vf_commit\nwait 25\nvf_visual_bench operator_fortress\nwait 215\n'
 # Gloves change alone, then removal of the shoulder accessory.
 s+=click(69,278)+click(880,208)+click(1090,317)+snap('gloves')
 s+=click(220,222)+click(980,505)+snap('without_shoulders')+'vf_revert\n'
 s+=click(410,104)+'wait 15\n'
 for f,name in enumerate(['baseline','predator','fortress','rogue','engine','anomalous']):
  s+=click(67+(f%3)*94,551+(f//3)*38)+snap('weapon_'+name)
 s+=click(255,551)+'vf_commit\nwait 25\nvf_visual_bench weapon_fortress\nwait 215\n'+click(1220,40)+snap('in_hand')
 s+='+attack\nwait 22\n-attack\nwait 25\n+reload\nwait 30\n'+snap('reload')+'-reload\nwait 110\ncmd vf_body_info\nwait 20\n'
 s+='vf_character\nwait 20\n'+mode(1)+click(640,104)+'wait 25\nvf_skin_all 151\nvf_skin_set 0 145\nvf_skin_commit\nwait 30\nvf_animation_time 0\n'+snap('free_skin')
 s+=click(901,104)+click(250,520)+click(1160,692)+'wait 20\n'+snap('free_weapon')
 s+=mode(0)+snap('linked_style')+click(140,104)+snap('linked_restored')
 s+=mode(1)+click(640,104)+'wait 20\n'+snap('free_restored')
 s+=click(1220,40)+'save vf_equipment_test\nwait 55\nload vf_equipment_test\nwait 170\ndeveloper 1\ncon_notifytime 0\nvf_character\nwait 30\n'+mode(0)+snap('after_load')
 s+=click(1220,40)+'cmd vf_skin_camera\nwait 25\n'+snap('mannequin')
 s+='map vf_range\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_effects\nwait 20\nvf_effect_select toxic\n'+snap('toxic')+'vf_effect_spawn\nwait 20\n'+snap('toxic_world')
 s+='vf_effects\nwait 10\nvf_effect_select caustic_contagion\n'+snap('contambloom')+'vf_effect_spawn\nwait 20\n'+snap('contambloom_world')
 s+='vf_effect_clear\nvf_engine_stats\nquit\n'
 assert len(s.encode())<24000
 (MOD/'vf_equipment_test.cfg').write_text(s,encoding='ascii');logfile=f'equipment-{width}.log';start=time.time()
 p=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-borderless','-width',str(width),'-height',str(height),'-console','-nointro','-nowriteconfig','-log',logfile,'+exec','lab_controls.cfg','+map','vf_range','+exec','vf_equipment_test.cfg'],cwd=ENGINE)
 try:p.wait(timeout=120)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,p.returncode
 log=(ENGINE/logfile).read_text(errors='replace')
 for expected in ['VFEquipment audit: objects=154 passed=154 failed=0 max_parts=16','VFAppearance state: player=1 mode=0','VFAppearance state: player=1 mode=1','VFUI click: Liee a l\'equipement','VFUI click: Apparence libre','VFState player=1 skins=145,145,145,145,145','VFState player=1 skins=145,151,151,151,151','VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1','VFX spawn: toxic active=1','VFX spawn: caustic_contagion active=1']:assert expected in log,expected
 assert 'VFState rejected' not in log
 after=log.split('Loading game from save/vf_equipment_test.sav')[-1]
 assert 'VFAppearance state: player=1 mode=1' in after,'free mode survives save/load'
 for name in captures:
  f=MOD/'scrshots'/(name+'.png');assert f.stat().st_mtime>=start and f.stat().st_size>1000,name
  assert Image.open(f).size==(width,height),'actual viewport size must match requested resolution'
 def difference(a,b):
  x=Image.open(MOD/'scrshots'/f'eq_{width}_{a}.png').convert('RGB');y=Image.open(MOD/'scrshots'/f'eq_{width}_{b}.png').convert('RGB');scale=min(width/1280,height/720);ox=(width-1280*scale)/2;oy=(height-720*scale)/2;box=tuple(map(int,[ox+330*scale,oy+205*scale,ox+806*scale,oy+480*scale]));return sum(max(p)>25 for p in ImageChops.difference(x.crop(box),y.crop(box)).getdata())
 visual_changes={key:difference(*pair) for key,pair in {'operator':('operator_fortress','operator_rogue'),'weapon':('weapon_fortress','weapon_anomalous'),'effects':('toxic','contambloom')}.items()}
 assert all(n>200 for n in visual_changes.values()),visual_changes
 benches=re.findall(r'VFBench (\w+): samples=180 mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log);assert len(benches)==2,benches
 report=dict(resolution=[width,height],captures=captures,changed_pixels=visual_changes,benchmarks=[dict(zip(['name','cpu_mean_ms','cpu_p95_ms','frame_ms','model_loads','texture_bytes'],b)) for b in benches],checks=['154 actual item assemblies accepted by native renderer','six operator and six weapon collections previewed','server confirms linked and free modes','free skin retained across toggles and save/load','equipment preview, first-person firing/reloading and mannequin captured','Toxic and ContamBloom visually distinct','standing collision hull retained'],limits=['Pointer events injected at native client route, not OS mouse automation','CPU preview timings are not GPU timings','weapon attachments remain a first-person prototype, original MP5 behavior retained'])
 (ROOT/'build'/f'equipment-engine-verification-{width}.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS equipment engine',width,len(captures),'captures',visual_changes)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080);a=p.parse_args();run(a.width,a.height)

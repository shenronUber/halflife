"""Native visual workshop: real screenshots, all module combinations and timing."""
import json,re,subprocess,time
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_visual'

def run():
 captures=[]
 def capture(name):
  captures.append(name);return f'wait 50\nscreenshot scrshots/{name}.png\nwait 4\n'
 script='wait 220\ndeveloper 1\ncon_notifytime 0\nfps_max 300\nweapon_9mmAR\nwait 90\nvf_visual_enabled 0\nvf_skins\nwait 60\nvf_animation_time 0\n'
 script+='vf_skin_all 127\nvf_skin_set 2 9\nvf_skin_set 4 0\nvf_skin_commit\n'+capture('visual_seams')
 script+='vf_visual_bench mixed\nwait 900\n'
 for id in [0,44,145,146,151]:script+=f'vf_skin_all {id}\n'+capture(f'visual_skin_{id}')
 script+='vf_skin_all 145\nvf_skin_set 2 146\nvf_skin_set 4 147\nvf_skin_commit\n'+capture('visual_palette_mix')+'vf_visual_bench shared_mesh\nwait 900\n'
 script+=''.join(f'vf_weapon_part {z} 0\n' for z in range(4))
 script+='vf_skin_tab 2\nwait 20\nvf_animation_time 0\n'+capture('visual_mp40')
 script+='vf_weapon_equip\nvf_skins\n'+capture('visual_mp40_hand')+'vf_skins\nvf_skin_tab 2\n'
 for name,parts in [('hybrid',[0,1,2,1]),('nail',[1,1,1,1]),('thompson',[2,2,2,2])]:
  script+=''.join(f'vf_weapon_part {z} {v}\n' for z,v in enumerate(parts))
  script+=capture('visual_'+name)+'vf_visual_bench '+name+'\nwait 900\nvf_weapon_equip\nvf_skins\n'+capture('visual_'+name+'_hand')
  script+='+attack\nwait 30\n-attack\nwait 50\n+reload\nwait 80\nscreenshot scrshots/visual_'+name+'_reload.png\nwait 4\n-reload\nwait 150\nvf_skins\nvf_skin_tab 2\n'
  captures.append('visual_'+name+'_reload')
 script+='vf_engine_audit\nvf_weapon_audit\nvf_engine_stats\nvf_skins\ncmd vf_body_info\nsave vf_visual_smoke\nwait 80\nload vf_visual_smoke\nwait 220\nvf_skins\nvf_skin_tab 0\n'+capture('visual_restored')+'vf_skins\nwait 5\nquit\n'
 (MOD/'vf_visual_test.cfg').write_text(script,encoding='ascii')
 command=[str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-windowed','-width','1280','-height','720','-console','-nointro','-log','visual-test.log','+exec','lab_controls.cfg','+map','vf_range','+exec','vf_visual_test.cfg']
 start=time.time();p=subprocess.Popen(command,cwd=ENGINE)
 try:p.wait(timeout=180)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,p.returncode
 log=(ENGINE/'visual-test.log').read_text(errors='replace')
 for text in ['VFEngine audit: loaded=219 failed=0','VFVisual audit: combinations=81 failed=0','VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1','VFVisual equipped: 0,1,2,1','Loading game from save/vf_visual_smoke.sav']:
  assert text in log,text
 assert 'VFState player=1 skins=145,145,146,145,147' in log.split('Loading game from save/vf_visual_smoke.sav')[-1]
 for name in captures:
  path=MOD/'scrshots'/(name+'.png');assert path.stat().st_mtime>=start and path.stat().st_size>1000,name
 changes={}
 for left,right,box in [('visual_skin_145','visual_skin_146',(520,185,1240,575)),('visual_mp40','visual_hybrid',(430,185,1235,575)),('visual_hybrid','visual_thompson',(430,185,1235,575))]:
  a=Image.open(MOD/'scrshots'/(left+'.png')).convert('RGB').crop(box);b=Image.open(MOD/'scrshots'/(right+'.png')).convert('RGB').crop(box)
  changed=sum(max(pixel)>30 for pixel in ImageChops.difference(a,b).getdata());assert changed>500,(left,right,changed);changes[left+' -> '+right]=changed
 benchmarks=[dict(zip(['name','samples','mean_ms','p95_ms','frame_ms','loads','texture_bytes'],row)) for row in re.findall(r'VFBench (\w+): samples=(\d+) mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log)]
 assert len(benchmarks)==5,benchmarks
 report={'checks':['154 appearances and 65 original TFC models accepted','81 module assemblies resolve with valid bone sockets','standing collision hull and rifle preserved','skin families survive save/load','shoot/reload exercised on three hybrid configurations'],'benchmarks':benchmarks,'captures':captures,'timing_scope':'Native preview CPU submission and wall time between frames; 180 samples after 30 warm-up frames, capped at 300 fps; not GPU profiling'}
 report['visual_changed_pixels']=changes
 (ROOT/'build/visual-engine-verification.json').write_text(json.dumps(report,indent=2))
 print(f'PASS: visual workshop, {len(captures)} captures, 5 benchmarks')

if __name__=='__main__':run()

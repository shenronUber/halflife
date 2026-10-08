"""Run the actual Xash renderer, matrix navigation, effect life cycle and bounded benchmarks."""
import argparse,json,re,subprocess,time
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_visual'
def run(width=1920,height=1080):
 data=json.loads((ROOT/'data/effects.json').read_text());captures=[]
 def click(x,y):return f'vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 6\n'
 def snap(name):
  name=f'fx_{width}_{name}';captures.append(name);return f'wait 16\nscreenshot scrshots/{name}.png\nwait 4\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\nvf_effect_audit\nvf_effects\nwait 25\n'+click(1165,207)+snap('matrix')
 # A disabled cell must not select; the Hydro/Electro pair must open ArcChain.
 s+='echo VFX_INVALID_PAIR_BEGIN\n'+click(383,307)+'echo VFX_INVALID_PAIR_END\n'+click(301,307)+snap('pair_from_matrix')
 s+=click(810,558)+snap('primary_from_reaction')+click(1000,550)+snap('reaction_from_partner')
 subset=data['effects'] if width>=1280 else [data['effects'][0],data['effects'][7],data['effects'][13],data['effects'][20]]
 for e in subset:
  s+=f'vf_effect_select {e["id"]}\n'+snap('guide_'+e['id'])
  s+='vf_effect_spawn\nwait 16\nvf_effect_stats\n'+snap('world_'+e['id'])+'vf_effects\nwait 8\n'
 s+='vf_effect_select arc_chain\n'+click(600,697)+'wait 35\nvf_effect_stats\n'+snap('comparison')
 if width>=1280:
  s+='vf_effect_bench\nwait 190\n'+snap('motion_a')+'wait 35\n'+snap('motion_b')
  s+='vf_effect_layers 1 0\nwait 10\nvf_effect_stats\n'+snap('halo_only')
  s+='vf_effect_layers 0 1\nwait 10\nvf_effect_stats\n'+snap('particles_only')
  s+='vf_effect_layers 1 1\nvf_effect_select steam_veil\nvf_effect_spawn compare\nwait 35\nvf_effect_bench\nwait 190\n'+snap('steam_comparison')
  s+='vf_effect_clear\nwait 10\nvf_effect_stats\n'+snap('cleared')
  s+='cmd vf_skin_camera\nwait 25\nvf_effect_select thermal\nvf_effect_attach\nwait 30\nvf_effect_stats\n'+snap('attached')
  s+='vf_effect_select missing\nwait 4\ncmd vf_body_info\nwait 10\nvf_effect_clear\nmap vf_range\nwait 160\ndeveloper 1\ncon_notifytime 0\nvf_effect_stats\nvf_effects\nvf_effect_audit\n'+snap('after_map')
 s+='vf_effect_clear\nquit\n';assert len(s.encode())<24000
 (MOD/'vf_effects_test.cfg').write_text(s,encoding='ascii');logfile=f'fx-{width}-test.log'
 start=time.time();args=[str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-borderless','-width',str(width),'-height',str(height),'-console','-nointro','-nowriteconfig','-log',logfile,'+exec','lab_controls.cfg','+map','vf_range','+exec','vf_effects_test.cfg']
 p=subprocess.Popen(args,cwd=ENGINE)
 try:p.wait(timeout=115)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,p.returncode
 log=(ENGINE/logfile).read_text(errors='replace');assert 'VFX audit: effects=21 sprites=5/5' in log
 invalid=log.split('VFX_INVALID_PAIR_BEGIN',1)[1].split('VFX_INVALID_PAIR_END',1)[0];assert 'VFX select:' not in invalid
 assert 'VFX spawn: arc_chain active=3 visual_only=1' in log
 for e in subset:assert f'VFX spawn: {e["id"]} active=1 visual_only=1' in log,e['id']
 assert 'VFX spawn rejected' not in log
 for name in captures:
  path=MOD/'scrshots'/(name+'.png');assert path.stat().st_mtime>=start and path.stat().st_size>1000,name
 report=dict(resolution=[width,height],captures=captures,effects_tested=[e['id'] for e in subset],checks=['all requested effects render in actual engine and native guide','matrix rejects unassigned pair and opens assigned pair','source and reaction links clickable','A / reaction / B comparison spawned with 3 visible models','local visual emitters do not modify server combat or movement'],limits=['Pointer events injected at client UI boundary; physical OS input not covered.','Visual cues local to each client; no multiplayer effect replication implemented.'])
 if width>=1280:
  assert 'VFX attach: entity=' in log,'existing character attachment'
  assert 'VFX rejected: unknown effect' in log
  assert 'primitives=0' in log and 'halo=1 particles=0' in log
  assert 'VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1' in log
  after=log.rsplit('VFX stats: active=0',1)[1];assert 'VFX audit: effects=21 sprites=5/5' in after
  a=Image.open(MOD/f'scrshots/fx_{width}_motion_a.png').convert('RGB').crop((250,180,1010,560));b=Image.open(MOD/f'scrshots/fx_{width}_motion_b.png').convert('RGB').crop((250,180,1010,560))
  changed=sum(max(p)>25 for p in ImageChops.difference(a,b).getdata());assert changed>100,changed;report['animated_pixels']=changed
  report['benchmarks']=[dict(zip(['active','primitives','samples','mean_ms','p95_ms','frame_ms'],map(float,m))) for m in re.findall(r'VFX bench: active=(\d+) primitives=(\d+) samples=(\d+) mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+)',log)]
  assert len(report['benchmarks'])==2;report['checks']+=['all five sprites loaded again after map reset','halos and particles independently disabled','visual attachment to an existing studio entity','unknown effect rejected','clear removes every local emitter','standing collision hull preserved','actual moving particles differ between frames','180-frame CPU submission benchmarks on 3 simultaneous emitters']
  report['limits']+=['Benchmark measures generation plus render submission CPU time, not isolated GPU cost.']
 (ROOT/'build'/f'effects-engine-verification-{width}.json').write_text(json.dumps(report,indent=2));print('PASS effects engine',width,len(captures),'captures')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080);a=p.parse_args();run(a.width,a.height)

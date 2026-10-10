"""Exercise first-person status feedback against real authoritative state messages."""
import json,re,shutil,time
from pathlib import Path
import weapon_fx_test as base
ROOT=base.ROOT
EFFECTS=json.loads((ROOT/'data/effects.json').read_text())['effects']
def section(log,name):return log.split('STATUS_VIS_BEGIN_'+name,1)[1].split('STATUS_VIS_END_'+name,1)[0]
def stats(text):
 matches=re.findall(r'VFStatus visual: local=(\d+) active=(\d+) edges=(\d+) primitives=(\d+) arms=(\d+) dominant=(\w+)',text)
 assert matches,text[-2000:]
 return [int(x) for x in matches[-1][:5]]+[matches[-1][5]]
def stage_feedback(name):
 base.OUT=ROOT/'build/status-feedback-native'
 engine,mod=base.stage(name)
 shutil.copy2(ROOT/'build/client/client.dll',mod/'cl_dlls/client.dll')
 shutil.copy2(ROOT/'build/server/hl.dll',mod/'dlls/hl.dll')
 shutil.copytree(ROOT/'generated/effects',mod/'sprites/vf_effects',dirs_exist_ok=True)
 shutil.copytree(ROOT/'generated/status-decals',mod/'sprites/vf_status',dirs_exist_ok=True)
 return engine,mod
def native():
 engine,mod=stage_feedback('single')
 script='gl_vsync 0\nfps_max 60\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_voices 0\nvf_voice_subtitles 0\nweapon_9mmAR\nvf_operator\nwait 20\n'+base.click(1220,40)+'cl_bob 0\ncmd vf_fx_camera concrete\nwait 30\ncmd vf_status_dev 1\nwait 12\n'
 captures=[]
 def block(name,commands):
  nonlocal script
  script+='echo STATUS_VIS_BEGIN_'+name+'\n'+commands+'vf_status_visual_stats\necho STATUS_VIS_END_'+name+'\n'
 def capture(name):captures.append(name);return 'screenshot scrshots/'+name+'.png\nwait 2\n'
 block('inactive',capture('status_clear')+'vf_status_decal_audit\n')
 for e in EFFECTS:
  block(e['id'],'cmd vf_status_clear\nwait 5\ncmd vf_status_apply '+e['id']+' 6\nwait 22\n'+capture('status_'+e['id']))
 block('motion','cmd vf_status_clear\nwait 6\ncmd vf_status_apply thermal 6\nwait 24\n'+capture('status_thermal_motion_a')+'vf_status_visual_stats\nwait 17\n'+capture('status_thermal_motion_b'))
 for background in ('sky','metal'):
  commands='vf_status_visual_layers 0 0\ncmd vf_status_clear\ncmd vf_fx_camera '+background+'\nwait 24\n'+capture('status_bg_'+background)
  for id in ('thermal','cryo','caustic_contagion'):
   commands+='cmd vf_status_clear\nwait 4\ncmd vf_status_apply '+id+' 6\nvf_status_visual_layers 1 0\nwait 24\n'+capture('status_'+background+'_'+id)
  block('background_'+background,commands)
 script+='cmd vf_status_clear\nvf_status_visual_layers 1 1\ncmd vf_fx_camera concrete\nwait 24\n'
 block('refresh','cmd vf_status_clear\nwait 4\ncmd vf_status_apply thermal 2\nwait 25\ncmd vf_status_apply thermal 6\nwait 10\n')
 block('pair','cmd vf_status_clear\nwait 4\ncmd vf_status_pair hydro electro 6\nwait 22\nvf_status_client\n'+capture('status_atomic_arc'))
 block('four','cmd vf_status_clear\nwait 4\ncmd vf_status_apply hydro 6\ncmd vf_status_apply cryo 6\ncmd vf_status_apply toxic 6\ncmd vf_status_apply ward 6\nwait 22\n'+capture('status_four'))
 block('layers_off','vf_status_visual_layers 0 0\nwait 16\n'+capture('status_layers_off'))
 block('layers_on','vf_status_visual_layers 1 1\nwait 16\n'+capture('status_layers_on'))
 block('arms_only','vf_status_visual_layers 0 1\ncmd vf_status_clear\nwait 6\ncmd vf_status_apply cryo 6\nwait 22\n'+capture('status_arms_only'))
 block('arms_base','vf_status_visual_layers 0 0\nwait 16\n'+capture('status_arms_base'))
 block('reload','vf_status_visual_layers 1 1\ncmd vf_status_clear\nwait 6\ncmd vf_status_apply thermal 6\nwait 22\n+attack\nwait 2\n-attack\nwait 16\n+reload\nwait 22\n'+capture('status_reload')+'-reload\n')
 block('third_person','thirdperson\nwait 16\n'+capture('status_third_person'))
 block('first_person','firstperson\nwait 16\n')
 block('expiry','cmd vf_status_clear\nwait 6\ncmd vf_status_apply ward .3\nwait 60\n'+capture('status_expired'))
 block('clear','cmd vf_status_apply toxic 6\nwait 22\ncmd vf_status_clear\nwait 12\n')
 block('damage_burn','cmd vf_voice_test burn\nwait 22\n')
 block('death','cmd vf_status_apply thermal 6\nwait 22\ncmd vf_voice_test death\nwait 25\n')
 script+='map vf_fx_range\nwait 180\ndeveloper 1\ncon_notifytime 0\n'+base.click(1220,40)+'wait 25\n'
 block('map_reset','wait 15\n')
 script+='quit\n'
 started=time.time();log=base.run_cfg(engine,mod,'status-feedback',script,timeout=100)
 (ROOT/'build/status-feedback-native.log').write_text(log)
 assert 'VFStatus decals: loaded=16/16 frames=64/64' in log
 for e in EFFECTS:
  s=stats(section(log,e['id']));assert s[:3]==[1,1,4] and s[3]>0 and s[4:]==[1,e['id']],(e['id'],s)
 for name in ('inactive','expiry','clear','death','map_reset'):
  s=stats(section(log,name));assert s[1:5]==[0,0,0,0] and s[-1]=='none',(name,s)
 motion=re.findall(r'VFStatus decal: effect=thermal frame=(\d+) next=(\d+) blend=([\d.]+)',section(log,'motion'));assert len(motion)==2 and motion[0]!=motion[1],motion
 assert stats(section(log,'refresh'))[1:3]==[1,4]
 pair=section(log,'pair');assert stats(pair)[-1]=='arc_chain';assert 'effect=arc_chain' in pair and 'effect=hydro' not in pair and 'effect=electro' not in pair
 assert stats(section(log,'four'))[1:3]==[4,4]
 assert stats(section(log,'layers_off'))[2:5]==[0,0,0]
 assert stats(section(log,'layers_on'))[2]==4 and stats(section(log,'layers_on'))[4]==1
 assert stats(section(log,'arms_only'))[2:5]==[0,0,1]
 assert stats(section(log,'damage_burn'))[4:]==[1,'thermal']
 assert stats(section(log,'reload'))[4]==1
 assert stats(section(log,'third_person'))[1:3]==[1,4] and stats(section(log,'third_person'))[4]==0
 for name in captures:assert (mod/'scrshots'/(name+'.png')).stat().st_mtime>=started,name
 for error in ('Host_Error','SV_Error','VFState rejected','S_LoadSound:'):assert error not in log,error
 from PIL import Image,ImageChops,ImageStat
 def pixels(name):return Image.open(mod/'scrshots'/(name+'.png')).convert('RGB')
 def difference(a,b,rect):return sum(ImageStat.Stat(ImageChops.difference(a.crop(rect),b.crop(rect))).mean)/3
 for background in ('sky','metal'):
  baseline=pixels('status_bg_'+background);w,h=baseline.size
  center=(int(w*.28),int(h*.24),int(w*.72),int(h*.53))
  edge=(0,int(h*.18),int(w*.12),int(h*.68))
  for id in ('thermal','cryo','caustic_contagion'):
   image=pixels('status_'+background+'_'+id)
   assert difference(baseline,image,center)<.1,(background,id,'center changed')
   assert difference(baseline,image,edge)>1,(background,id,'edge not visible')
 a=pixels('status_thermal_motion_a');b=pixels('status_thermal_motion_b');w,h=a.size
 assert difference(a,b,(0,0,w,int(h*.12)))>.3,'Native flipbook must actually animate the displayed pixels'
 report=dict(effects=21,captures=[str(mod/'scrshots'/(n+'.png')) for n in captures],checks=['16 custom flipbooks loaded with 64 native frames; visible pixel animation','clear aiming area and visible borders verified on bright sky and dark metal backgrounds','all 8 elements, 8 reactions and 5 tactical states render 4 edges and fitted first-person arm shells','reaction consumes component states and displays only the result','refresh remains visible','4 simultaneous states retain separate edge signatures','independent screen and arm layer controls','arm shell retained during accepted reload','expiry, clear, death and map reset remove both layers'],limits=['Fitted R1 hands and sleeves receive the shell; legacy developer weapons retain their own presentation.','Native screenshot review complements the state and draw counters.'])
 (ROOT/'build/status-feedback-verification.json').write_text(json.dumps(report,indent=2))
 print('PASS first-person status feedback',report['checks'],flush=True)
def multiplayer():
 import subprocess
 from weapon_fx_multiplayer_test import put,wait_log,read
 a,am=stage_feedback('mp-a');b,bm=stage_feedback('mp-b')
 for engine,mod in ((a,am),(b,bm)):
  (engine/'feedback-peer.log').unlink(missing_ok=True)
  for phase in ('init','next','clear','quit'):
   put(mod/('feedback-'+phase+'.cfg'),'wait 15\nexec feedback-'+phase+'.cfg\n')
  put(mod/'feedback-peer.cfg','developer 1\ngl_vsync 0\nfps_max 60\ncon_notifytime 0\nexec feedback-init.cfg\n')
 (a/'feedback-server.log').unlink(missing_ok=True)
 common=['-rodir',base.STEAM,'-game','vf_fx_test','-console','-nointro']
 server=subprocess.Popen([str(a/'xash.exe'),*common,'-log','feedback-server.log','+ip','127.0.0.1','-port','27115','+rcon_password','vf_feedback_test','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+vf_native_models','1','+vf_voices','0','+map','vf_fx_range'],cwd=a,creationflags=subprocess.CREATE_NO_WINDOW)
 children=[]
 try:
  wait_log(a/'feedback-server.log','4 player server started',server)
  def launch(engine,port,name):
   p=subprocess.Popen([str(engine/'xash3d.exe'),*common,'-borderless','-width','1280','-height','720','-nowriteconfig','-log','feedback-peer.log','-clientport',str(port),'+developer','1','+gl_vsync','0','+fps_max','60','+name',name,'+connect','127.0.0.1:27115','+exec','feedback-peer.cfg'],cwd=engine);children.append(p);return p
  pa=launch(a,27116,'FEEDBACK_A')
  wait_log(a/'feedback-peer.log','VFStatus received: player=1',pa)
  init='developer 1\ncon_notifytime 0\nvf_voice_subtitles 0\nweapon_9mmAR\nwait 30\n'
  put(am/'feedback-init.cfg',init+'cmd vf_fx_camera concrete\ncmd vf_status_dev 1\nwait 12\ncmd vf_status_apply thermal 30\nwait 25\nvf_status_visual_stats\necho FEEDBACK_A_READY\nexec feedback-next.cfg\n')
  wait_log(a/'feedback-peer.log','FEEDBACK_A_READY',pa)
  pb=launch(b,27117,'FEEDBACK_B')
  wait_log(b/'feedback-peer.log','VFStatus received: player=1 developer=1 active=1',pb)
  put(bm/'feedback-init.cfg',init+'cmd vf_fx_camera side\nwait 25\necho FEEDBACK_B_REMOTE_BEGIN\nvf_status_visual_stats\nvf_status_client\nvf_engine_stats\nscreenshot scrshots/status_remote_only.png\necho FEEDBACK_B_REMOTE_END\necho FEEDBACK_B_READY\nexec feedback-next.cfg\n')
  wait_log(b/'feedback-peer.log','FEEDBACK_B_READY',pb)
  put(bm/'feedback-next.cfg','cmd vf_status_dev 1\nwait 12\ncmd vf_status_apply cryo 30\nwait 25\nvf_status_visual_stats\nscreenshot scrshots/status_local_cryo_remote_fire.png\necho FEEDBACK_B_OWN\nexec feedback-clear.cfg\n')
  wait_log(b/'feedback-peer.log','FEEDBACK_B_OWN',pb)
  put(am/'feedback-next.cfg','cmd vf_status_clear\nwait 25\nvf_status_visual_stats\necho FEEDBACK_A_CLEAR\nexec feedback-clear.cfg\n')
  wait_log(a/'feedback-peer.log','FEEDBACK_A_CLEAR',pa)
  put(bm/'feedback-clear.cfg','wait 25\necho FEEDBACK_B_AFTER_REMOTE_CLEAR\nvf_status_visual_stats\necho FEEDBACK_B_STILL_OWN\nexec feedback-quit.cfg\n')
  wait_log(b/'feedback-peer.log','FEEDBACK_B_STILL_OWN',pb)
  put(am/'feedback-clear.cfg','rcon_password vf_feedback_test\nrcon sv_cheats 0\nwait 90\nvf_status_visual_stats\necho FEEDBACK_A_REVOKED\nexec feedback-quit.cfg\n')
  wait_log(a/'feedback-peer.log','FEEDBACK_A_REVOKED',pa)
  wait_log(b/'feedback-peer.log','VFStatus received: player=2 developer=0 active=0',pb)
  put(bm/'feedback-quit.cfg','wait 25\nvf_status_visual_stats\nquit\n')
  put(am/'feedback-quit.cfg','quit\n')
  for child in children:child.wait(timeout=15);assert child.returncode==0
  logs=[read(engine/'feedback-peer.log') for engine in (a,b)]
  remote=logs[1].split('FEEDBACK_B_REMOTE_BEGIN',1)[1].split('FEEDBACK_B_REMOTE_END',1)[0]
  assert stats(remote)[1:5]==[0,0,0,0] and 'player=1 effect=thermal' in remote,remote
  draws=re.findall(r'VFEngine remote weapons drawn=(\d+)',remote);assert draws and int(draws[-1])>0,remote
  assert stats(logs[1].split('FEEDBACK_B_AFTER_REMOTE_CLEAR',1)[1].split('FEEDBACK_B_STILL_OWN',1)[0])[4:]==[1,'cryo']
  for log in logs:assert stats(log)[1:5]==[0,0,0,0]
  report=dict(clients=2,checks=['late join renders remote active state without contaminating local screen or arms','local Cryo remains while a different player has Thermal','clearing remote state preserves own feedback','revoking developer state clears both clients'],captures=[str(bm/'scrshots/status_remote_only.png'),str(bm/'scrshots/status_local_cryo_remote_fire.png')])
  (ROOT/'build/status-feedback-multiplayer-verification.json').write_text(json.dumps(report,indent=2));print('PASS status feedback multiplayer',report['checks'],flush=True)
 finally:
  for child in children:
   if child.poll() is None:child.terminate();child.wait(10)
  if server.poll() is None:server.terminate();server.wait(10)
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['native','multiplayer','all'],default='native');args=parser.parse_args()
 if args.mode in ('native','all'):native()
 if args.mode in ('multiplayer','all'):multiplayer()


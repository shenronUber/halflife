"""Three native clients: remote elemental death, respawn and late corpse sync."""
import json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
OUT=ROOT/'build/death-visual'
def run(motion="auto",effect="electro"):
 import json
 sys.path.insert(0,str(ROOT))
 from studio_assets import Studio
 atlas=json.loads((ROOT/"assets/animations/death-atlas.json").read_text());effects=[p["effect"] for p in atlas["profiles"]];effect_id=effects.index(effect)
 model=Studio(ROOT/"generated/deaths/persona_death.mdl");motions={m["id"]:m["sequence"] for m in atlas["motions"]}
 sequences=[motions[id] for id in atlas["profiles"][effect_id]["motions"]] if motion=="auto" else [motions[motion]]
 engines=[harness.stage('death-peer-'+effect+'-'+motion+'-'+str(i)) for i in range(3)]
 setup='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\ns_show 1\nr_drawviewmodel 0\ncmd give weapon_9mmAR\nweapon_9mmAR\nwait 10\ncmd vf_peer_pose\nwait 10\n'
 observer=setup+''.join(f'wait 20\necho SAMPLE_{i}\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/remote_{i:02}.png\n' for i in range(45))+'quit\n'
 actor=setup+'vf_reference\nwait 90\nvf_item gign_head_salvager\nvf_item gign_torso_warden\nvf_item gign_gloves_gign\nvf_item gign_legs_salvager\nvf_item gign_boots_gign\nvf_commit\nwait 30\nvf_character\nwait 30\ncmd vf_peer_pose\nwait 10\ncmd vf_death_test left_arm electro\nwait 180\necho DEAD_PLAYER\nvf_death_client\nvf_engine_stats\n+attack\nwait 20\n-attack\nwait 35\necho RESPAWNED_PLAYER\ncmd vf_body_info\nvf_death_client\nvf_engine_stats\nwait 80\nvf_reference\nwait 90\nvf_item gign_torso_gign\nvf_commit\nwait 10\nvf_character\nwait 760\necho EXPIRED_REMOTE\nvf_death_client\nwait 10\nquit\n'
 late=setup+'echo LATE_JOIN\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/late_corpse.png\nwait 150\necho LATE_STILL\nvf_death_client\nvf_engine_stats\nquit\n'
 actor=actor.replace('vf_death_test left_arm electro','vf_death_test left_arm '+effect+' '+motion)
 for engine,cfg in zip(engines,[observer,actor,late]):(engine/'vf_animation/death_peer.cfg').write_text(cfg,encoding='ascii')
 common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-console','-nointro']
 server=subprocess.Popen([str(engines[0]/'xash.exe'),*common,'-log','death-server.log','+ip','127.0.0.1','-port','27075','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range'],cwd=engines[0],creationflags=subprocess.CREATE_NO_WINDOW)
 children=[];started=time.monotonic()
 def launch(i):
  e=engines[i];children.append(subprocess.Popen([str(e/'xash3d.exe'),*common,'-windowed','-width','960','-height','600','-nowriteconfig','-log','death-peer.log','-clientport',str(27076+i),'+name','DeathLab_'+str(i),'+connect','127.0.0.1:27075','+exec','death_peer.cfg'],cwd=e))
 try:
  time.sleep(2);assert server.poll() is None;launch(0);time.sleep(2);launch(1);time.sleep(9);launch(2)
  for p in children:p.wait(timeout=55);assert p.returncode==0
 finally:
  for p in children+[server]:
   if p.poll() is None:p.terminate();p.wait(10)
 logs=[(e/'death-peer.log').read_text(errors='replace') for e in engines];srv=(engines[0]/'death-server.log').read_text(errors='replace');OUT.mkdir(exist_ok=True)
 for i,log in enumerate(logs):
  (OUT/f'peer-{effect}-{motion}-{i}.log').write_text(log)
  assert 'VFCorpse received' in log and f'mask=2 effect={effect_id}' in log,(i,log[-2000:])
  assert 'rejected=0' in log and 'VFState rejected' not in log,i
  assert 'Could not load' not in log and 'Host_Error' not in log,i
 matches=re.findall(fr'VFDeathVisual corpse=(\d+) victim=2 mask=2 effect={effect_id} sequence=(\w+)',srv);assert len(matches)==1 and matches[0][1] in sequences,srv[-4000:]
 corpse,sequence=matches[0];sequence_index=model.sequences.index(sequence)
 assert re.search(r'VFCorpse client entity='+corpse+fr' mask=2 effect={effect_id} .*sequence='+str(sequence_index)+r' frame=[\d.]+ model=models/vf_deaths/persona_death.mdl',logs[0]),'observer did not see animated remote corpse'
 received=re.findall(r'VFCorpse client entity='+corpse+fr' mask=2 effect={effect_id} body=\d+ skins=([\d,]+)',logs[1]);assert len(received)>1 and len(set(received))==1,received
 assert len(set(received[0].split(',')))>1,'mixed outfit was not captured'
 late_match=re.search(r'VFCorpse received entity='+corpse+fr' mask=2 effect={effect_id} age=([\d.]+)',logs[2]);assert late_match and float(late_match[1])>2,late_match
 assert f'skins={received[0]}' in logs[2] and 'frame=255.0 model=models/vf_deaths/persona_death.mdl' in logs[2],'late join did not receive settled corpse with original clothes'
 alive=logs[1].split('RESPAWNED_PLAYER')[1].split('EXPIRED_REMOTE')[0];assert 'VFBody player=2' in alive and 'model=models/vf_r01/r01_tp.mdl' in alive and 'VFCorpse client' in alive,'respawn broke corpse or original player'
 assert 'VFCorpse client' not in logs[1].split('EXPIRED_REMOTE')[1]
 spawned=re.findall(fr'VFFragment spawn entity=(\d+) body=(\d+) effect={effect_id} whole=(\d+)',srv);assert len(spawned)==4 and sum(int(f[2]) for f in spawned)==1
 whole=next(f[0] for f in spawned if f[2]=='1')
 from fragment_skins import pair_skin
 captured=[int(s) for s in received[0].split(',')];expected_skin=pair_skin(captured[1],captured[2])
 for i in range(3):
  assert re.search(fr'VFFragment client entity={whole} body=16 [^\n]*skin={expected_skin} primary={captured[1]} detail={captured[2]}',logs[i]),('detached glove lost its independent finish',i)

 for i in (0,1):
  trail=re.findall(fr'VFFragment client entity={whole} body=16 effect={effect_id} whole=1 age=[\d.]+ blood=(\d+) elemental=(\d+) travel=([\d.]+)',logs[i]);assert trail and max(int(t[0]) for t in trail)>0 and max(int(t[1]) for t in trail)>0 and max(float(t[2]) for t in trail)>10,(i,trail)
 assert re.search(fr'VFFragment client entity={whole} body=16 effect={effect_id} whole=1 age=[\d.]+ blood=0 elemental=0',logs[2]),'late join replayed an old limb explosion'
 # One-shot native sound diagnostics must reach both connected observers,
 # while corpse/fragment catch-up must not replay a past cry or either SFX.
 for i in (0,1):
  events=re.findall(r'VFDeathSfx received: entity=(\d+) layer=(death|dismemberment) effect='+effect+r' channel=(\d+)',logs[i])
  assert sorted(events)==sorted([('2','death','4'),(corpse,'dismemberment','3')]),(i,events)
  assert len(re.findall(r'VFDeath received: entity=2 actor=\w+ cause='+effect,logs[i]))==1,i
 assert 'VFDeathSfx received:' not in logs[2],'late observer replayed an old sound effect'
 assert 'VFDeath received: entity=2' not in logs[2],'late observer replayed an old death cry'
 assert len(re.findall(r'VFDeathSfx play .*layer=death effect='+effect,srv))==1
 assert len(re.findall(r'VFDeathSfx play .*layer=dismemberment effect='+effect,srv))==1
 report=dict(effect=effect,motion=sequence,clients=3,seconds=round(time.monotonic()-started,2),corpse=int(corpse),skins=received[0],late_join_age=float(late_match[1]),checks=['remote elemental animation and missing left arm','real projected arm and elemental/blood trails on both connected clients','late observer receives existing fragments without replaying an old explosion','five-zone outfit retained after victim respawn and equipment change','detached sleeve/glove pair replicated unchanged to both live clients and late observer','late join receives age, mask, effect and settled pose','three independent positional audio layers reach both connected clients once','late observer does not hear an old death','all corpse assemblies accepted by native renderer','15-second expiry removes client corpse state'])
 (OUT/('multiplayer-'+effect+'-'+motion+'-verification.json')).write_text(json.dumps(report,indent=2));print('PASS native multiplayer deaths',json.dumps(report),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--motion',choices=['auto','quaternius','kaykit_a','kaykit_b'],default='auto');p.add_argument('--effect',choices=['electro','corrosion'],default='electro');args=p.parse_args();run(args.motion,args.effect)

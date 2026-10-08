"""Fitted GIGN appearances on two real clients, including a late join."""
import json,subprocess,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from play_personas import ROOT,ENGINE,MOD,deploy
from native_multiplayer_test import prepare_peer

def run():
 deploy();peer=prepare_peer('vf_personas')
 assert (peer/'vf_visual/gameinfo.txt').exists(),'Visual resource fallback must already be installed for this peer.'
 common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_personas','-console','-nointro']
 start='wait 220\ndeveloper 1\ncon_notifytime 0\nfps_max 100\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 25\ncmd vf_peer_pose\nwait 40\nvf_skins\nwait 30\n'
 first=start+'vf_skin_all 179\nvf_skin_commit\nwait 35\nvf_skins\nwait 1500\nvf_engine_stats\nscreenshot scrshots/persona_peer_a.png\nwait 10\n+forward\nwait 15\n-forward\nwait 250\nquit\n'
 second=start+'vf_skin_all 177\nvf_skin_set 0 181\nvf_skin_set 2 178\nvf_skin_commit\nwait 35\nvf_skins\nwait 400\nvf_engine_stats\nscreenshot scrshots/persona_peer_b.png\nwait 10\n+duck\nwait 80\n-duck\nwait 500\nvf_engine_stats\nscreenshot scrshots/persona_peer_move.png\nwait 10\nquit\n'
 (MOD/'persona_peer_a.cfg').write_text(first);(peer/'vf_personas/persona_peer_b.cfg').write_text(second)
 server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','persona-server.log','+ip','127.0.0.1','-port','27045','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW)
 children=[];began=time.time()
 try:
  time.sleep(4);assert server.poll()is None
  def launch(folder,port,cfg,name):
   args=[str(folder/'xash3d.exe'),*common,'-borderless','-width','1920','-height','1080','-nowriteconfig','-log','persona-peer.log','+exec','lab_controls.cfg','-clientport',str(port),'+name',name,'+connect','127.0.0.1:27045','+exec',cfg]
   children.append(subprocess.Popen(args,cwd=folder))
  launch(ENGINE,27046,'persona_peer_a.cfg','Canopy')
  time.sleep(8);launch(peer,27047,'persona_peer_b.cfg','Porcelain')
  for child in children:child.wait(timeout=75);assert child.returncode==0
  for folder in (ENGINE,peer):
   log=(folder/'persona-peer.log').read_text(errors='replace')
   assert 'VFState player=1 skins=179,179,179,179,179'in log
   assert 'VFState player=2 skins=181,177,178,177,177'in log
   assert 'VFState rejected'not in log and 'rejected=0'in log
  files=[]
  for folder,name in [(ENGINE,'a'),(peer,'b'),(peer,'move')]:
   path=folder/'vf_personas/scrshots'/('persona_peer_'+name+'.png');assert path.stat().st_mtime>=began;files.append(str(path))
  (ROOT/'build/personas-multiplayer-verification.json').write_text(json.dumps(dict(clients=2,late_join=True,captures=files,checks=['jungle appearance replicated to late joiner','mixed porcelain head and prehistoric gloves replicated to both clients','native remote-player rendering, movement and crouch exercised'],scope='loopback clients, not Internet hosting'),indent=2))
  print('PASS GIGN multiplayer: two clients, late join, independent five-zone appearances.')
 finally:
  for p in children+[server]:
   if p.poll()is None:p.terminate();p.wait(10)
if __name__=='__main__':run()

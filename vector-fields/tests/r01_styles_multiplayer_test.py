"""Verify R01 texture choices across two clients and a late join on loopback."""
import json,subprocess,time,shutil
from library_engine_test import ROOT,ENGINE,MOD,click
from native_multiplayer_test import prepare_peer

def run():
 peer=prepare_peer('vf_visual')
 common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-console','-nointro']
 start='wait 220\ndeveloper 1\ncon_notifytime 0\nfps_max 100\nweapon_9mmAR\nvf_reference 0\nwait 35\n'
 first=start+'vf_reference_style 4\nvf_commit\nwait 35\n'+click(1220,40)+'wait 2200\nvf_engine_stats\nscreenshot scrshots/r01_styles_peer_a.png\nwait 20\nquit\n'
 second=start+'vf_reference_style 2\nvf_reference_style 6 16\nvf_commit\nwait 35\n'+click(1220,40)+'wait 1000\nvf_engine_stats\nscreenshot scrshots/r01_styles_peer_b.png\nwait 20\nquit\n'
 (MOD/'r01_peer_a.cfg').write_text(first,encoding='ascii')
 (peer/'vf_visual/r01_peer_b.cfg').write_text(second,encoding='ascii')
 server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','r01-styles-server.log','+ip','127.0.0.1','-port','27035','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW)
 children=[];started=time.time()
 try:
  time.sleep(4);assert server.poll()is None
  def launch(folder,port,cfg,name):
   args=[str(folder/'xash3d.exe'),*common,'-borderless','-width','1920','-height','1080','-nowriteconfig','-log','r01-styles-peer.log','+exec','lab_controls.cfg','-clientport',str(port),'+name',name,'+connect','127.0.0.1:27035','+exec',cfg]
   children.append(subprocess.Popen(args,cwd=folder))
  launch(ENGINE,27036,'r01_peer_a.cfg','R01_A')
  time.sleep(8)
  launch(peer,27037,'r01_peer_b.cfg','R01_B')
  for p in children:p.wait(timeout=70);assert p.returncode==0
  logs=[(folder/'r01-styles-peer.log').read_text(errors='replace')for folder in [ENGINE,peer]]
  for log in logs:
   assert 'VFR01 state: player=1 first=4 optic=4 feed=4'in log
   assert 'VFR01 state: player=2 first=2 optic=6 feed=2'in log
   assert 'VFState rejected'not in log
  for i,(folder,name)in enumerate([(ENGINE,'a'),(peer,'b')]):
   path=folder/'vf_visual/scrshots'/f'r01_styles_peer_{name}.png'
   assert path.stat().st_mtime>=started and path.stat().st_size>1000
  # Inspect serialized state fields in a diagnostic string for the independently styled optic module.
  serverLog=(ENGINE/'r01-styles-server.log').read_text(errors='replace')
  assert 'VFR01 styles accepted: player=2 first=2 optic=6 feed=2'in serverLog
  report=dict(clients=2,late_join=True,checks=[
    'first client equips jungle before the second joins',
    'late join receives player 1 jungle choices',
    'both clients receive player 2 medieval choices',
    'player 2 also applies a porcelain optic-module override',
    'authoritative equipment/style packets accepted by both clients'],
    scope='loopback replication; third-person weapon retains its existing stock model')
  (ROOT/'build/r01-styles-multiplayer-verification.json').write_text(json.dumps(report,indent=2))
  print('PASS R01 styles: two clients, late join, independent saved texture choices.')
 finally:
  for p in children:
   if p.poll()is None:p.terminate();p.wait(10)
  if server.poll()is None:server.terminate();server.wait(10)
if __name__=='__main__':run()

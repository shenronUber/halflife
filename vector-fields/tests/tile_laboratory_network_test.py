"""Real peers, including a late join, receive the new room and sealed-joint choices."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import private_copy,port,wait_for_log
from slide_feet_bundle import prepare_slide_feet
from build_tile_laboratory import build
from build_atmosphere import deploy as atmosphere
from build_modular_ambience import deploy as ambience
from tile_laboratory_native_test import expected
OUT=ROOT/'docs/validation/tile-laboratory/network'
def run():
 live=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'));sdk=Path(os.environ.get('VF_RELEASE_SDK',ROOT/'build'))
 stages=[]
 for name in('server','actor','late'):
  engine,mod=prepare_slide_feet('tiles-'+name,server=sdk/'server/hl.dll',client=sdk/'client/client.dll',engine_binaries=live)
  private_copy(build(ensure=True),mod/'maps/vf_tiles.bsp');atmosphere(mod);ambience(mod);stages.append((engine,mod))
 common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-nointro','-nowriteconfig']
 server_port=port();server_engine,mod=stages[0];children=[]
 server=subprocess.Popen([str(server_engine/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-port',str(server_port),'-log','server.log','+developer','1','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+vf_tiles_variant','-1','+vf_modular_seed','6','+map','vf_tiles'],cwd=server_engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 try:
  wait_for_log(server_engine/'server.log','VFModular seed=6 cells=',[server])
  for i,(engine,mod)in enumerate(stages[1:]):
   (mod/'peer.cfg').write_text('gl_vsync 0\nfps_max 60\ndeveloper 1\nwait 10\nexec peer.cfg\n',encoding='ascii')
   child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6',*common,'-windowed','-width','1280','-height','720','-clientport',str(port()),'-log','peer.log','+name',f'tile-peer-{i}','+connect',f'127.0.0.1:{server_port}','+exec','peer.cfg'],cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));children.append(child)
   # Start the late joiner only after the first peer received its player state.
   # Keep both alive until sign-on finishes, then release the actual probes.
   wait_for_log(engine/'peer.log',('client connected at',f'VFState player={i+1} '),[server,*children])
  for engine,mod in stages[1:]:
   pending=mod/'peer.next.cfg'
   pending.write_text('gl_vsync 0\nhost_framerate .0166667\nfps_max 60\ndeveloper 1\ncon_notifytime 0\necho PEER_READY\ncmd vf_tiles_info\ncmd vf_tiles_check\nvf_atmosphere_info\nwait 20\nscreenshot scrshots/peer.png\nwait 25\nquit\n',encoding='ascii')
   pending.replace(mod/'peer.cfg')
  for child in children:child.wait(timeout=80)
 finally:
  for child in[*children,server]:
   if child.poll()is None:child.terminate();child.wait(timeout=8)
 OUT.mkdir(parents=True,exist_ok=True);layout=expected(6);records=[]
 for i,(engine,mod)in enumerate(stages[1:]):
  text=(engine/'peer.log').read_text(errors='replace');shutil.copy2(engine/'peer.log',OUT/f'peer-{i}.log');shutil.copy2(mod/'scrshots/peer.png',OUT/f'peer-{i}.png')
  assert children[i].returncode==0 and 'VFModular check seed=6 candidates=141 mismatches=0'in text
  assert text.index('client connected at')<text.index('PEER_READY'), 'Probe ran before sign-on'
  cells=re.findall(r'VFModular seed=6 cells=([\d,]+)',text);assert ','.join(map(str,layout['cells']))in cells
  rooms=re.findall(r'VFTiles module=(\d+) mask=(\d+) form=(\w+) room=(\d+) forced=(-?\d+)',text)
  unique={int(m):(int(mask),form,int(room),int(forced))for m,mask,form,room,forced in rooms}
  assert len(unique)==4 and {row[1]for row in unique.values()}=={'mono','domino','I','L'}
  for m,(mask,form,room,forced)in unique.items():
   assert forced== -1 and all(layout['rooms'][c]==room for c in range(9)if mask&(1<<c))
  assert 'VFAtmosphere active=1'in text;records.append(unique)
 assert records[0]==records[1]
 (OUT/'network.json').write_text(json.dumps(dict(passed=True,seed=6,peers=records,checks=['all four module forms','server-owned rooms and seams','late-join candidate collisions','atmosphere resources loaded']),indent=2))
 print('PASS tile multiplayer: confirmed sign-on, mixed I/L/domino/mono and late join',flush=True)
if __name__=='__main__':run()

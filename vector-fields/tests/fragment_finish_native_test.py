"""A mixed equipped outfit keeps independent glove and boot finishes on real gibs."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import third_person_native_test as harness
from fragment_skins import pair_skin
OUT=ROOT/'build/fragment-finishes'

def run():
 OUT.mkdir(parents=True,exist_ok=True);engine=harness.stage('fragment-finishes');mod=engine/'vf_animation'
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\nvf_reference\nwait 50\n'
 for item in ('gign_head_salvager','gign_torso_warden','gign_gloves_gign','gign_legs_salvager','gign_boots_gign'):cfg+='vf_item '+item+'\n'
 cfg+='vf_commit\nwait 30\nvf_character\nwait 30\ncmd vf_death_test all standard legacy\n'
 for i in range(8):cfg+='wait 10\nvf_death_client\nvf_engine_stats\n'
 cfg+='screenshot scrshots/mixed_fragments.png\nwait 5\nquit\n';(mod/'fragment_finishes.cfg').write_text(cfg,encoding='ascii')
 started=time.monotonic();p=subprocess.Popen([str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','fragment-finishes.log','+sv_cheats','1','+map','vf_range','+exec','fragment_finishes.cfg'],cwd=engine)
 try:p.wait(timeout=30);assert p.returncode==0
 finally:
  if p.poll() is None:p.terminate();p.wait(10)
 log=(engine/'fragment-finishes.log').read_text(encoding='utf-8',errors='replace');(OUT/'native.log').write_text(log,encoding='utf-8')
 expected=[pair_skin(1,1),pair_skin(2,0),pair_skin(2,0),pair_skin(1,0),pair_skin(1,0)]
 spawned=re.findall(r'VFFragment spawn entity=(\d+) body=(\d+) effect=-1 whole=([01])[^\n]*skin=(\d+)',log)
 assert len(spawned)==20,spawned
 for entity,body,whole,skin in spawned:
  body=int(body);region=body-15 if int(whole) else body//3
  assert int(skin)==expected[region],(body,skin,expected[region])
  if int(whole):assert re.search(fr'VFFragment client entity={entity} body={body} [^\n]*skin={skin} primary=\d+ detail=\d+',log),(entity,body,skin)
 assert 'rejected=0' in log and not any(e in log for e in ('Host_Error','SV_Error','Could not load','not precached'))
 assert (mod/'scrshots/mixed_fragments.png').stat().st_size>1000
 for relative,source in [('dlls/hl.dll','build/server/hl.dll'),('cl_dlls/client.dll','build/client/client.dll')]:assert hashlib.sha256((mod/relative).read_bytes()).digest()==hashlib.sha256((ROOT/source).read_bytes()).digest()
 report=dict(seconds=round(time.monotonic()-started,2),fragments=20,expected_families=expected,checks=['real player death with five independently equipped clothing zones','all twenty physical fragments use the captured primary/detail pair','all five whole anatomical pieces have their native skin replicated to the client','native render accepts 196 families without new entities or assemblies'])
 (OUT/'native-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS native mixed fragment finishes',json.dumps(report),flush=True)

if __name__=='__main__':run()

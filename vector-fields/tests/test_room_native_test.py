"""One short native test of four reactive targets and all eight six-hit procs."""
import hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
from build_test_room import patch
from import_tfc import entities
OUT=ROOT/'build/test-room'
ELEMENTS=['hydro','electro','cryo','thermal','toxic','corrosion','sonic','kinetic']
def run():
 engine=harness.stage('test-room');mod=engine/'vf_animation';(mod/'maps').mkdir(exist_ok=True)
 shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',mod/'maps/vf_range.bsp')
 source=(mod/'maps/vf_range.bsp').read_bytes();rows=entities(source)
 assert len([e for e in rows if e.get('classname')=='vf_range_target'])==4
 assert not any(e.get('classname')=='cycler'and 'vf_tfc/'in e.get('model','')for e in rows)
 assert patch(source)==source
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nvf_voice_subtitles 2\nfps_max 60\nweapon_9mmAR\nvf_reference 0\nwait 25\nvf_commit\nwait 25\nvf_ui_pointer 1220 40 1\nwait 3\nvf_ui_pointer 1220 40 0\nwait 15\n'
 s+='cmd vf_range_aim 0\nwait 15\ncmd vf_range_info\nvf_range_client\nscreenshot scrshots/range_start.png\nwait 4\n'
 for i,e in enumerate(ELEMENTS):
  slot=i%4;s+=f'cmd vf_range_reset {slot}\ncmd vf_fx_profile {e}\nwait 4\ncmd vf_range_fire {slot} 5\nwait 6\necho FIVE_{e}\ncmd vf_range_info\nwait 4\ncmd vf_range_fire {slot} 1\nwait 20\necho PROC_{e}\ncmd vf_range_info\nvf_range_client\ncmd vf_range_aim {slot}\nwait 8\nscreenshot scrshots/proc_{e}.png\nwait 5\n'
 s+='cmd vf_range_reset 0\ncmd vf_fx_profile thermal\ncmd vf_range_aim 0\nwait 25\n+attack\nwait 42\n-attack\nwait 15\necho REAL_TRIGGER\ncmd vf_range_info\nwait 10\ncmd vf_range_reset 0\ncmd vf_taunt\nwait 280\necho COUNTER_DONE\ncmd vf_range_info\n'
 # Genuine repeated hits kill a target and its scheduled respawn restores it.
 s+='cmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\ncmd vf_range_fire 0 6\nwait 160\necho RESPAWN_DONE\ncmd vf_range_info\nvf_engine_stats\nwait 12\nquit\n'
 (mod/'range_test.cfg').write_text(s,encoding='ascii');start=time.monotonic()
 child=subprocess.Popen([str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','range-test.log','+exec','lab_controls.cfg','+developer','1','+sv_cheats','1','+map','vf_range','+exec','range_test.cfg'],cwd=engine)
 try:child.wait(timeout=45);assert child.returncode==0,child.returncode
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 log=(engine/'range-test.log').read_text(encoding='utf-8',errors='replace');(OUT/'native.log').write_text(log,encoding='utf-8')
 assigned=re.findall(r'VFRange target=(\d) entity=(\d+) skin=(\d+) actor=(\S+) model=(\S+)',log);assert len(assigned)>=4,log[-4000:]
 assert len(set(a[2]for a in assigned[:4]))==4 and all('persona_rig' in a[4]for a in assigned[:4]),assigned
 def part(marker):
  start=re.search(r'^'+re.escape(marker)+r'\s*$',log,re.M);assert start,marker
  rest=log[start.end():];end=re.search(r'^(?:FIVE_\w+|PROC_\w+|REAL_TRIGGER|COUNTER_DONE|RESPAWN_DONE)\s*$',rest,re.M)
  return rest[:end.start()] if end else rest
 for i,e in enumerate(ELEMENTS):
  slot=i%4;five=part('FIVE_'+e);assert f'VFRange effect target={slot} id={e} hits=5 active=0'in five,(e,five[:3000])
  active=part('PROC_'+e);assert f'VFRange effect target={slot} id={e} hits=0 active=1'in active,(e,active[:3000])
  assert f'VFProc target={slot}'in log and f'effect={e} hits=6 window=3 duration=6'in log,e
  assert f'VFRange client effect target={slot} id={e} hits=0 active=1'in active,e
 assert re.search(r'VFRange effect target=0 id=thermal hits=\d+ active=1',part('REAL_TRIGGER')),part('REAL_TRIGGER')[:3000]
 assert 'event=counter_taunt' in log and 'VFRange heard target=0' in log,log[-6000:]
 assert 'VFRange death target=0 respawn=2'in log and re.search(r'VFRange info target=0[^\n]*health=300.0 alive=1',part('RESPAWN_DONE'))
 for i,e in enumerate(ELEMENTS):
  assert f'VFRange effect target={i%4} id={e} hits=0 active=0 remaining=0.00' in part('RESPAWN_DONE'),e
  assert re.search(r'VFRange voice entity=\d+ actor=\S+ event='+e+r' clip=',log),e
 assert 'VFState rejected'not in log and 'rejected=0'in log
 for e in ELEMENTS:assert (mod/'scrshots'/('proc_'+e+'.png')).stat().st_size>1000
 report=dict(elapsed_seconds=round(time.monotonic()-start,2),targets=assigned[:4],elements=ELEMENTS,server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),client_sha256=hashlib.sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),map_sha256=hashlib.sha256(source).hexdigest(),captures=[str(mod/'scrshots'/('proc_'+e+'.png'))for e in ELEMENTS],checks=['four distinct GIGN outfits; random existing operator voices','five actual engine hits do not proc; sixth hit procs for all eight elements','effect state and counts received by the client','normal attack input also triggers the six-hit rule','nearest target responds to a genuine player taunt','all status durations expire and the eight effect onset voices are emitted','target dies under genuine hits and respawns after two seconds','renderer accepts all GIGN target assemblies','map geometry and lighting preserved; patch is idempotent'])
 assert report['server_sha256']==hashlib.sha256((ROOT/'build/server/hl.dll').read_bytes()).hexdigest(),'Room test staged an obsolete server DLL'
 assert report['client_sha256']==hashlib.sha256((ROOT/'build/client/client.dll').read_bytes()).hexdigest(),'Room test staged an obsolete client DLL'
 (OUT/'native-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS native room',json.dumps(report))
if __name__=='__main__':run()

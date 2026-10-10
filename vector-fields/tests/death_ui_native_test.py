"""Real menu pointer path, corpse save/load and bounded repeated dismemberment."""
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
OUT=ROOT/'build/death-visual'
def run():
 e=harness.stage('death-ui');m=e/'vf_animation'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\nvf_death_lab\nwait 10\necho GUI_BEGIN\nvf_ui_pointer 1100 445 1\nwait 3\nvf_ui_pointer 1100 445 0\nwait 35\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/gui_head_electro.png\necho GUI_END\n'
 s+='save vf_death_visual_test\nwait 15\nload vf_death_visual_test\nwait 160\necho RESTORED_CORPSE\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/restored_corpse.png\ncmd vf_death_clear\nwait 5\n'
 s+='echo BUDGET_BEGIN\n'+('cmd vf_range_reset 0\ncmd vf_range_death 0 all standard legacy\nwait 1\n'*13)+'wait 8\necho BUDGET_STATE\nvf_death_client\nvf_engine_stats\ncmd vf_death_clear\nwait 8\necho CLEAN_STATE\nvf_death_client\necho CLEAN_END\n+duck\nwait 60\ncmd vf_body_info\nwait 3\necho CROUCH_DEATH\ncmd vf_death_test head electro\nwait 30\nvf_death_client\nquit\n'
 (m/'death_ui.cfg').write_text(s,encoding='ascii')
 p=subprocess.Popen([str(e/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','death-ui.log','+sv_cheats','1','+map','vf_range','+exec','death_ui.cfg'],cwd=e)
 try:p.wait(timeout=40);assert p.returncode==0
 finally:
  if p.poll() is None:p.terminate();p.wait(10)
 log=(e/'death-ui.log').read_text(errors='replace');(OUT/'menu.log').write_text(log)
 part=log.split('GUI_BEGIN')[1].split('GUI_END')[0];assert 'VFUI click: Tete explosee' in part and 'mask=1 effect=1 sequence=vf_electro' in part,part
 from PIL import Image
 assert sum(Image.open(m/'scrshots/gui_head_electro.png').getpixel((900,240))[:3])>200,'menu did not close to show death'
 restored=log.split('RESTORED_CORPSE')[1].split('BUDGET_BEGIN')[0];assert 'mask=1 effect=1' in restored and 'frame=255.0 model=models/vf_deaths/persona_death.mdl' in restored,restored
 budget=log.split('BUDGET_STATE')[1].split('CLEAN_STATE')[0];assert len(re.findall('VFCorpse client entity=',budget))==12,budget
 assert len(re.findall('VFFragment client entity=',budget))==72,budget
 assert all(int(n)<=384 for n in re.findall(r'pool active=(\d+)',log)),log
 clean=log.split('CLEAN_STATE')[1].split('CLEAN_END')[0];assert 'VFCorpse client entity=' not in clean and 'VFFragment client entity=' not in clean
 crouch=log.split('CROUCH_DEATH')[1];assert re.search(r'victim=1 mask=1 effect=1 .*origin_z=36.0 victim_mins_z=-18.0',crouch),crouch
 assert log.count('mask=31 effect=-1 sequence=headshot')==13
 assert 'rejected=0' in log and not any(x in log for x in ['Could not load','Host_Error','SV_Error','not precached'])
 report=dict(checks=['pointer click triggers actual head explosion/electrical death','corpse pose, missing head and cause survive save/load','thirteen simultaneous full dismemberments retain twelve corpses and 72 fragments','elemental particle pool stays within 384','clear removes all corpse states','native assemblies accepted','crouching player corpse preserves floor height'])
 (OUT/'menu-verification.json').write_text(json.dumps(report,indent=2));print('PASS native death menu/save/budget',json.dumps(report),flush=True)
if __name__=='__main__':run()

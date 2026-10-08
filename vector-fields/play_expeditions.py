"""Launch five matching GIGN and R-01 appearances from the Expeditions pack."""
import argparse,json,shutil,subprocess
from pathlib import Path
from build_personas import ROOT
from build_reference_weapon import ensure_current,main as build_weapon
from play_personas import deploy as deploy_personas,command,ENGINE,MOD
PACK=ROOT/'assets/expeditions-01.json'

def deploy(theme='ww1-trench'):
 if not ensure_current():build_weapon()
 target=ENGINE/'vf_visual/models/vf_r01';target.mkdir(parents=True,exist_ok=True)
 for path in (ROOT/'generated/r01').glob('*.mdl'):shutil.copy2(path,target/path.name)
 for name in ('equipment.txt','r01_styles.txt'):shutil.copy2(ROOT/'data'/name,ENGINE/'vf_visual/vf'/name)
 manifest=deploy_personas()
 themes=json.loads(PACK.read_text(encoding='utf-8-sig'))['themes'];entry=next(t for t in themes if t['id']==theme)
 persona=next(t for t in manifest['themes'] if t['key']=='persona_'+entry['key'])
 styles=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))['styles'];style=next(s['skin'] for s in styles if s['id']==theme)
 script=f'wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\nvf_reference 0\nwait 30\nvf_reference_style {style}\nvf_commit\nwait 30\nvf_skins\nwait 30\nvf_skin_tab 0\nvf_skin_filter 7\nvf_skin_all {persona["id"]}\nvf_skin_commit\nwait 30\nvf_animation_time 0\nvf_ui_pointer 1220 590 1\nwait 3\nvf_ui_pointer 1220 590 0\nwait 12\n'
 script+='vf_rotate\n'*6
 cfg=MOD/'vf_expeditions_start.cfg';cfg.write_text(script,encoding='ascii')
 return cfg

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--theme',default='ww1-trench',choices=[t['id']for t in json.loads(PACK.read_text(encoding='utf-8-sig'))['themes']]);p.add_argument('--deploy-only',action='store_true');a=p.parse_args();cfg=deploy(a.theme)
 if not a.deploy_only:subprocess.Popen(command(cfg.name,'vf-expeditions.log'),cwd=ENGINE)

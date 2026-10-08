"""Open the fitted GIGN character workshop using the existing game's resources."""
import argparse,json,shutil,subprocess
from pathlib import Path
from build_personas import build,ROOT
ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_personas'

def deploy():
 manifest=build(ensure=True)
 clients=[p for p in (ROOT/'build/client/client.dll',ROOT/'build/personas-client/client.dll')if p.exists()and b'persona_rig.mdl'in p.read_bytes()and b'vf_skin_filter'in p.read_bytes()]
 if not clients:raise RuntimeError('Rebuild the client with vector-fields/build.ps1 before opening the GIGN workshop.')
 client=max(clients,key=lambda p:p.stat().st_mtime)
 for folder in ('cl_dlls','dlls','vf','models/vf_skins','scrshots','save'):(MOD/folder).mkdir(parents=True,exist_ok=True)
 for source,target in [(ROOT/'generated/personas/persona_rig.mdl',MOD/'models/vf_skins/persona_rig.mdl'),(client,MOD/'cl_dlls/client.dll'),(ROOT/'build/server/hl.dll',MOD/'dlls/hl.dll'),(ROOT/'generated/personas/persona_scout.mdl',MOD/'models/vf_skins/persona_scout.mdl'),(ROOT/'generated/visual_skins/skins.txt',MOD/'vf/skins.txt')]:
  shutil.copy2(source,target)
 for name in ('equipment.txt','arsenal.txt','weapon_modules.txt','r01_styles.txt'):
  shutil.copy2(ENGINE/'vf_visual/vf'/name,MOD/'vf'/name)
 # Also register the family in the normal workshop; its next deployment uses
 # the updated source client and the same appearance catalog/model.
 for source,target in [(ROOT/'generated/personas/persona_rig.mdl',ENGINE/'vf_visual/models/vf_skins/persona_rig.mdl'),(ROOT/'generated/personas/persona_scout.mdl',ENGINE/'vf_visual/models/vf_skins/persona_scout.mdl'),(ROOT/'generated/visual_skins/skins.txt',ENGINE/'vf_visual/vf/skins.txt')]:shutil.copy2(source,target)
 (MOD/'gameinfo.txt').write_text('''title "Vector Fields - Personnages GIGN"
basedir "valve"
fallback_dir "vf_visual"
startmap "vf_range"
gamedll "dlls/hl.dll"
dllpath "cl_dlls"
gamemode "normal"
max_edicts "2048"
''',encoding='ascii')
 first=manifest['themes'][0]['id']
 script=f'wait 180\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 25\nvf_skins\nwait 35\nvf_skin_tab 0\nvf_skin_filter 7\nvf_skin_all {first}\nvf_skin_commit\nwait 25\n'
 (MOD/'vf_personas_start.cfg').write_text(script,encoding='ascii')
 return manifest

def command(cfg='vf_personas_start.cfg',log='vf-personas.log'):
 return [str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_personas','-borderless','-width','1920','-height','1080','-console','-nointro','-nowriteconfig','-log',log,'+exec','lab_controls.cfg','+map','vf_range','+exec',cfg]
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--deploy-only',action='store_true');args=parser.parse_args();deploy()
 if not args.deploy_only:subprocess.Popen(command(),cwd=ENGINE)

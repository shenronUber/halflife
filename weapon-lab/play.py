"""Select a local rifle and launch the isolated Half-Life SDK playtest."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
HALF_LIFE=Path('F:/SteamLibrary/steamapps/common/Half-Life')
XASH=PROJECT/'runtime'/'xash3d'
MODEL_NAMES={'v_9mmar.mdl','p_9mmar.mdl','w_9mmar.mdl','w_9mmarclip.mdl',
             'w_argrenade.mdl','w_chainammo.mdl','shell.mdl','grenade.mdl'}

def single(paths):
    paths=list(paths)
    if len(paths)!=1: raise ValueError(f'Expected exactly one input, found {paths}')
    return paths[0]

def variants():
    entries=[]
    for name in ['M4A1','M16A2','M16A3','M727']:
        base=single((ROOT/'extracted'/'636816').glob('*/Choose Your AR/'+name))
        entries.append((f'Colt {name}',636816,base/'Required',base/'Hand Options'/'HEV Hands'/'v_9mmar.mdl',None))
    for item,name in [(640445,'HK416'),(640447,'LR-300')]:
        base=single((ROOT/'extracted'/str(item)).iterdir())
        entries.append((name,item,base/'Required',base/'Hands Options'/'HEV Hands'/'v_9mmar.mdl',None))
    base=ROOT/'extracted'/'682919'
    entries.append(('Morita 9mm',682919,base,base/'v_choices'/'nochrome'/'v_9mmar.mdl','morita'))
    base=ROOT/'extracted'/'660140'
    entries.append(('AK-47',660140,base,base/'models'/'v_9mmar.mdl',None))
    base=ROOT/'extracted'/'641014'/'Aks74u'
    entries.append(('AKS-74U + Tishina',641014,base/'normal',base/'normal'/'models'/'v_9mmar.mdl',base/'sound'))
    for item,name in [(618001,'M4A1 chargeur tambour'),(615797,'M4 viseur + lance-grenades')]:
        base=ROOT/'extracted'/str(item)/'valve'
        view=single(p for p in (base/'models').iterdir() if p.name.lower()=='v_9mmar.mdl')
        entries.append((name,item,base,view,None))
    base=single((ROOT/'extracted'/'536775').iterdir())
    entries.append(("Tigg M4 (detail eleve)",536775,base,base/'models'/'models'/'v_9mmar.mdl','tigg'))
    base=single((ROOT/'extracted'/'706926').glob('*/valve'))
    view=single(p for p in (base/'models').iterdir() if p.name.lower()=='v_9mmar.mdl')
    entries.append(('Colt 727 basse definition',706926,base,view,None))
    base=single((ROOT/'extracted'/'640445').iterdir())
    entries.append(('Hybride HK416 + chargeurs LR-300',640445,base/'Required',ROOT/'generated'/'hybrid'/'v_9mmar.mdl','hybrid'))
    return entries

def copy_file(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)

def deploy(entry,engine,mod_name='vf_lab'):
    name,item,base,view,special=entry
    engine_root=XASH if engine=='xash' else HALF_LIFE
    if mod_name not in ('vf_lab','vf_character','vf_modular','vf_skins','vf_engine','vf_visual'):
        raise ValueError('Unknown local prototype directory')
    destination=engine_root/mod_name
    marker=destination/'vector-fields-lab.marker'
    if destination.exists() and not marker.exists():
        raise RuntimeError(f'Refusing to overwrite an existing unrecognized mod: {destination}')
    destination.mkdir(parents=True,exist_ok=True)
    marker.write_text('Owned by the local Vector Fields weapon-lab scripts.\n')
    # Restore stock defaults first, including for packs that lack a player/world model.
    for p in (HALF_LIFE/'valve'/'models').iterdir():
        if p.name.lower() in MODEL_NAMES: copy_file(p,destination/'models'/p.name.lower())
    for rel in ['hks1.wav','hks2.wav','hks3.wav','glauncher.wav','glauncher2.wav']:
        p=HALF_LIFE/'valve'/'sound'/'weapons'/rel
        if p.exists(): copy_file(p,destination/'sound'/'weapons'/rel)
    model_base=base/'models'/'models' if special=='tigg' else base/'models'
    if special=='morita': model_base=base/"p&w's"
    if model_base.exists():
        for p in model_base.iterdir():
            if p.name.lower() in MODEL_NAMES: copy_file(p,destination/'models'/p.name.lower())
    sound_dirs=[p for p in base.iterdir() if p.is_dir() and p.name.lower()=='sound']
    if special=='morita': sound_dirs=[base/'weaponsounds']
    if isinstance(special,Path) and special.exists(): sound_dirs.append(special)
    for folder in sound_dirs:
        for p in folder.rglob('*'):
            if p.suffix.lower()!='.wav': continue
            rel=p.relative_to(folder)
            if special=='morita' or len(rel.parts)==1: rel=Path('weapons')/rel
            copy_file(p,destination/'sound'/rel)
    copy_file(view,destination/'models'/'v_9mmar.mdl')
    copy_file(PROJECT/'technical-probe'/'server'/'hl.dll',destination/'dlls'/'hl.dll')
    copy_file(PROJECT/'technical-probe'/'client'/'client.dll',destination/'cl_dlls'/'client.dll')
    copy_file(ROOT/'generated'/'range'/'vf_range.bsp',destination/'maps'/'vf_range.bsp')
    (destination/'liblist.gam').write_text('''game "Vector Fields - Laboratoire"
startmap "vf_range"
trainmap "vf_range"
gamedll "dlls/hl.dll"
mpentity "info_player_deathmatch"
type "singleplayer_only"
fallback_dir "valve"
''',encoding='ascii')
    (destination/'autoexec.cfg').write_text('exec lab_controls.cfg\n',encoding='ascii')
    # A local config prevents the read-only Valve folder's personal bindings
    # from overriding the lab controls after autoexec has run.
    if not (destination/'config.cfg').exists():
        (destination/'config.cfg').write_text('exec lab_controls.cfg\n',encoding='ascii')
    if not (destination/'userconfig.cfg').exists():
        (destination/'userconfig.cfg').write_text('// Local lab settings.\n',encoding='ascii')
    (destination/'lab_controls.cfg').write_text('''// AZERTY ZQSD: Xash bindings use physical QWERTY key positions.
// Internal w/a are the physical Z/Q keys on a French keyboard.
unbind "z"
unbind "q"
bind "w" "+forward"
bind "s" "+back"
bind "a" "+moveleft"
bind "d" "+moveright"
bind "SPACE" "+jump"
bind "CTRL" "+duck"
bind "SHIFT" "+speed"
bind "MOUSE1" "+attack"
bind "MOUSE2" "+attack2"
bind "r" "+reload"
bind "e" "+use"
bind "1" "weapon_crowbar"
bind "3" "weapon_9mmAR"
bind "F4" "map vf_range"
bind "F6" "give ammo_9mmbox"
bind "F8" "screenshot"
bind "F10" "toggleconsole"
// Always look with the mouse; never move the player with mouse deltas.
unbind "ALT"
-strafe
lookspring "0"
lookstrafe "0"
m_forward "0"
m_side "0"
+mlook
sensitivity "2.5"
fps_max "100"
default_fov "90"
hud_fastswitch "1"
sv_cheats "1"
sv_lan "1"
volume "0.3"
''',encoding='ascii')
    selection={'name':name,'source':f'https://gamebanana.com/mods/{item}',
               'engine':engine,'local_only':True,'movement':'Unmodified Valve HLSDK DLLs'}
    (destination/'selected-rifle.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    print(f'Pret : {name} / {engine}\nDossier : {destination}',flush=True)
    return engine_root

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',choices=['xash','goldsrc'],default='xash')
    parser.add_argument('--weapon',type=int)
    parser.add_argument('--deploy-only',action='store_true')
    args=parser.parse_args()
    choices=variants()
    index=args.weapon
    if index is None:
        print('\nVECTOR FIELDS - LABORATOIRE DES ARMES\n')
        for i,entry in enumerate(choices,1): print(f'{i:2}. {entry[0]}')
        answer=input('\nNumero de l arme [14 = hybride] : ').strip()
        index=int(answer) if answer else 14
    if not 1<=index<=len(choices): raise ValueError('Numero invalide')
    engine_root=deploy(choices[index-1],args.engine)
    if args.deploy_only: return
    if args.engine=='xash':
        command=[str(XASH/'xash3d.exe'),'-rodir',str(HALF_LIFE),'-game','vf_lab',
                 '-windowed','-width','1280','-height','720','-console','-nointro','-log','weapon-lab.log',
                 '+exec','lab_controls.cfg','+map','vf_range']
    else:
        command=[str(HALF_LIFE/'hl.exe'),'-game','vf_lab','-windowed','-w','1280','-h','720','-console',
                 '+exec','lab_controls.cfg','+map','vf_range']
    process=subprocess.Popen(command,cwd=engine_root)
    print('Jeu lance, PID',process.pid,flush=True)

if __name__=='__main__': main()

"""Deploy and test the modular Vector Fields prototype in its own mod directory."""
import argparse
import json
import shutil
import subprocess
import sys
import time
from release import VERSION, startup as release_startup, check_native_interface, prepare_native_renderer_update, verify_deployment
from pathlib import Path
from import_tfc import install,entities,write_entities
from import_cs import install as install_cs
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'weapon-lab'))
import play as weapons
MOD='vf_skins'

def add_mannequins(destination,native=False):
    # The range and effect-guide previews share the installed GIGN assets.
    target=destination/'models/vf_skins';target.mkdir(parents=True,exist_ok=True)
    for name in ('persona_rig.mdl','persona_scout.mdl'):
        shutil.copy2(ROOT/'generated/personas'/name,target/name)
    bsp=destination/'maps/vf_range.bsp'
    if native:
        from build_test_room import build
        shutil.copy2(build(ensure=True),bsp)
        return
    # Keep the standalone legacy skin inspector usable without native assembly.
    data=bsp.read_bytes();items=entities(data)
    for item in items:
        if item.get('classname')=='game_player_equip':item['ammo_9mmbox']='1'
    for name,x in [('scout',-200),('soldier',0),('hvyweapon',200)]:
        source=weapons.HALF_LIFE/'tfc/models/player'/name/(name+'2.mdl')
        model=destination/'models/vf_tfc'/(name+'.mdl')
        model.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,model)
        items.append(dict(classname='cycler',model=f'models/vf_tfc/{name}.mdl',origin=f'{x} -220 36',angle='225'))
    for z in range(5):
        items.append(dict(classname='cycler',targetname=f'vf_skin_zone_{z}',model='models/vf_skins/skin_000.mdl',body=str(1<<z),origin='-280 -160 36',angle='225'))
    bsp.write_bytes(write_entities(data,items))


def fingerprint():
    value=2166136261
    for b in (ROOT/'data/equipment.txt').read_bytes():value=((value^b)*16777619)&0xffffffff
    return value

def main():
    global MOD
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy-only',action='store_true')
    parser.add_argument('--native-engine',action='store_true')
    parser.add_argument('--visual-lab',action='store_true')
    parser.add_argument('--reference-lab',action='store_true',help='Open the Relais R-01 reference weapon')
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--smoke-skins',action='store_true')
    parser.add_argument('--smoke-maps',action='store_true')
    parser.add_argument('--map',default='vf_range')
    args=parser.parse_args()
    if args.reference_lab:args.visual_lab=True
    if args.visual_lab:args.native_engine=True
    if args.native_engine:
        MOD='vf_engine';weapons.XASH=PROJECT/'runtime/vector-engine'
        if not (weapons.XASH/'xash3d.exe').exists():raise RuntimeError('Run build-engine.ps1 first')
        if args.visual_lab:MOD='vf_visual'
        if prepare_native_renderer_update(weapons.XASH,ROOT/'build/client/client.dll'):print('Verified native status renderer installed.',flush=True)
        check_native_interface(weapons.XASH,ROOT/'build/client/client.dll')
    if args.visual_lab:
        from build_reference_weapon import build as build_reference
        from build_personas import build as build_personas
        build_reference(ensure=True)
        build_personas(ensure=True)
        from build_lootpool import build as build_lootpool
        build_lootpool()
    for p in ['build/server/hl.dll','build/client/client.dll','generated/modular/vf_operator.mdl','generated/modular/v_9mmar.mdl']:
        if not (ROOT/p).exists():raise RuntimeError('Build missing: '+p)
    engine=weapons.deploy(weapons.variants()[4],'xash',mod_name=MOD);dst=engine/MOD
    for source,target in [('build/server/hl.dll','dlls/hl.dll'),('build/client/client.dll','cl_dlls/client.dll'),
        ('data/equipment.txt','vf/equipment.txt'),('data/r01_styles.txt','vf/r01_styles.txt'),('generated/modular/vf_operator.mdl','models/vf_operator.mdl'),
        ('generated/modular/v_9mmar.mdl','models/v_9mmar.mdl'),('generated/modular/operator.vfm','vf/operator.vfm'),('generated/modular/rifle.vfm','vf/rifle.vfm')]:
        out=dst/target;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,out)
    shutil.copytree(ROOT/'generated/modular/sprites',dst/'sprites/vf_preview',dirs_exist_ok=True)
    for source in (ROOT/'generated/skins').glob('*.mdl'):
        target=dst/'models/vf_skins'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for pattern in ['*.vfm','*.txt']:
        for source in (ROOT/'generated/skins').glob(pattern):shutil.copy2(source,dst/'vf'/source.name)
    shutil.copytree(ROOT/'generated/skins/sprites',dst/'sprites/vf_preview',dirs_exist_ok=True)
    if args.visual_lab:
        source=ROOT/'generated/visual_skins'
        for path in source.glob('*.mdl'):shutil.copy2(path,dst/'models/vf_skins'/path.name)
        for pattern in ['*.vfm','*.txt']:
            for path in source.glob(pattern):shutil.copy2(path,dst/'vf'/path.name)
        shutil.copytree(source/'sprites',dst/'sprites/vf_preview',dirs_exist_ok=True)
        shutil.copytree(ROOT/'generated/equipment_visuals',dst/'models/vf_equipment',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.smd','*.qc','*.log','*.bmp'))
        modules=ROOT/'generated/weapon_visuals';target=dst/'models/vf_modules';target.mkdir(parents=True,exist_ok=True)
        for path in modules.glob('*.mdl'):shutil.copy2(path,target/path.name)
        shutil.copy2(modules/'weapon_modules.txt',dst/'vf/weapon_modules.txt')
        sounds=next((PROJECT/'weapon-lab/extracted/179714').glob('*/sound/weapons'))
        shutil.copytree(sounds,dst/'sound/weapons',dirs_exist_ok=True)
    (dst/'selected-rifle.json').write_text(json.dumps({'name':'HK416 modular: standard/drum magazine, optional muzzle attachment',
        'source':'https://gamebanana.com/mods/640445','generated_by':'vector-fields/build_modular.py','engine':'xash',
        'local_only':True,'movement':'Valve HLSDK movement unchanged; equipment DLLs modified'},indent=2))
    manifest=install(weapons.HALF_LIFE/'tfc',engine,dst)
    print(f'TFC: {manifest["count"]} files, {len(manifest["maps"])} exploration maps',flush=True)
    cs_manifest=install_cs(weapons.HALF_LIFE/'cstrike',engine,dst) if args.visual_lab else {'maps':[]}
    if args.visual_lab:
        library=ROOT/'generated/library'
        if not (library/'manifest.json').exists():raise RuntimeError('Build the expanded library first')
        for folder in ['models','sound']:
            if (library/folder).exists():shutil.copytree(library/folder,dst/folder,dirs_exist_ok=True)
        shutil.copy2(library/'manifest.json',dst/'vf/library-provenance.json')
        from build_first_person import build as build_first_person
        build_first_person(ensure=True)
        from third_person import build as build_third_person
        build_third_person(ensure=True)
        target=dst/'models/vf_r01';target.mkdir(parents=True,exist_ok=True)
        for path in (ROOT/'generated/r01').glob('*.mdl'):shutil.copy2(path,target/path.name)
        for path in (ROOT/'generated/third-person').glob('*.mdl'):shutil.copy2(path,target/path.name)
        print(f'CS: {cs_manifest["count"]} resources, {len(cs_manifest["maps"])} exploration maps',flush=True)
    valid_maps=['vf_range']+[i['name'] for i in manifest['maps']]+[i['name'] for i in cs_manifest['maps']]
    if args.map not in valid_maps:raise ValueError('Choose one of: '+', '.join(valid_maps))
    from build_deaths import build as build_deaths
    build_deaths(ensure=True)
    shutil.copytree(ROOT/'generated/deaths',dst/'models/vf_deaths',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.smd','*.qc','*.bmp','*.log','manifest.json'))
    add_mannequins(dst,args.native_engine)
    (dst/'gameinfo.txt').write_text('''title "Vector Fields - Atelier de skins"
basedir "valve"
fallback_dir "tfc_assets"
startmap "vf_range"
gamedll "dlls/hl.dll"
dllpath "cl_dlls"
gamemode "singleplayer_only"
max_edicts "2048"
''',encoding='ascii')
    if args.native_engine:
        info=dst/'gameinfo.txt';info.write_text(info.read_text().replace('Atelier de skins','Moteur modulaire').replace('gamemode "singleplayer_only"','gamemode "normal"'))
        if args.visual_lab:info.write_text(info.read_text().replace('Vector Fields - Moteur modulaire','Vector Fields / '+VERSION['version']).replace('fallback_dir "tfc_assets"','fallback_dir "cs_assets"'))
        (dst/'vf/native_engine.txt').write_text('Vector Fields renderer extension v2 required.\n')
        target=dst/'models/vf_modules';target.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'generated/sockets/suppressor.mdl',target/'suppressor.mdl')
        target=dst/'models/vf_tfc_arsenal';target.mkdir(parents=True,exist_ok=True)
        for row in (ROOT/'generated/skins/arsenal.txt').read_text().splitlines():
            name=row.split('|')[2]
            source=weapons.HALF_LIFE/'tfc/models'/(name+'.mdl');shutil.copy2(source,target/source.name)
            companion=source.with_name(name+'t.mdl')
            if companion.exists():shutil.copy2(companion,target/companion.name)
    shutil.copytree(ROOT/'generated/ui',dst/'sprites/vf_ui',dirs_exist_ok=True)
    shutil.copytree(ROOT/'generated/effects',dst/'sprites/vf_effects',dirs_exist_ok=True)
    from build_status_decals import build as build_status_decals
    build_status_decals(ensure=True)
    shutil.copytree(ROOT/'generated/status-decals',dst/'sprites/vf_status',dirs_exist_ok=True,ignore=shutil.ignore_patterns('manifest.json','*-mask.spr'))
    shutil.copy2(ROOT/'data/status_decals.json',dst/'vf/status_decals.json')
    shutil.copy2(ROOT/'data/effects.json',dst/'vf/effects.json')
    # Six original bilingual operators; no ElevenLabs dependency at runtime.
    from death_voice_workshop import deploy as deploy_death_voices
    deploy_death_voices(dst)
    from build_death_sounds import deploy as deploy_death_sounds
    deploy_death_sounds(dst)
    voice_assets=ROOT/'assets/audio/operators'
    if (voice_assets/'manifest.json').exists():
        for actor in json.loads((voice_assets/'manifest.json').read_text())['actors']:
            target=dst/'sound/vf_voices'/actor['id'];target.mkdir(parents=True,exist_ok=True)
            for wav in (voice_assets/actor['id']).glob('*.wav'):
                if not wav.stem.endswith('_master') and not wav.stem.startswith('death'):shutil.copy2(wav,target/wav.name)
        shutil.copy2(voice_assets/'manifest.json',dst/'vf/voice-manifest.json')
        (dst/'vf_voices.cfg').write_text('bind "j" "cmd vf_taunt"\nvf_voice_subtitles 1\n',encoding='ascii')

    from build_weapon_fx_range import build as build_fx_range
    build_fx_range()
    from build_weapon_fx import build as build_weapon_fx
    build_weapon_fx()
    shutil.copytree(ROOT/'generated/weapon-fx/sprites',dst/'sprites/vf_weaponfx',dirs_exist_ok=True)
    shutil.copytree(ROOT/'generated/weapon-fx/sound',dst/'sound/vf_weaponfx',dirs_exist_ok=True)
    shutil.copy2(ROOT/'generated/weapon-fx/decals.wad',dst/'decals.wad')
    shutil.copy2(ROOT/'data/weapon_fx.json',dst/'vf/weapon_fx.json')
    shutil.copy2(ROOT/'generated/weapon-fx/range/vf_fx_range.bsp',dst/'maps/vf_fx_range.bsp')
    with (dst/'lab_controls.cfg').open('a') as f:
        f.write('\nbind "F1" "vf_character"\nbind "F2" "vf_operator"\nbind "F5" "vf_dev; exec vf_visit_2fort.cfg"\nhud_scale 1\nr_studio_drawelements 1\nr_studio_builtin_renderer 0\ndeveloper 0\ncon_notifytime 3\n')
        f.write('\nbind F11 \"vf_reference\"\nbind F7 "vf_dev"\nscr_drawversion 0\nbind F6 vf_dev\nbind F4 "map vf_range; exec vf_start.cfg"\nbind F3 vf_effects\nbind F9 vf_effect_clear\nbind PGUP vf_effect_prev\nbind PGDN vf_effect_next\n')
        f.write('\nbind F8 vf_death_lab\n')
        f.write('\nbind j "cmd vf_taunt"\n')
        f.write('\nvf_native_models '+('1' if args.native_engine else '0')+'\n')
    wait='wait 180\n' # Xash3D supports a frame count; keep the command buffer small.
    equip='give item_suit\ngive weapon_9mmAR\ngive ammo_9mmbox\nweapon_9mmAR\n'
    # The range already equips the player with a suit and rifle. Giving a
    # second suit leaves its world model at the camera, obscuring the weapon.
    start=wait+('weapon_9mmAR\n' if args.map=='vf_range' else equip)+wait+('vf_character\n' if args.smoke or not args.smoke_skins else 'vf_skins\n')
    if args.reference_lab:start=wait+('weapon_9mmAR\n' if args.map=='vf_range' else equip)+wait+'vf_reference 0\nwait 30\nvf_commit\n'
    if args.visual_lab and args.map=='vf_range' and not(args.reference_lab or args.smoke or args.smoke_skins or args.smoke_maps):
        start=release_startup()
    shutil.copy2(ROOT/'version.json',dst/'vf/version.json')
    if args.visual_lab:shutil.copy2(ROOT/'data/lootpool.json',dst/'vf/lootpool.json')
    (dst/'vf_visit_2fort.cfg').write_text('map vf_tfc_2fort\n'+wait+equip,encoding='ascii')
    screenshots=[]
    def capture(name):
        screenshots.append(name)
        return wait+f'screenshot scrshots/{name}.png\n'+wait
    hash_value=fingerprint()
    if args.smoke_skins:
        start='developer 1\ncon_notifytime 0\n'+start+wait+'vf_skin_audit\n'+capture('skins_soldier')
        for name,ids in [('mixed_human',[44,0,69,138,9]),('mixed_alien',[27,63,2,115,17])]:
            start+=''.join(f'vf_skin_set {z} {id}\n' for z,id in enumerate(ids))+'vf_skin_commit\n'+capture(name)
            start+='vf_rotate\n'*3+capture(name+'_side')+'vf_rotate\n'*9
        start+='vf_skin_set 2 69\nvf_skin_isolate\n'+capture('isolated_gloves')+'vf_skin_isolate\n'
        start+='vf_skin_set 4 17\nvf_skin_isolate\n'+capture('isolated_shoes')+'vf_skin_isolate\n'
        for id in [119,127,86,54,144]:start+=f'vf_skin_all {id}\n'+capture(f'source_{id}')
        start+='vf_skin_all 127\nvf_skin_set 2 9\nvf_skin_set 4 0\nvf_skin_commit\n'+capture('skins_final')
        skin_hash=2166136261
        for b in (ROOT/'generated/skins/skins.txt').read_bytes():skin_hash=((skin_hash^b)*16777619)&0xffffffff
        start+=f'cmd vf_skin_apply {skin_hash} 999 0 0 0 0\n'+wait+'cmd vf_skin_apply 0 0 0 0 0 0\n'+wait
        start+='vf_skins\n'+wait+'save vf_skins_smoke\n'+wait+'load vf_skins_smoke\n'+wait+'vf_skins\n'+capture('skins_restored')
        for id in [0,15,30,50,64]:start+=f'vf_arsenal_select {id}\n'+capture(f'arsenal_{id}')
        start+='vf_skins\n'+wait+'cmd vf_skin_inspect\ncmd vf_skin_camera\n'+capture('skins_mannequin')+'quit\n'
    if args.smoke:
        start=start.replace('vf_character\n',capture('standard_in_hand')+'vf_character\n',1)
        start='developer 1\ncon_notifytime 0\n'+start
        start+=capture('operator_soldier')
        start+='vf_select_slot 0\nvf_next_item\nvf_select_slot 3\nvf_next_item\nvf_select_slot 5\nvf_next_item\nvf_next_item\nvf_commit\n'
        start+=capture('operator_mixed')
        start+='vf_rotate\nvf_rotate\nvf_rotate\n'+capture('operator_rotated')+'vf_rotate\n'*9
        start+='vf_select_slot 12\n'+capture('rifle_standard')
        start+='vf_next_item\nvf_select_slot 11\nvf_next_item\nvf_commit\n'+capture('rifle_drum')
        start+='vf_character\n'+capture('drum_in_hand')+'vf_model_info\n'
        start+='+attack\nwait 50\n-attack\n'+wait+'+reload\nwait 35\n'
        start+='screenshot scrshots/drum_reload.png\nvf_model_info\nwait 35\nscreenshot scrshots/drum_reload_insert.png\n-reload\n'+wait+'vf_model_info\n'
        screenshots.extend(['drum_reload','drum_reload_insert'])
        start+='vf_character\n'+wait
        overload=' '.join(str(n) for n in range(2,43,2))
        wrong='7 '+' '.join(str(n) for n in range(3,43,2))
        for invalid in [overload,wrong,'999 '+' '.join(str(n) for n in range(3,43,2))]:start+=f'cmd vf_apply {hash_value} {invalid}\n'+wait
        start+=capture('modular_rejected')
        start+='vf_character\n'+wait+'save vf_modular_smoke\n'+wait+'load vf_modular_smoke\n'+wait+'vf_character\n'+capture('modular_restored')+'vf_character\n'+wait+'quit\n'
    if args.smoke_maps:
        screenshots=[m['name'] for m in manifest['maps']]
        # One bounded process per map avoids overflowing GoldSrc's command
        # buffer and gives each map an independent, reproducible spawn.
        started=time.time()
        for name in screenshots:
            script='developer 1\ncon_notifytime 0\n'+wait+equip+wait+f'screenshot scrshots/{name}.png\n'+wait+'quit\n'
            (dst/'vf_map_test.cfg').write_text(script,encoding='ascii')
            command=[str(engine/'xash3d.exe'),'-rodir',str(weapons.HALF_LIFE),'-game',MOD,'-borderless','-width','1920','-height','1080','-nointro','-log',name+'.log',
                     '+exec','lab_controls.cfg','+developer','1','+map',name,'+exec','vf_map_test.cfg']
            process=subprocess.Popen(command,cwd=engine)
            try:process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                process.terminate();process.wait(timeout=10);raise RuntimeError('Map test timed out: '+name)
            assert process.returncode==0,(name,process.returncode)
            log=(engine/(name+'.log')).read_text(errors='replace')
            assert 'Spawn Server: '+name in log,name
            p=dst/'scrshots'/(name+'.png');assert p.stat().st_mtime>=started and p.stat().st_size>1000,name
            print('PASS map:',name,flush=True)
        (ROOT/'build/maps-verification.json').write_text(json.dumps({'maps':screenshots,'count':len(screenshots),'tfc_files':manifest['count'],'checks':['each map spawned in a fresh process and produced a screenshot'],'limits':['exploration only; TFC classes and objectives not implemented']},indent=2))
        return
    assert len(start.encode('ascii'))<24000,'Leave room in the engine command buffer'
    if not (dst/'vf_voice_behavior.cfg').exists():shutil.copy2(ROOT/'data/voice_behavior.cfg',dst/'vf_voice_behavior.cfg')
    if not start.startswith('exec vf_voice_behavior.cfg\n'):start='exec vf_voice_behavior.cfg\n'+start
    (dst/'vf_start.cfg').write_text(start,encoding='ascii')
    if args.visual_lab:verify_deployment(dst)
    if args.deploy_only:return
    smoke=args.smoke or args.smoke_maps or args.smoke_skins
    log_name='vf-skins-test.log' if args.smoke_skins else 'vf-modular-test.log' if args.smoke else 'vf-skins.log'
    command=[str(engine/'xash3d.exe'),'-rodir',str(weapons.HALF_LIFE),'-game',MOD,
             '-borderless','-width','1920','-height','1080','-console','-nointro','-log',log_name,
             '+exec','lab_controls.cfg','+map',args.map,'+exec','vf_start.cfg']
    started=time.time();process=subprocess.Popen(command,cwd=engine)
    print('Prototype PID:',process.pid,flush=True)
    if smoke:
        try:process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=10);raise RuntimeError('Isolated smoke child timed out')
        if process.returncode:raise RuntimeError(f'Game exited with {process.returncode}')
        log=(engine/log_name).read_text(errors='replace');checks=[]
        if args.smoke_skins:
            for expected in ['VFSkin: result=0 ids=44,0,69,138,9','VFSkin: result=3 ids=127,127,9,127,0','VFSkin: result=2 ids=127,127,9,127,0','Loading game from save/vf_skins_smoke.sav']:
                assert expected in log,expected
            restored=log.split('Loading game from save/vf_skins_smoke.sav')[-1]
            assert 'VFSkin preview audit: loaded=210 failed=0' in log
            assert 'MAX_CLIENT_SPRITES limit exceeded' not in log
            assert 'VFSkin client: result=0 ids=127,127,9,127,0' in restored
            for z,id in enumerate([127,127,9,127,0]):assert f'VFSkin entity: zone={z} body={1<<z} model=models/vf_skins/skin_{id:03}.mdl' in log
            checks=['all 210 previews loaded in one engine session without sprite exhaustion','five independent skin zones committed','invalid source and stale catalog rejected atomically','selection restored after save/load','all five mannequin entities use the committed MDL and zone bodygroup','native model previews captured for all four games','gloves and shoes isolated in 3D']
        if args.smoke:
            for expected in ['VF equipment: result=0','VF equipment: result=4','VF equipment: result=3','VFBuild received: result=2','VF visuals: operator=22 weapon=3','Loading game from save/vf_modular_smoke.sav']:
                assert expected in log,expected
            restored=log.split('Loading game from save/vf_modular_smoke.sav')[-1]
            assert 'VF visuals: operator=22 weapon=3' in restored
            assert log.count('VF viewmodel: body=3 model=models/v_9mmAR.mdl')==3,'Actual viewmodel body must remain modular during reload'
            checks=['server commits modular selection','over-budget/wrong-slot/unknown-item rejected','bodygroup selection retained after save/load','shoot/reload commands exercised','actual viewmodel body checked before, during and after reload']
        for name in screenshots:
            p=dst/'scrshots'/(name+'.png')
            assert p.stat().st_mtime>=started and p.stat().st_size>1000,name
        report={'engine':'Xash3D FWGS 9137964 i386','catalog_fingerprint':hash_value,'checks':checks,'screenshots':screenshots,
            'tfc_files':manifest['count'],'limits':['single-player only','combat effects not implemented','TFC objectives not ported','skin assembly currently applied to the test mannequin','world and third-person rifle models remain stock']}
        (ROOT/'build'/('skins-verification.json' if args.smoke_skins else 'verification.json')).write_text(json.dumps(report,indent=2))
        print('PASS: in-engine modular smoke test',flush=True)

if __name__=='__main__':main()

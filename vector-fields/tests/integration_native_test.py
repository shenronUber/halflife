"""Run focused integrations against a frozen copy of the installed bundle."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import engine_path,private_copy,shared_copy
import slide_feet_bundle as bundle
SNAP=ROOT/'build/integration-audit/installed'
OUT=ROOT/'build/integration-audit/native'
ONLY=None

def fixture_at(engine,mod_name='vf_animation'):
    from release import check_native_interface
    check_native_interface(SNAP/'engine',SNAP/'client/client.dll')
    engine.mkdir(parents=True,exist_ok=True)
    for source in (SNAP/'engine').iterdir():
        if source.is_file():private_copy(source,engine/source.name)
    for target,source in [('valve','valve'),('tfc_assets','tfc_assets'),('cs_assets','cs_assets'),('vf_installed','vf_visual')]:
        link=engine/target
        if not link.exists():
            bundle._winapi.CreateJunction(str(bundle.INSTALLED/source),str(link));bundle._fallbacks.append(link)
    mod=engine/mod_name
    for name in ['dlls','cl_dlls','scrshots','save']:(mod/name).mkdir(parents=True,exist_ok=True)
    for source,target in [('server/hl.dll','dlls/hl.dll'),('client/client.dll','cl_dlls/client.dll'),('delta.lst','delta.lst')]:private_copy(SNAP/source,mod/target)
    for name in ['models','maps','vf']:shutil.copytree(SNAP/name,mod/name,dirs_exist_ok=True,copy_function=shared_copy)
    (mod/'gameinfo.txt').write_text('title "Vector Fields - Installed integration audit"\nbasedir "valve"\nfallback_dir "vf_installed"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    return engine,mod

def fixture(name,**kwargs):return fixture_at(engine_path(OUT/name))

def run(case):
    OUT.mkdir(parents=True,exist_ok=True)
    if case in ['wallrun','wallrun_network']:
        import wallrun_native_test as native
        import wallrun_multiplayer_test as network
        module=native if case=='wallrun' else network
        module.BUILD=SNAP;module.OUT=OUT/case;module.prepare_slide_feet=fixture
        module.run()
    elif case=='walljump':
        import traversal_wall_jump_native_test as module
        module.CANDIDATE=SNAP;module.OUT=OUT/case
        module.stage_installed=lambda engine:fixture_at(engine,'vf_visual')[1]
        module.build_traversal_range.build=lambda ensure=True:SNAP/'maps/vf_traversal.bsp'
        module.run()
    elif case=='walk':
        import traversal_wall_jump_walk_test as module
        module.CANDIDATE=SNAP;module.OUT=OUT/case;module.stage=lambda name,candidate:fixture(name)
        module.run()
    elif case in ['pose','pose_extended','pose_strike','combat']:
        import player_pose_native_test as pose
        import combat_regression_native_test as combat
        module=pose if case.startswith('pose') else combat
        module.OUT=OUT/case;module.harness.stage=lambda name,**kwargs:fixture(name,**kwargs)[0]
        if case.startswith('pose'):
            module.build=lambda ensure=True:SNAP/'maps/vf_traversal.bsp'
            module.run(SNAP,only=ONLY,extended=case in ['pose_extended','pose_strike'],melee_phases=case=='pose_strike')
        else:module.run(SNAP)
    elif case in ['melee','melee_network']:
        import weapon_melee_native_test as native
        import weapon_melee_network_test as network
        from build_weapon_melee import sources,digest
        inputs=sources()
        for relative,expected in inputs.items():
            assert digest(SNAP/'source'/relative)==expected,('Compiled input changed',relative)
        target=OUT/case;target.mkdir(parents=True,exist_ok=True)
        for part,name in [('client','client.dll'),('server','hl.dll')]:
            (target/part).mkdir(exist_ok=True);shutil.copy2(SNAP/part/name,target/part/name)
        build=dict(sources=inputs,client_sha256=digest(SNAP/'client/client.dll'),server_sha256=digest(SNAP/'server/hl.dll'),assets={p.name:digest(p)for p in(SNAP/'models/vf_melee').glob('*.mdl')})
        (target/'build.json').write_text(json.dumps(build,indent=2)+'\n')
        module=native if case=='melee' else network
        module.OUT=target;module.stage=lambda:fixture(case)
        if case=='melee':module.ASSET_MODELS=SNAP/'models/vf_melee'
        if case=='melee_network':module.copy_resources=lambda engine,peer,**kwargs:fixture_at(peer)
        module.run()
    elif case in ['melee_integration','gesture_status']:
        if case=='melee_integration':import melee_integration_native_test as module
        else:import gesture_status_native_test as module
        module.audit.SNAP=SNAP;module.audit.OUT=OUT
        module.run()
    elif case=='headgear':
        import headgear_action_native_test as module
        module.stage=lambda name,candidate:fixture(name)
        report=module.run(True,False,SNAP)
        (OUT/'headgear.json').write_text(json.dumps(report,indent=2)+'\n')
    else:raise ValueError(case)
    print('PASS installed integration:',case,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=['wallrun','wallrun_network','walljump','walk','pose','pose_extended','pose_strike','combat','melee','melee_network','melee_integration','gesture_status','headgear'])
    parser.add_argument('--bundle',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--only');args=parser.parse_args()
    ONLY=args.only
    if args.bundle:SNAP=args.bundle.resolve()
    if args.output:OUT=args.output.resolve()
    run(args.case)

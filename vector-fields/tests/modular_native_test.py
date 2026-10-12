"""Actual BSP collision, seeded reloads and movement over every active junction."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import private_copy,port
from build_modular_range import build,geometry
from play_modular import SERVER,CLIENT,prepare
from slide_feet_bundle import prepare_slide_feet

OUT=ROOT/'docs/validation/modular'


def expected(seed):
    exe=ROOT/'build/policy-tests/modular/modular.exe'
    sources=[ROOT/'tests/modular_layout_test.cpp',ROOT.parent/'game_shared/vf_modular_layout.h']
    if not exe.exists() or any(source.stat().st_mtime>exe.stat().st_mtime for source in sources):
        import cpp_tests
        suites=cpp_tests.TESTS
        try:
            cpp_tests.TESTS={'modular':suites['modular']}
            if cpp_tests.run():raise RuntimeError('Modular layout fixture failed')
        finally:cpp_tests.TESTS=suites
    return json.loads(subprocess.check_output([str(exe),'--dump',str(seed)],text=True))


def run(seed=42):
    prepare()
    engine,mod=prepare_slide_feet('modular',build=ROOT/'build/modular',server=SERVER,
                                  engine_binaries=ROOT.parent/'runtime/vector-engine',client=CLIENT)
    private_copy(build(ensure=True),mod/'maps/vf_modular.bsp')
    layout=expected(seed);g=geometry()
    lines=['wait 120','gl_vsync 0','host_framerate 0.0166667','fps_max 60','developer 1','con_notifytime 0',
           'sv_cheats 1','cmd give item_suit','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR',
           'wait 40','vf_reference 0','wait 25','vf_commit','wait 30','vf_character','vf_character',
           'wait 10','echo MOD_BEGIN','cmd vf_modular_info','cmd vf_modular_check','wait 10']

    def add(*commands):lines.extend(commands)
    def probe(name):add('echo MOD_'+name,'cmd vf_traversal_info','wait 2')
    for edge in g['edges']:
        e=edge['edge'];start=edge['start'];center=edge['center'];axis=edge['axis']
        kind=layout['links'][e]
        add('-forward','-jump','-duck','wait 12')
        if kind in (0,1):
            x,y=(start-96,center) if axis=='x' else (center,start-96)
            vx,vy=(320,0) if axis=='x' else (0,320)
            yaw=0 if axis=='x' else 90
            add(f'cmd vf_traversal_place {x} {y} 36.1 {yaw} {vx} {vy} 0',f'vf_traversal_look {yaw} 0','+forward','wait 90')
            probe(f'EDGE_{e}_CROSS');add('-forward','wait 15')
        else:
            for direction in (1,-1):
                u=start-96 if direction==1 else start+g['gap']+96
                face=edge['wall_face']+18
                x,y=(u,face) if axis=='x' else (face,u)
                vx,vy=(320*direction,0) if axis=='x' else (0,320*direction)
                yaw=(0 if direction==1 else 180) if axis=='x' else (90 if direction==1 else 270)
                entry=(300 if direction==1 else 240) if axis=='x' else (150 if direction==1 else 210)
                name=f'EDGE_{e}_'+('FORWARD' if direction==1 else 'REVERSE')
                add('-forward','-jump','wait 15',f'cmd vf_traversal_place {x} {y} 128 {entry} {vx} {vy} 0',
                    f'vf_traversal_look {entry} 0','+forward','+jump','wait 2','-jump',f'vf_traversal_look {yaw} 0','wait 32')
                probe(name+'_RUN')
                if direction==1:add('screenshot scrshots/modular_wallrun_'+str(e)+'.png','wait 2')
                add('wait 62','-forward','wait 45');probe(name+'_LANDED')
    add('-forward','-jump','wait 12',f"cmd vf_traversal_place {g['extent']//2+128} 0 128 0",'wait 130');probe('RECOVERY')
    add('cmd vf_modular_info','wait 10','save vf_modular','wait 4','load vf_modular','wait 120',
        'echo MOD_RESTORED','cmd vf_modular_info','cmd vf_modular_check','wait 10')
    # Capture a readable complete grid as evidence, plus a normal ground view.
    x,y,z=g['spawn'];add(f'cmd vf_traversal_place {x} {y} 36.1 0','wait 4','vf_traversal_look 0 -10','wait 10','screenshot scrshots/modular_ground.png','wait 2')
    add('noclip','cmd vf_traversal_place 0 0 2800 90','wait 4','vf_traversal_look 90 89','default_fov 110','r_drawviewmodel 0','vf_first_person_body 0','wait 12',
        'screenshot scrshots/modular_overview.png','wait 2','noclip','default_fov 90','r_drawviewmodel 1','vf_first_person_body 1')
    # Same seed on restart, different fixed seed, then two automatic draws.
    add('map vf_modular','wait 120','echo MOD_REPEAT','cmd vf_modular_info','cmd vf_modular_check','wait 10',
        'vf_modular_seed 12345','map vf_modular','wait 120','echo MOD_OTHER','cmd vf_modular_info','cmd vf_modular_check','wait 10',
        'vf_modular_seed 0','map vf_modular','wait 120','echo MOD_RANDOM_A','cmd vf_modular_info','cmd vf_modular_check','wait 10',
        'map vf_modular','wait 120','echo MOD_RANDOM_B','cmd vf_modular_info','cmd vf_modular_check','wait 20','quit')
    for part,start in enumerate(range(0,len(lines),85)):
        chunk=lines[start:start+85]
        if start+85<len(lines):chunk.append(f'exec modular_test_{part+1:03}.cfg')
        (mod/f'modular_test_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
         '-game',mod.name,'-windowed','-width','1280','-height','720','-nointro','-nowriteconfig','-dev','1',
         '-log','modular-native.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1',
         '+maxplayers','1','+map','vf_modular','+vf_modular_seed',str(seed),'+map','vf_modular','+exec','modular_test_000.cfg'],
         cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:process.wait(timeout=150)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    OUT.mkdir(parents=True,exist_ok=True)
    text=(engine/'modular-native.log').read_text(errors='replace')
    shutil.copy2(engine/'modular-native.log',OUT/'native.log')
    for image in (mod/'scrshots').glob('modular_*.png'):shutil.copy2(image,OUT/image.name)
    cases={}
    for name,block in re.findall(r'MOD_([A-Z_0-9]+)\s+(.*?)(?=MOD_|\Z)',text,re.S):
        move=re.search(r'VFTraversal phase=(\d+) state=(\d+) origin=([\d.,-]+) velocity=([\d.,-]+)',block)
        if move:
            phase,state,origin,velocity=move.groups()
            cases[name]=dict(phase=int(phase),origin=list(map(float,origin.split(','))),velocity=list(map(float,velocity.split(','))))
        state=re.search(r'VFModular seed=(\d+) cells=([\d,]+) modules=(\d+)',block)
        if state:
            value,cells,modules=state.groups()
            cases.setdefault(name,{}).update(seed=int(value),cells=list(map(int,cells.split(','))),modules=int(modules))
    checks=re.findall(r'VFModular check seed=(\d+) candidates=(\d+) mismatches=(\d+)',text)
    report=dict(passed=False,expected=layout,cases=cases,collision_checks=checks,exit_code=process.returncode)
    (OUT/'native.json').write_text(json.dumps(report,indent=2))
    assert process.returncode==0
    assert len(checks)==6 and all(int(n)==102 and int(errors)==0 for _,n,errors in checks),checks
    for name in ('BEGIN','RESTORED','REPEAT'):
        assert cases[name]['seed']==seed and cases[name]['cells']==layout['cells'],(name,cases)
    assert cases['OTHER']['cells']==expected(12345)['cells']
    assert cases['RANDOM_A']['seed']!=cases['RANDOM_B']['seed']
    for edge in g['edges']:
        e=edge['edge'];axis=0 if edge['axis']=='x' else 1;start=edge['start'];kind=layout['links'][e]
        if kind in (0,1):
            row=cases[f'EDGE_{e}_CROSS'];assert row['origin'][axis]>start+g['gap']+30 and row['origin'][2]>30,(e,row)
        else:
            for direction,word in ((1,'FORWARD'),(-1,'REVERSE')):
                running=cases[f'EDGE_{e}_{word}_RUN'];landing=cases[f'EDGE_{e}_{word}_LANDED']
                assert running['phase']==8 and start<running['origin'][axis]<start+g['gap'],(e,word,running)
                assert landing['phase']==0 and 35<landing['origin'][2]<38,(e,word,landing)
                assert (landing['origin'][axis]>start+g['gap']) if direction==1 else (landing['origin'][axis]<start),(e,word,landing)
    assert abs(cases['RECOVERY']['origin'][0]-g['spawn'][0])<2 and abs(cases['RECOVERY']['origin'][1]-g['spawn'][1])<2 and cases['RECOVERY']['origin'][2]>30,cases['RECOVERY']
    report.update(passed=True,checks=['all candidate visibility/solidity states','real floor/wall traces for all 12 edges',
                  'every join and bridge crossed','every wall run crossed in both directions','automatic fall recovery',
                  'save/load keeps seed and geometry','same seed replays','different seed regenerates','random draws on map restart'])
    (OUT/'native.json').write_text(json.dumps(report,indent=2))
    print('PASS native modular collisions, traversal and map-load regeneration',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,default=42)
    run(parser.parse_args().seed)

"""Actual engine: both push-offs, higher recatch, weapon lock and two views.

Stages the installed game and overlays only the private wall-jump candidates.
"""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_workspace import engine_path,stage_installed,private_copy,port
import build_traversal_range
from studio_assets import Studio
OUT=ROOT/'docs/validation/traversal/wall-jump';CANDIDATE=ROOT/'build/wall-jump'

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    engine=engine_path(CANDIDATE/'native');mod=stage_installed(engine)
    for p in (CANDIDATE/'engine').iterdir():
        if p.is_file()and(p.suffix in ('.dll','.exe')or p.name=='vector-engine-build.json'):private_copy(p,engine/p.name)
    for relative,source in [('dlls/hl.dll',CANDIDATE/'server/hl.dll'),('cl_dlls/client.dll',CANDIDATE/'client/client.dll')]:private_copy(source,mod/relative)
    assets=json.loads((CANDIDATE/'assets.json').read_text())
    for a in assets:private_copy(a['candidate'],mod/a['relative'])
    build_traversal_range.OUT=CANDIDATE/'generated/traversal-range'
    private_copy(build_traversal_range.build(ensure=True),mod/'maps/vf_traversal.bsp')
    # Use the matching live network declarations, including existing agents'
    # changes, without publishing their work as part of this test.
    private_copy(ROOT.parent/'network/delta.lst',mod/'delta.lst')
    lines=['wait 180','developer 2','con_notifytime 0','gl_vsync 0','host_framerate .0166667','fps_max 60',
           'sv_cheats 1','god','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR','wait 45',
           'vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 15']
    def cmd(*items):lines.extend(items)
    def info(name):cmd('echo WJ_'+name,'cmd vf_traversal_info','vf_traversal_render_info','wait 1')
    def shot(name):cmd('screenshot scrshots/'+name+'.png','wait 1')
    video='--video'in sys.argv;motion_counts={}
    def advance(key,count):
        if not video:cmd('wait '+str(count));return
        for i in range(count):
            n=motion_counts.get(key,0);motion_counts[key]=n+1
            shot(key+'_motion_'+str(n).zfill(3))
    for view in ('first','third'):
        for turned in (False,True):
            key=view+('_turn'if turned else'_back')
            cmd('-jump','-back','-forward','-attack','cam_command 2',
                'cmd vf_traversal_place 238 -500 54 0','wait 2','+jump','wait 22','-jump','wait 20')
            if view=='third':cmd('cam_snapto 1','cam_idealdist 135','cam_idealyaw 90','cam_idealpitch 5','cam_command 1','wait 20')
            if turned:cmd('vf_traversal_look 180 0','wait 8')
            info(key+'_held');shot(key+'_held')
            cmd('+jump'if turned else'+back',*(['+jump']if not turned else[]));advance(key,3)
            info(key+'_release');shot(key+'_release');cmd('+attack');advance(key,3);info(key+'_busy');shot(key+'_push')
            cmd('-attack','-back','vf_traversal_look 180 0');advance(key,6)
            info(key+'_flight');shot(key+'_flight');advance(key,22)
            info(key+'_caught');shot(key+'_caught');cmd('wait 30');info(key+'_settled');shot(key+'_settled')
            cmd('-jump','cam_command 2','wait 5')
    # Ordinary climb remains the facing-wall Space command.
    cmd('cmd vf_traversal_place 238 0 54 0','wait 2','+jump','wait 22','-jump','wait 15','+jump','wait 6')
    info('climb');cmd('-jump','wait 70');info('climb_done');cmd('wait 3','quit')
    (mod/'wall_jump_test.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    args=[str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-dev','2',
          '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-windowed',
          '-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','wall-jump.log',
          '+sv_cheats','1','+developer','2','+maxplayers','1','+map','vf_traversal','+exec','wall_jump_test.cfg']
    process=subprocess.Popen(args,cwd=engine)
    try:process.wait(timeout=150)
    finally:
        if process.poll()is None:process.terminate();process.wait(timeout=8)
    text=(engine/'wall-jump.log').read_text(errors='replace');(OUT/'native.log').write_text(text)
    captures=OUT/'captures';captures.mkdir(exist_ok=True)
    for p in (mod/'scrshots').glob('*.png'):shutil.copy2(p,captures/p.name)
    pattern=r'WJ_(\w+)\s+VFTraversal phase=(\d+) state=(\d+) origin=([\d.,-]+) velocity=([\d.,-]+) time=([\d.-]+) health=([\d.-]+) clip=(-?\d+) reload=(\d+) sequence=(\d+) yaw=([\d.-]+) anchor=([\d.-]+)'
    cases={}
    for name,p,s,pos,vel,time,hp,clip,reload,seq,yaw,anchor in re.findall(pattern,text):
        cases[name]=dict(phase=int(p),state=int(s),origin=list(map(float,pos.split(','))),velocity=list(map(float,vel.split(','))),
            time=float(time),clip=int(clip),reload=int(reload),sequence=int(seq),yaw=float(yaw),wall_yaw=float(anchor))
    report=dict(cases=cases,assets=assets,binaries={n:hashlib.sha256((mod/p).read_bytes()).hexdigest()for n,p in [('client','cl_dlls/client.dll'),('server','dlls/hl.dll')]},
                engine={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in engine.iterdir()if p.suffix in('.dll','.exe')},
                delta_sha256=hashlib.sha256((mod/'delta.lst').read_bytes()).hexdigest())
    (OUT/'native.json').write_text(json.dumps(report,indent=2));print({k:v['phase']for k,v in cases.items()},flush=True)
    model=Studio(CANDIDATE/'generated/third-person/r01_tp.mdl')
    for view in ('first','third'):
        for mode in ('back','turn'):
            k=view+'_'+mode;held=cases[k+'_held'];release=cases[k+'_release'];busy=cases[k+'_busy'];flight=cases[k+'_flight'];caught=cases[k+'_caught']
            assert held['phase']==2 and release['phase']==7 and busy['phase']==7,(k,held,release,busy)
            assert bool(release['state']&32768)==(mode=='turn'),(k,release)
            assert release['velocity'][0]<-240 and release['velocity'][2]>200,(k,release)
            assert release['sequence']==model.sequences.index('vf_wall_jump_turn'if mode=='turn'else'vf_wall_jump'),(k,release)
            assert busy['clip']==held['clip'] and not busy['reload'],(k,busy)
            assert flight['phase']==7 and flight['origin'][2]>release['origin'][2],(k,flight)
            assert caught['phase']==2 and abs(caught['origin'][2]-120)<.1 and abs(caught['origin'][0]-114)<.1,(k,caught)
            assert cases[k+'_settled']['phase']==2,(k,cases[k+'_settled'])
            for frame in ('held','release','push','flight','caught','settled'):assert (captures/(k+'_'+frame+'.png')).exists()
    assert cases['climb']['phase']==4 and cases['climb_done']['phase']==0 and cases['climb_done']['origin'][2]>131,cases
    report['passed']=True;(OUT/'native.json').write_text(json.dumps(report,indent=2))
    if video:
        (OUT/'video.json').write_text(json.dumps(motion_counts,indent=2))
    print('PASS native wall jump: both commands, both views, higher recatch and ordinary climb',flush=True)

if __name__=='__main__':run()

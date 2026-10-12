"""Two continuous native runs of the concept-inspired traversal bay."""
import argparse,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'tests'))
import integration_native_test as audit
from native_workspace import port
from build_weapon_melee import digest
OUT=ROOT/'docs/videos/parcours-2026-10-12';BUNDLE=ROOT/'build/animation-feedback/candidate'

def record(probe_only=False,only=None):
    OUT.mkdir(parents=True,exist_ok=True);audit.SNAP=BUNDLE;audit.OUT=ROOT/'build/animation-feedback/course'
    engine,mod=audit.fixture('probe'if probe_only else'film')
    resources=[BUNDLE/'client/client.dll',BUNDLE/'server/hl.dll',BUNDLE/'engine/ref_gl.dll',BUNDLE/'engine/xash.dll',BUNDLE/'maps/vf_traversal.bsp']+list((BUNDLE/'models/vf_melee').glob('*.mdl'))+list((BUNDLE/'models/vf_r01').glob('r01_tp*.mdl'))
    hashes={str(p):digest(p)for p in resources}
    lines=['wait 180','developer 2','con_notifytime -1','host_framerate .016666667','gl_vsync 0','fps_max 1000','sv_cheats 1','god','hud_draw 0','vf_voice_subtitles 0','weapon_9mmAR','wait 45','vf_reference','wait 20','vf_item r01_receiver_a47__original','vf_item r01_feed_a__original','vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15']
    clips=[];counts={}
    def add(*items):lines.extend(items)
    def frame(key,n):
        if probe_only:add('wait '+str(n));return
        for _ in range(n):
            i=counts.get(key,0);counts[key]=i+1;add(f'screenshot scrshots/{key}_{i:04}.png','wait 1')
    def check(key,name):add('echo COURSE_'+key+'_'+name,'cmd vf_traversal_info')
    def look(yaw,pitch,view):
        add(f'vf_traversal_look {yaw} {pitch}')
        if view=='third':add(f'cam_idealyaw {90-yaw}')
    for view in ['first']if probe_only else[only]if only else['first','third']:
        key='parcours_'+view
        add('-jump','-back','-forward','-duck','-attack','-attack2','firstperson','wait 15','cmd vf_traversal_place 1440 882 36 0','vf_traversal_look 0 0','wait 15')
        add('cam_snapto 1','cam_idealdist 130','cam_idealyaw 90','cam_idealpitch 8','firstperson'if view=='first'else'thirdperson','r_drawviewmodel '+('1'if view=='first'else'0'))
        frame(key,24);add('vf_melee');frame(key,75)
        add('cmd vf_traversal_place 1440 882 36 0 320 0 0','+forward');frame(key,10)
        add('+duck');frame(key,16);check(key,'slide');frame(key,32)
        add('-duck');frame(key,58);check(key,'runup')
        look(60,0,view);add('+jump');frame(key,4);add('-jump');look(0,0,view);frame(key,18);check(key,'wallrun');frame(key,63);check(key,'wallrun_end')
        look(0,-5,view);add('+jump');frame(key,3);check(key,'wall_push');add('-forward');frame(key,30);add('-jump');frame(key,18);check(key,'held')
        look(0,0,view);frame(key,24)
        add('+back','+jump');frame(key,3);check(key,'backjump');add('-back')
        for yaw in range(15,181,15):look(yaw,0,view);frame(key,1)
        frame(key,28);check(key,'caught');add('-jump');frame(key,30)
        add('+jump');frame(key,5);check(key,'climb');add('-jump');frame(key,65);check(key,'finish');frame(key,30)
        clips.append(dict(key=key,feature='parcours',view=view,frames=counts.get(key,0)))
    add('quit')
    for part,start in enumerate(range(0,len(lines),70)):
        chunk=lines[start:start+70]
        if start+70<len(lines):chunk.append(f'exec course_{part+1}.cfg')
        (mod/f'course_{part}.cfg').write_text('\n'.join(chunk)+'\n')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','course.log','+maxplayers','1','+map','vf_traversal','+exec','course_0.cfg'],cwd=engine)
    try:process.wait(180);assert process.returncode==0
    finally:
        if process.poll()is None:process.terminate();process.wait(10)
    log=(engine/'course.log').read_text(errors='replace');(OUT/('probe.log'if probe_only else'native.log')).write_text(log)
    states={}
    for name,block in re.findall(r'COURSE_(\w+)\s+(.*?)(?=COURSE_|$)',log,re.S):
        row=re.search(r'VFTraversal phase=(\d+) state=(\d+) origin=([-\d.,]+) velocity=([-\d.,]+)',block)
        assert row,(name,block[:400]);states[name]=dict(phase=int(row[1]),state=int(row[2]),origin=list(map(float,row[3].split(','))),velocity=list(map(float,row[4].split(','))))
    print(json.dumps(states,indent=2),flush=True)
    (OUT/('probe.json'if probe_only else'states.json')).write_text(json.dumps(states,indent=2))
    if probe_only:return states
    previous=json.loads((OUT/'capture.json').read_text())if only else None
    if previous:
        assert previous['sources']==hashes,'Do not combine footage from different game bundles'
        previous['states'].update(states);states=previous['states']
    for view in ['first','third']:
        for name,expected in [('slide',5),('wallrun',8),('held',2),('backjump',7),('caught',2),('climb',4),('finish',0)]:
            assert states['parcours_'+view+'_'+name]['phase']==expected,(view,name,states)
    captures=OUT/'captures';captures.mkdir(exist_ok=True)
    for clip in clips:
        for i in range(clip['frames']):
            source=mod/'scrshots'/f"{clip['key']}_{i:04}.png";assert source.is_file();shutil.copy2(source,captures/source.name)
    # A clearly labelled slow-motion replay makes the early turn/reach legible.
    for i in range(180):
        source=captures/f'parcours_third_{360+i//2:04}.png'
        shutil.copy2(source,captures/f'rebond_detail_{i:04}.png')
    clips.append(dict(key='rebond_detail',feature='rebond_detail',view='third',frames=180))
    if previous:
        clips=[next((c for c in clips if c['key']==old['key']),old)for old in previous['clips']]
    assert hashes=={str(p):digest(p)for p in resources}
    report=dict(passed=True,width=1280,height=720,fps=60,clips=clips,states=states,frames_directory=str(captures),sources=hashes,
        concept=str(ROOT/'concept-art/2026-10-12-parcours/06-librairie-etude-de-volumes.png'),capture_kind='Native gameplay; each route is continuous after its initial setup.')
    (OUT/'capture.json').write_text(json.dumps(report,indent=2));print('PASS two continuous slide/wallrun/rebound/recatch/climb runs',flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true');parser.add_argument('--only',choices=['first','third']);args=parser.parse_args();record(args.probe,args.only)

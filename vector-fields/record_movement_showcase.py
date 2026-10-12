"""Record current installed gameplay, frame by frame, in an isolated native session."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'tests'))
import integration_native_test as audit
from native_workspace import port
from release import check_native_interface
OUT=ROOT/'docs/videos/mouvements-2026-10-12';SNAP=ROOT/'build/movement-video/installed';LIVE=PROJECT/'runtime/vector-engine'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def record(only=None):
    OUT.mkdir(parents=True,exist_ok=True);SNAP.mkdir(parents=True,exist_ok=True)
    files=[p for p in LIVE.iterdir()if p.is_file()and(p.suffix.lower()in ['.dll','.exe']or p.name=='vector-engine-build.json')]
    for p in files:
        target=SNAP/'engine'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    for src,dst in [('cl_dlls/client.dll','client/client.dll'),('dlls/hl.dll','server/hl.dll'),('delta.lst','delta.lst')]:
        source=LIVE/'vf_visual'/src;target=SNAP/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);files.append(source)
    for folder in ['vf','maps','models']:
        shutil.copytree(LIVE/'vf_visual'/folder,SNAP/folder,dirs_exist_ok=True)
    files+=list((LIVE/'vf_visual/models').rglob('*.mdl'))
    before={str(p.relative_to(PROJECT)):sha(p)for p in files}
    check_native_interface(SNAP/'engine',SNAP/'client/client.dll')
    audit.SNAP=SNAP;audit.OUT=ROOT/'build/movement-video/native';engine,mod=audit.fixture('showcase')
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667',
        'sv_cheats 1','god','vf_voice_subtitles 0','hud_draw 0','weapon_9mmAR','wait 45',
        'vf_reference','wait 20','vf_item r01_receiver_a47__original','vf_item r01_feed_a__original',
        'vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15']
    clips=[];counts={}
    def add(*items):lines.extend(items)
    def view(which,yaw=100,dist=110):
        add('cam_snapto 1',f'cam_idealdist {dist}',f'cam_idealyaw {yaw}','cam_idealpitch 6',
            'firstperson'if which=='first'else'thirdperson','r_drawviewmodel '+('1'if which=='first'else'0'))
    def frames(key,count):
        for _ in range(count):
            n=counts.get(key,0);counts[key]=n+1;add(f'screenshot scrshots/{key}_{n:04}.png','wait 1')
    def probe(name,kind='traversal'):
        add('echo VIDEO_'+name, 'cmd vf_melee_info'if kind=='melee'else'cmd vf_traversal_info','vf_engine_stats')
    def clear():add('-jump','-back','-forward','-duck','-attack','-attack2','-reload','cam_command 2','wait 15')
    for feature in ['melee','wallrun','backjump','reload']:
        for which in ['first','third']:
            key=feature+'_'+which
            if only and key not in only.split(','):continue
            clips.append(dict(key=key,feature=feature,view=which))
            clear()
            if feature=='melee':
                add('cmd vf_melee_place -500 -600 36 0 0','vf_traversal_look 0 0','wait 20');view(which,120,100)
                frames(key,30);add('vf_melee');frames(key,20);probe(key+'_active','melee');frames(key,70)
                add('vf_melee');frames(key,20);probe(key+'_repeat','melee');frames(key,70)
            elif feature=='wallrun':
                add('cmd vf_traversal_place -800 -1006 128 0 320 0 0','vf_traversal_look 300 0','+forward','+jump','wait 3','-jump','vf_traversal_look 0 0','wait 5');view(which,-130,105)
                if which=='third':add('cam_idealpitch 14')
                frames(key,30)
                frames(key,10)
                add('-jump');probe(key+'_active');frames(key,35)
                if which=='first':
                    for pitch in [10,20,30,40,50,60,65]:add(f'vf_traversal_look 0 {pitch}');frames(key,1)
                    frames(key,24)
                    for pitch in [60,50,40,30,20,10,0]:add(f'vf_traversal_look 0 {pitch}');frames(key,1)
                    frames(key,37)
                else:frames(key,75)
                probe(key+'_running');add('vf_traversal_look 60 -15')
                if which=='third':add('cam_idealyaw -190')
                add('+jump');frames(key,3);probe(key+'_exit');add('-jump');frames(key,57)
                # A second take shows the new free-look limits independently
                # of the active jump impulse demonstrated just above.
                clear()
                add('cmd vf_traversal_place -800 -1006 128 300 320 0 0','vf_traversal_look 300 0',
                    '+forward','+jump','wait 3','-jump','vf_traversal_look 0 0','wait 5');view(which,-130,105)
                frames(key,15)
                for yaw in [30,60,90]:
                    add(f'vf_traversal_look {yaw} 0')
                    if which=='third':add(f'cam_idealyaw {-130-yaw}')
                    frames(key,10)
                probe(key+'_free_running')
                add('vf_traversal_look 90.1 0')
                if which=='third':add('cam_idealyaw -220.1')
                frames(key,3);probe(key+'_angle_exit');frames(key,35)
            elif feature=='backjump':
                add('cmd vf_traversal_place 238 -500 54 0','vf_traversal_look 0 0','wait 2','+jump','wait 22','-jump','wait 20')
                view(which,90,135);frames(key,30);probe(key+'_held')
                add('+back','+jump');frames(key,3);probe(key+'_push');frames(key,3);add('-back')
                for yaw in range(18,181,18):
                    add(f'vf_traversal_look {yaw} 0')
                    if which=='third':add(f'cam_idealyaw {90-yaw}')
                    frames(key,1)
                frames(key,20);probe(key+'_caught');frames(key,60);add('-jump')
            else:
                add('cmd vf_melee_place -500 -600 36 0 0','vf_traversal_look 0 0','wait 20');view(which,120,100)
                add('+duck','wait 25','+attack','wait 5','-attack','wait 20');frames(key,15)
                add('+reload');frames(key,10);probe(key+'_active');add('-reload');frames(key,145)
    add('quit')
    for part,start in enumerate(range(0,len(lines),70)):
        chunk=lines[start:start+70]
        if start+70<len(lines):chunk.append(f'exec showcase_{part+1}.cfg')
        (mod/f'showcase_{part}.cfg').write_text('\n'.join(chunk)+'\n')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
        '-console','-nointro','-nowriteconfig','-log','movement-video.log','+sv_cheats','1','+maxplayers','1','+map','vf_traversal','+exec','showcase_0.cfg'],cwd=engine)
    try:process.wait(360);assert process.returncode==0
    finally:
        if process.poll()is None:process.terminate();process.wait(10)
    log=(engine/'movement-video.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
    assert not any(e in log for e in ['Host_Error','SV_Error','VFState rejected','not precached'])
    blocks=dict(re.findall(r'VIDEO_(\w+)\s+(.*?)(?=VIDEO_|$)',log,re.S));states={}
    for name,block in blocks.items():
        if name.startswith('melee'):
            assert re.search(r'VFMelee server: active=1 .*model=models/vf_melee/',block),(name,'strike did not start')
            states[name]=1
        elif name.startswith('reload'):
            assert re.search(r'VFTraversal phase=0 .*reload=1',block),(name,'crouched reload did not start')
            states[name]=0
        else:
            match=re.search(r'VFTraversal phase=(\d+)',block);assert match,(name,block[:400]);states[name]=int(match[1])
            expected=8 if name.endswith(('active','running'))else 0 if name.endswith('exit')else 7 if name.endswith('push')else 2
            assert int(match[1])==expected,(name,'wrong movement phase',int(match[1]),expected)
    captures=OUT/'captures';captures.mkdir(exist_ok=True)
    for clip in clips:
        clip['frames']=counts[clip['key']]
        for i in range(clip['frames']):
            p=mod/'scrshots'/f"{clip['key']}_{i:04}.png";assert p.is_file();shutil.copy2(p,captures/p.name)
    assert before=={str(p.relative_to(PROJECT)):sha(p)for p in files},'Installed build changed during recording'
    report=dict(passed=True,fps=60,width=1280,height=720,clips=clips,states=states,
        installed_sources=before,frames_directory=str(captures),capture_kind='Actual installed gameplay; a private scene uses developer positioning between clips.')
    if only and (OUT/'capture.json').exists():
        old=json.loads((OUT/'capture.json').read_text());old['clips']=[next((c for c in clips if c['key']==previous['key']),previous)for previous in old['clips']]
        old['states'].update(states);old['installed_sources']=before;old['updated_clips']=clips;report=old
        (OUT/(only.replace(',','-')+'-native.log')).write_text(log)
    (OUT/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS main-build video capture:',sum(counts.values()),'frames;',states,flush=True)
    return report
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--only');record(parser.parse_args().only)

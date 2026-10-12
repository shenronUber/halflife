"""Ordinary locomotion remains animated in both real Studio body views."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from headgear_preview import stage,asset_library
from native_workspace import private_copy,port
OUT=ROOT/'docs/validation/traversal/wall-jump/walking';CANDIDATE=ROOT/'build/wall-jump'

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    engine,mod=stage('wall-jump-walking',CANDIDATE)
    for a in json.loads((CANDIDATE/'assets.json').read_text()):private_copy(a['candidate'],mod/a['relative'])
    (mod/'maps').mkdir(exist_ok=True)
    private_copy(CANDIDATE/'generated/traversal-range/vf_traversal.bsp',mod/'maps/vf_traversal.bsp')
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','host_framerate .0166667','fps_max 60',
           'sv_cheats 1','god','vf_voices 0','vf_voice_subtitles 0','hud_draw 0','weapon_9mmAR','wait 35',
           'vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 10']
    events=[]
    for view in ('first','third'):
        for direction,inputs in [('forward',['+forward']),('diagonal',['+forward','+moveright']),('sideways',['+moveleft']),('backward',['+back'])]:
            key=view+'_'+direction;events.append(key)
            lines+=['-forward','-back','-moveright','-moveleft','-speed','cam_command 2','wait 10',
                    'cmd vf_traversal_place 128 -750 36 0','wait 3','vf_traversal_look 0 85','wait 10']
            if view=='third':lines+=['vf_traversal_look 0 0','cam_snapto 1','cam_idealdist 105','cam_idealyaw 100','cam_idealpitch 12','cam_command 1','wait 10']
            # +speed exercises the ordinary walking gait, rather than slide
            # velocity or scripted animation. Only real movement keys act.
            lines+=['+speed',*inputs,'wait 12','echo WALK_'+key+'_BEGIN','cmd vf_traversal_info','wait 1']
            for i in range(36):
                if i in (0,9,18,27,35):lines+=['screenshot scrshots/'+key+'_'+str(i).zfill(2)+'.png']
                lines+=['wait 1']
            lines+=['cmd vf_traversal_info','wait 1','echo WALK_'+key+'_END','wait 1']
    lines+=['-forward','-back','-moveright','-moveleft','-speed','cam_command 2','wait 12',
            'echo WALK_STOP_BEGIN','cmd vf_traversal_info','wait 35','cmd vf_traversal_info','wait 1','echo WALK_STOP_END','wait 2','quit']
    for part,start in enumerate(range(0,len(lines),100)):
        chunk=lines[start:start+100]
        if start+100<len(lines):chunk.append('exec walk_'+str(part+1).zfill(3)+'.cfg')
        (mod/('walk_'+str(part).zfill(3)+'.cfg')).write_text('\n'.join(chunk)+'\n')
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),'-dev','2',
        '-rodir',str(asset_library()),'-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig',
        '-log','walking.log','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','walk_000.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:p.wait(timeout=150);assert p.returncode==0
    finally:
        if p.poll()is None:p.terminate();p.wait(timeout=8)
    text=(engine/'walking.log').read_text(errors='replace');(OUT/'native.log').write_text(text)
    assert not any(s in text for s in ('Host_Error','SV_Error','VFState rejected','Could not load'))
    cases={}
    for key in events:
        block=text.split('WALK_'+key+'_BEGIN')[1].split('WALK_'+key+'_END')[0]
        rows=re.findall(r'VFBodyFeet phase=(\d+) hip=([\d.,-]+) left=([\d.,-]+) right=([\d.,-]+) own=(\d+) origin=([\d.,-]+) look=([\d.,-]+)',block)
        rows=[r for r in rows if r[0]=='0'and r[4]==('1'if key.startswith('first')else'0')]
        assert len(rows)>15,(key,'Body is not rendered as a moving Studio model',len(rows))
        relative=[]
        for _,hip,left,right,own,origin,look in rows:
            hip=np.array(list(map(float,hip.split(','))))
            # Cancel translation and hip bob: this measures actual leg motion.
            relative.append(np.r_[np.array(list(map(float,left.split(','))))-hip,
                                  np.array(list(map(float,right.split(','))))-hip])
        feet=np.array(relative);swing=np.ptp(feet,axis=0)
        assert max(swing[:3])>2 and max(swing[3:])>2,(key,'Frozen feet',swing)
        states=re.findall(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+) velocity=([\d.,-]+)',block)
        assert len(states)==2 and all(r[0]=='0'for r in states),(key,states)
        origins=np.array([list(map(float,r[1].split(',')))for r in states])
        distance=float(np.linalg.norm(origins[1,:2]-origins[0,:2]));assert distance>30,(key,'No actual movement',distance)
        assert np.max(np.abs(origins[:,2]-36.031))<.1,(key,'Walking changes collision height',origins)
        cases[key]=dict(rendered_samples=len(rows),distance=distance,left_swing=float(max(swing[:3])),right_swing=float(max(swing[3:])))
        for frame in (0,9,18,27,35):shutil.copy2(mod/'scrshots'/(key+'_'+str(frame).zfill(2)+'.png'),OUT/(key+'_'+str(frame).zfill(2)+'.png'))
    stop=text.split('WALK_STOP_BEGIN')[1].split('WALK_STOP_END')[0]
    velocities=re.findall(r'VFTraversal phase=0 state=\d+ origin=[\d.,-]+ velocity=([\d.,-]+)',stop)
    assert velocities and np.linalg.norm(list(map(float,velocities[-1].split(','))))<.1,('Stopping should clear momentum',velocities)
    board=Image.new('RGB',(1920,824),'#141e27');draw=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
    for i,key in enumerate(('first_forward','first_diagonal','first_sideways','third_forward','third_diagonal','third_sideways')):
        x=(i%3)*640;y=(i//3)*412
        draw.text((x+8,y+5),key.replace('_',' '),font=font,fill='white')
        board.paste(Image.open(OUT/(key+'_18.png')).resize((640,360)),(x,y+32))
    board.save(OUT/'walking-review.jpg',quality=93)
    report=dict(passed=True,cases=cases,stops=True,views=2,walking_directions=4,
        binaries={n:hashlib.sha256((mod/p).read_bytes()).hexdigest()for n,p in [('client','cl_dlls/client.dll'),('server','dlls/hl.dll')]},
        renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest(),
        delta_sha256=hashlib.sha256((mod/'delta.lst').read_bytes()).hexdigest(),
        assets={a['relative']:hashlib.sha256((mod/a['relative']).read_bytes()).hexdigest()for a in json.loads((CANDIDATE/'assets.json').read_text())})
    (OUT/'native.json').write_text(json.dumps(report,indent=2));print('PASS ordinary walking:',json.dumps(cases),flush=True)

if __name__=='__main__':run()

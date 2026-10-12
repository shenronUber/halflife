"""Forward slide visibility with world-fixed legs and unchanged external pose."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from slide_feet_bundle import prepare_slide_feet
from native_workspace import port
OUT=ROOT/'docs/validation/traversal/slide-presentation'

def run(candidate=None):
    engine,mod=prepare_slide_feet('slide-presentation',build=candidate or ROOT/'build',
                                  engine_binaries=candidate/'engine' if candidate else ROOT.parent/'runtime/vector-engine')
    lines=['wait 180','gl_vsync 0','host_framerate .016666667','fps_max 60','developer 2','con_notifytime -1',
           'hud_draw 0','vf_headgear_hud 0','vf_voice_subtitles 0','sv_cheats 1','god','weapon_9mmAR','wait 20',
           'vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
    cases=[(f'offset_{offset}',offset,0,0,False) for offset in (-18,0,16,24,32,40)]
    cases += [(name,0,yaw,pitch,False) for name,yaw,pitch in
              [('look_down',0,20),('look_ground',0,55),('look_steep',0,80),('look_left',90,0),('look_back',180,0)]]
    cases += [('external_old',-18,0,0,True),('external_new',32,0,0,True)]
    for name,offset,yaw,pitch,external in cases:
        lines += ['-duck','wait 90','cam_command 2',f'vf_slide_body_forward {offset}',
                  'cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck']
        if external:lines += ['cam_snapto 1','cam_idealdist 100','cam_idealyaw 110','cam_idealpitch 4','cam_command 1']
        lines += ['wait 24',f'vf_traversal_look {yaw} {pitch}','wait 1',f'echo PRESENT_{name}_BEGIN',
                  'cmd vf_traversal_info',f'screenshot scrshots/{name}.png','wait 1',f'echo PRESENT_{name}_END']
    lines += ['-duck','cam_command 2','wait 100','echo PRESENT_FINISHED','cmd vf_traversal_info','wait 2','quit']
    for index,start in enumerate(range(0,len(lines),100)):
        chunk=lines[start:start+100]
        if start+100<len(lines):chunk.append(f'exec presentation_{index+1:03}.cfg')
        (mod/f'presentation_{index:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2',
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
        '-console','-nointro','-nowriteconfig','-log','presentation.log','-port',str(port()),'-clientport',str(port()),
        '+exec','lab_controls.cfg','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','presentation_000.cfg'],
        cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:child.wait(timeout=150);assert child.returncode==0
    finally:
        if child.poll() is None:child.terminate();child.wait(timeout=8)
    text=(engine/'presentation.log').read_text(errors='replace')
    assert 'native extension v4 connected' in text
    assert not any(e in text for e in ('Host_Error','SV_Error','VFState rejected'))
    assert not re.search(r'Unknown command[^\n]*vf_slide_body_forward',text),'Presentation renderer must be connected'
    def block(name):return text.split('PRESENT_'+name+'_BEGIN')[1].split('PRESENT_'+name+'_END')[0]
    pattern=r'VFBodyFeet phase=5 hip=([\d.,-]+) left=([\d.,-]+) right=([\d.,-]+) own=(\d) origin=([\d.,-]+) look=([\d.,-]+)'
    def pose(name,own):
        rows=[r for r in re.findall(pattern,block(name)) if int(r[3])==own]
        assert rows,('Missing actual rendered feet',name,own)
        return np.concatenate([np.array(list(map(float,p.split(',')))) for p in rows[0][:3]])
    views=[pose(name,1) for name in ('offset_0','look_down','look_ground','look_steep','look_left','look_back')]
    drift=float(np.max(np.ptp(np.array(views),axis=0)))
    assert drift<.05,('Camera must not rotate or translate the presentation legs',drift)
    external_drift=float(np.max(np.abs(pose('external_new',0)-pose('external_old',0))))
    assert external_drift<.05,('Subjective visibility adjustment must leave the external pose alone',external_drift)
    assert re.search(r'PRESENT_FINISHED\s+VFTraversal phase=0 ',text)
    images={name:np.array(Image.open(mod/'scrshots'/(name+'.png')).convert('RGB'),dtype=np.int16) for name,_,_,_,_ in cases}
    # Identical timed slides isolate the new leg silhouette from the gun/sleeve.
    difference=np.max(np.abs(images['offset_0']-images['offset_-18']),axis=2)>24
    visible=int(difference[400:700,40:600].sum())
    assert visible>3000,('Forward view must visibly communicate the seated leg',visible)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,_,_,_,_ in cases:shutil.copy2(mod/'scrshots'/(name+'.png'),OUT/(name+'.png'))
    shutil.copy2(engine/'presentation.log',OUT/'native.log')
    board=Image.new('RGB',(1920,788),'#141e27');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    for index,(name,label) in enumerate([('offset_-18','Avant : regard droit'),('offset_0','Présentation 0'),('offset_32','Décalage 32'),
                                        ('offset_40','Décalage 40'),('look_down','Regard un peu baissé'),('external_new','Pose extérieure')]):
        x=(index%3)*640;y=(index//3)*394;draw.text((x+10,y+5),label,font=font,fill='#e3efed')
        board.paste(Image.open(OUT/(name+'.png')).resize((640,360)),(x,y+34))
    image=ROOT/'docs/images/slide-forward-presentation.jpg';board.save(image,quality=94)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(passed=True,forward_leg_pixels=visible,look_pose_drift=drift,external_pose_drift=external_drift,
                slide_look_cases=len(views),forward_offset=0,image=str(image),
                renderer_sha256=digest(engine/'ref_gl.dll'),client_sha256=digest(mod/'cl_dlls/client.dll'),
                server_sha256=digest(mod/'dlls/hl.dll'),
                models={str(p.relative_to(mod)):digest(p) for group in ('vf_r01','vf_traversal','vf_skins') for p in (mod/'models'/group).glob('*.mdl')})
    (OUT/'native.json').write_text(json.dumps(report,indent=2));print('PASS slide presentation:',json.dumps({k:v for k,v in report.items() if k!='models'}),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate-dir',type=Path);run(p.parse_args().candidate_dir)

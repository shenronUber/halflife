"""Capture the seated slide with its legs and R1 gun in the actual FPS renderer."""
import argparse,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from slide_feet_bundle import prepare_slide_feet,digest
from native_workspace import port
OUT=ROOT/'docs/validation/traversal/slide-review'

def run(candidate=None):
    engine,mod=prepare_slide_feet('slide-review',build=candidate or ROOT/'build',engine_binaries=candidate/'engine' if candidate else ROOT.parent/'runtime/vector-engine')
    lines=['wait 180','gl_vsync 0','host_framerate 0.0166667','fps_max 60','developer 2','con_notifytime -1','cmd give weapon_9mmAR',
        'weapon_9mmAR','wait 20','vf_reference 0','wait 30','vf_commit','wait 35',
        'vf_character','vf_character','wait 12','cmd vf_traversal_place 128 -750 36 0 400 0 0',
        'wait 1','+duck','wait 20','echo SLIDE_REVIEW_START','cmd vf_traversal_info',
        'screenshot scrshots/slide_start.png','wait 10','echo SLIDE_REVIEW_LOOP','cmd vf_traversal_info',
        'screenshot scrshots/slide_forward.png','wait 4','vf_traversal_look 0 55','wait 5',
        'screenshot scrshots/slide_down.png','wait 4','vf_traversal_look 0 0','cam_snapto 1',
        'cam_idealdist 100','cam_idealyaw 110','cam_idealpitch 4','cam_command 1','wait 10',
        'screenshot scrshots/slide_body.png','wait 4','cam_command 2','-duck','wait 40',
        'echo SLIDE_REVIEW_END','cmd vf_traversal_info','screenshot scrshots/slide_end.png','wait 4','vf_engine_stats','quit']
    (mod/'slide_review.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    log=engine/'slide-review.log'
    if log.exists():log.unlink()
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig',
        '-dev','2','-log',log.name,'-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+developer','2','+maxplayers','1','+map','vf_traversal',
        '+exec','slide_review.cfg'],cwd=engine)
    try:process.wait(timeout=45)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    text=log.read_text(errors='replace')
    assert re.search(r'VFEngine: native extension v4 connected',text),'R1 renderer must be connected'
    assert 'VF catalogue:'not in text and 'rejected=0'in text,'Invalid R1 assembly'
    phases=re.findall(r'SLIDE_REVIEW_(START|LOOP|END)\s+VFTraversal phase=(\d+)',text)
    assert phases==[('START','5'),('LOOP','5'),('END','0')],phases
    body_phases=list(map(int,re.findall(r'VFFirstPersonBody parts=\d+ mask=\d+ phase=(\d+)',text)))
    assert 0 in body_phases and 5 in body_phases,'Equipped world body must supply the seated slide legs'
    after=text.split('SLIDE_REVIEW_END',1)[1]
    assert re.search(r'VFFirstPersonBody .*phase=0 ',after),'Body must return after slide'
    OUT.mkdir(parents=True,exist_ok=True)
    for p in (mod/'scrshots').glob('slide_*.png'):shutil.copy2(p,OUT/p.name)
    from PIL import Image
    import numpy as np
    frame=np.array(Image.open(OUT/'slide_down.png').convert('RGB'),dtype=float)
    blue=(frame[:,:,2]>frame[:,:,0]*1.2)&(frame[:,:,2]>frame[:,:,1]*1.1)&(frame[:,:,2]>40)
    # Feet are projected from the world pose; looking down reveals them.
    # A forward view no longer forces a camera-attached boot into the frame.
    visible=int(blue[340:720,150:1100].sum())
    assert visible>2000,('leading trouser leg must remain visible',visible)
    upper_blue=int(blue[70:340,280:1150].sum())
    report=dict(phases=phases,leg_pixels=visible,upper_leg_pixels=upper_blue,world_slide_body=True,
                permanent_body_restored_after_slide=True,client_sha256=digest(mod/'cl_dlls/client.dll'),
                renderer_sha256=digest(engine/'ref_gl.dll'),slide_model_sha256=digest(mod/'models/vf_traversal/slide_legs.mdl'))
    (OUT/'visibility.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    shutil.copy2(log,OUT/log.name)
    print('PASS native seated slide: world legs visible when looking down, third-person pose and return to equipped stance.',json.dumps(report))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-dir',type=Path);run(parser.parse_args().candidate_dir)

"""Actual server inventory, smooth headgear gesture, FP/TP matrices and saves."""
import argparse,json,re,subprocess,sys,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from headgear_preview import stage,asset_library

def run(quick=False,devtest=False,candidate=None):
    engine,mod=stage('headgear-action-devtest' if devtest else 'headgear-action-native',candidate)
    if devtest:
        from headgear_devtest import install
        install(mod)
    captures=[]
    def snap(name,wait=0):
        captures.append(name)
        return f'wait {wait}\nscreenshot scrshots/{name}.png\nwait 1\n' if wait else f'screenshot scrshots/{name}.png\nwait 1\n'
    helmets=json.loads((ROOT/'data/headgear.json').read_text())
    if quick:helmets=helmets[:1]
    script='wait 180\ndeveloper 2\ncon_notifytime -1\ngl_vsync 0\nfps_max 60\nhost_framerate .016666667\nsv_cheats 1\nweapon_9mmAR\nwait 45\n'
    script+='vf_headgear_audit\ncmd vf_body_info\n'
    for view in ('fp','tp'):
        script+=('firstperson\n' if view=='fp' else 'thirdperson\ncam_idealdist 80\ncam_idealyaw 160\ncam_idealpitch 5\n')+'wait 30\n'
        for h in helmets:
            key=h['id']
            script+=f'vf_operator\nwait 25\nvf_item {key}\nvf_commit\nwait 25\n'
            if view=='fp':script+=snap(key+'_inventory')
            script+='vf_operator\nwait 10\n'
            script+=snap(key+'_'+view+'_down')
            for direction in ('up','down'):
                # A second request during the gesture must be rejected server-side.
                script+='vf_headgear_toggle\nvf_headgear_toggle\n'
                phases=(('reach',16),('move',16),('return',16),('end',25))
                if view=='fp' and key==helmets[0]['id'] and direction=='up':
                    phases=(('present',6),('rise',5),('reach',1),('above',13),('move',7),('return',16),('end',25))
                for phase,frames in phases:
                    script+=snap(f'{key}_{view}_{direction}_{phase}',frames)
                script+='vf_headgear_info\ncmd vf_body_info\nwait 8\n'
    # Inspect actual hand-to-equipment contact from both sides of the wrist.
    # Use the native orbit camera rather than inferring orientation from IK.
    script+='thirdperson\ncam_snapto 1\ncam_idealdist 42\ndefault_fov 65\nhud_draw 0\n'
    for h in helmets:
        key=h['id']
        script+=f'vf_operator\nwait 25\nvf_item {key}\nvf_commit\nwait 25\nvf_operator\nwait 10\n'
        cameras=[(180,0,'front'),(270,0,'left'),(225,0,'oblique')]
        if devtest:cameras.append((180,35,'top'))
        for angle,pitch,label in cameras:
            script+=f'cam_idealyaw {angle}\ncam_idealpitch {pitch}\nwait 12\nvf_headgear_toggle\n'
            script+=snap(key+'_contact_'+label,23)
            script+='wait 60\nvf_headgear_toggle\nwait 90\n'
    script+='cam_snapto 0\ndefault_fov 90\nhud_draw 1\n'
    # Save an equipped, raised mask and restore both independent states.
    script+='firstperson\nvf_operator\nwait 25\nvf_item helmet_gas_mask\nvf_commit\nwait 25\nvf_operator\nwait 10\ncmd vf_headgear_toggle\nwait 85\nsave vf_headgear_action\nwait 45\nload vf_headgear_action\nwait 180\ndeveloper 2\ncon_notifytime 0\nvf_headgear_info\ncmd vf_request\nwait 20\nvf_operator\nwait 25\n'
    script+=snap('headgear_after_save')+'vf_operator\nwait 10\nvf_headgear_info\nvf_engine_stats\nquit\n'
    (mod/'action.cfg').write_text(script,encoding='ascii')
    started=time.time()
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir',str(asset_library()),'-game',mod.name,
        '-dev','2','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','headgear-action.log',
        '-port','27165' if devtest else '27161','-clientport','27166' if devtest else '27162',
        '+exec','lab_controls.cfg','+sv_cheats','1','+map','vf_range','+exec','action.cfg'],cwd=engine)
    try:p.wait(timeout=240)
    finally:
        if p.poll() is None:p.terminate();p.wait(timeout=10)
    log=(engine/'headgear-action.log').read_text(errors='replace')
    prefix='devtest-' if devtest else ''
    (ROOT/'build/headgear-action'/(prefix+('native-run-quick.json' if quick else 'native-run.json'))).write_text(json.dumps({'engine':str(engine),'mod':str(mod),'captures':captures,'returncode':p.returncode},indent=2))
    assert p.returncode==0,p.returncode
    assert 'v4 connected' in log and 'VFState rejected' not in log
    assert 'VFHeadgear audit: carriers=4 variants=12 passed=48 failed=0' in log
    assert not any(x in log for x in ('Host_Error','SV_Error','Could not load'))
    actions=re.findall(r'VFHeadgear action: player=1 item=(\S+) raised=(\d)',log)
    assert len(actions)==len(helmets)*(12 if devtest else 10)+1,(len(actions),actions)
    poses=re.findall(r'VFHeadgear pose: view=(\d) type=(\d) phase=([\d.]+) reach=([\d.]+) right_error=([\d.]+) weapon_error=([\d.]+)',log)
    assert poses and max(float(v[4]) for v in poses)<1e-6 and max(float(v[5]) for v in poses)<1e-6
    palm_samples=re.findall(r'VFHeadgear pose: view=(\d).*?reach=([\d.]+).*?wrist_normal=([\d.-]+) extension=([\d.]+)',log)
    engaged=[v for v in palm_samples if float(v[1])>.999]
    assert engaged and all(.93<float(v[2])<.95 for v in engaged if v[0]=='0'),'third-person palm must face the forehead, with the back facing outward'
    assert all(-.3<float(v[2])<-.2 for v in engaged if v[0]=='1'),'the first-person hand must present its thumb edge'
    assert 'VFHeadgear sleeve:' not in log,'the rejected sleeve deformation must be removed'
    assert b'VFHeadgear sleeve:' not in (engine/'ref_gl.dll').read_bytes(),'the renderer must not retain the sleeve deformation'
    view_path=re.findall(r'VFHeadgear pose: view=1.*?phase=([\d.]+).*?palm_y=([\d.-]+)',log)
    above=[float(y) for p,y in view_path if .34<float(p)<.68]
    assert above and min(above)>.7,'the hand must leave the upper frame while operating the headgear'
    for h in helmets:
        for view in ('0','1'):
            samples=[float(v[2]) for v in poses if v[0]==view and int(v[1])==h['type']]
            assert samples and min(samples)<.2 and max(samples)>.8,(h['id'],view,samples[:5])
    # Every actual raise AND lower must contain arm poses; an aggregate check
    # could otherwise overlook a first-message interpolation rewind.
    for block in log.split('VFHeadgear action:')[1:]:
        before_next=block.split('VFHeadgear action:')[0]
        assert 'VFHeadgear pose:' in before_next
    after=log.split('Loading game from save/vf_headgear_action.sav')[-1]
    assert 'VFHeadgear state: player=1 raised=1 elapsed=0' in after
    assert 'VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1' in log
    for name in captures:
        path=mod/'scrshots'/(name+'.png');assert path.stat().st_mtime>=started
        assert Image.open(path).size==(1280,720)
    thumb_front_pixels=None
    if devtest:
        # The frontal contact shot must hide the yellow thumb geometrically.
        # Inspect the hand region, excluding the gun hand and world markers.
        hand=Image.open(mod/'scrshots'/f'{helmets[0]["id"]}_contact_front.png').convert('RGB').crop((640,140,880,410))
        thumb_front_pixels=sum(r>200 and g>175 and b<80 for r,g,b in hand.getdata())
        assert thumb_front_pixels==0,('thumb must stay on the hidden side in front view',thumb_front_pixels)
    report=dict(passed=True,actions=len(actions),pose_samples=len(poses),first_and_third_person=True,
        max_right_hand_error=max(float(v[4])for v in poses),max_weapon_error=max(float(v[5])for v in poses),
        equipped_raised_save_restored=True,spam_rejected=True,captures=captures,
        palm_orientation_checked=True,third_person_palm_inward=True,third_person_palm_toward_forehead=True,
        first_person_overhead_path=True,first_person_hand_on_edge=True,first_person_simple_lift=True,
        sleeve_deformation_removed=True,
        client_sha256=__import__('hashlib').sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),
        renderer_sha256=__import__('hashlib').sha256((engine/'ref_gl.dll').read_bytes()).hexdigest(),
        server_sha256=__import__('hashlib').sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest())
    report['diagnostic_skin']=devtest
    if devtest:
        report['third_person_thumb_hidden_from_front']=True
        report['frontal_thumb_pixels']=thumb_front_pixels
    (ROOT/'build/headgear-action'/(prefix+('verification-quick.json' if quick else 'verification.json'))).write_text(json.dumps(report,indent=2))
    images=ROOT/'docs/images';images.mkdir(exist_ok=True)
    sequence=Image.new('RGB',(1920,796),'#141e27');d=ImageDraw.Draw(sequence)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    key=helmets[0]['id']
    for i,(phase,label) in enumerate([('present','1 - Main sur la tranche'),('rise','2 - Montee'),('reach','3 - Vers le front'),
                                    ('above','4 - Au-dessus du cadre'),('move','5 - Manipulation'),('end','6 - Retour sur l arme')]):
        x=(i%3)*640;y=(i//3)*398
        d.text((x+10,y+5),label,font=font,fill='#e5f3ed')
        shot=Image.open(mod/'scrshots'/f'{key}_fp_up_{phase}.png').resize((640,360))
        sequence.paste(shot,(x,y+38))
    sequence.save(images/(prefix+'headgear-hand-sequence.jpg'),quality=93)
    contact_board=Image.new('RGB',(1920,len(helmets)*398),'#141e27');d=ImageDraw.Draw(contact_board)
    for row,h in enumerate(helmets):
        for col,(view,label) in enumerate((('front','Face'),('left','Profil gauche'),('oblique','Trois quarts'))):
            x=col*640;y=row*398
            d.text((x+10,y+5),h['name']+' - '+label,font=font,fill='#e5f3ed')
            shot=Image.open(mod/'scrshots'/f'{h["id"]}_contact_{view}.png').crop((360,140,1000,500))
            contact_board.paste(shot,(x,y+38))
    contact_board.save(images/(prefix+('headgear-hand-contact-quick.jpg' if quick else 'headgear-hand-contact.jpg')),quality=93)
    contact_board.crop((0,0,1920,398)).save(images/(prefix+'headgear-hand-contact-riot.jpg'),quality=93)
    if devtest:
        diagnostic=Image.new('RGB',(1920,442),'#141e27');d=ImageDraw.Draw(diagnostic)
        d.text((12,5),'Orange = PAUME / INT     Bleu = DOS / EXT     Jaune = POUCE     Blanc = TRANCHE',font=font,fill='#e5f3ed')
        for i,(view,label) in enumerate((('front','Face'),('left','Profil gauche'),('oblique','Trois quarts'))):
            x=i*640;y=44
            d.text((x+10,y+5),label,font=font,fill='#e5f3ed')
            diagnostic.paste(Image.open(mod/'scrshots'/f'{key}_contact_{view}.png').crop((360,140,1000,500)),(x,y+38))
        diagnostic.save(images/'devtest-hand-orientation.jpg',quality=93)
        transition=Image.new('RGB',(1280,796),'#141e27');d=ImageDraw.Draw(transition)
        for i,(phase,label) in enumerate((('down','1 - Main posee sur l arme'),('up_rise','2 - Levee sur la tranche'),
                                         ('up_above','3 - Au-dessus de la tete'),('up_end','4 - Retour a la prise'))):
            x=(i%2)*640;y=(i//2)*398
            d.text((x+10,y+5),label,font=font,fill='#e5f3ed')
            transition.paste(Image.open(mod/'scrshots'/f'{key}_fp_{phase}.png').resize((640,360)),(x,y+38))
        transition.save(images/'devtest-hand-weapon-transition.jpg',quality=93)
    if not quick:
        board=Image.new('RGB',(1600,1320),'#141e27');d=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
        for row,h in enumerate(helmets):
            d.text((8,row*260+8),h['name'],font=font,fill='#e5f3ed')
            for col,(view,direction,phase) in enumerate([('fp','up','move'),('tp','up','move'),('tp','up','end'),('tp','down','end')]):
                shot=Image.open(mod/'scrshots'/f'{h["id"]}_{view}_{direction}_{phase}.png').resize((400,225))
                board.paste(shot,(col*400,row*260+34))
        board.save(images/(prefix+'headgear-actions-in-game.jpg'),quality=92)
    print('PASS headgear action native:',len(actions),'actions;',len(poses),'FP/TP poses;',len(captures),'captures',flush=True)
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--quick',action='store_true')
    parser.add_argument('--devtest',action='store_true',help='Use marked diagnostic skin on the actual meshes')
    parser.add_argument('--candidate-dir',type=Path)
    args=parser.parse_args();run(args.quick,args.devtest,args.candidate_dir)

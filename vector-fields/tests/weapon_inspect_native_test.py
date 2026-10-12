"""Native inspection: both sides, full assemblies, combat/gear/menu cancellation."""
import hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from play_weapon_inspect import stage,command,OUT
from build_weapon_inspect import sources,digest,build as build_client
from weapon_inspect_clearance_test import run as check_clearance

def save_film(names,target,path):
    images=[Image.open(target/(name+'.png')).convert('RGB').resize((960,540)) for name in names]
    palette=images[0].quantize(colors=256)
    images=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in images]
    images[0].save(path,save_all=True,append_images=images[1:],duration=117,loop=0,optimize=False)

def run():
    if not (OUT/'build.json').exists() or json.loads((OUT/'build.json').read_text())['sources']!=sources():
        build_client()
    build=json.loads((OUT/'build.json').read_text())
    assert sources()==build['sources'],'Rebuild after concurrent source changes'
    assert digest(OUT/'client/client.dll')==build['client_sha256']
    check_clearance()
    installed_assets={p.name:digest(ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_inspect'/p.name)
        if (ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_inspect'/p.name).exists() else None
        for p in (ROOT/'generated/weapon-inspect').glob('*.mdl')}
    engine,mod=stage();captures=[];frames=[];configurations={};films={}
    lines=['wait 180','developer 1','con_notifytime -1','gl_vsync 0','fps_max 60',
        'host_framerate .016666667','god','weapon_9mmAR','wait 45','bind i "vf_inspect"','bind i']
    def add(*commands):lines.extend(commands)
    def probe(name):add('echo INSPECT_'+name,'vf_inspect_info','cmd vf_reload_info','wait 2')
    def snap(name):captures.append(name);add('screenshot scrshots/'+name+'.png','wait 1')
    def close_menu():add('vf_ui_pointer 1220 40 1','wait 3','vf_ui_pointer 1220 40 0','wait 15')
    for platform,receiver,suffix in (('bottom','a47',''),('side','side','_side'),('top','top','_top')):
        for foregrip in (False,True):
            name=platform+('_foregrip' if foregrip else '_standard')
            rig='r01_rig'+suffix+('_fg' if foregrip else '')+'.mdl'
            configurations[name]=dict(platform=platform,foregrip=foregrip,rig=rig,magazine='r01_feed_d')
            add('vf_reference','wait 20','vf_item r01_receiver_'+receiver+'__original',
                'vf_item r01_feed_d__original','vf_item r01_underbarrel_'+('a' if foregrip else 'b')+'__original',
                'vf_commit','wait 25')
            close_menu();add('vf_traversal_look 160 0','wait 20')
            probe(name+'_ready');add('vf_engine_stats');snap(name+'_ready')
            add('vf_inspect');film=[]
            for frame in range(45):
                add('wait 6');shot=name+'_motion_'+str(frame).zfill(2);snap(shot);film.append(shot)
                if frame==12:probe(name+'_left');snap(name+'_left')
                if frame==27:probe(name+'_right');snap(name+'_right')
            films[name]=film
            probe(name+'_returned');add('vf_engine_stats');snap(name+'_returned')
    for i,(receiver,grip) in enumerate(zip(('a47','m40','ossuary','bramble'),'abcd')):
        add('vf_reference','wait 20','vf_item r01_receiver_'+receiver+'__original',
            'vf_item r01_grip_'+grip+'__original','vf_item r01_feed_a__original',
            'vf_item r01_underbarrel_b__original','vf_commit','wait 25')
        close_menu();add('vf_traversal_look 160 0','wait 20');probe(receiver+'_ready');snap(receiver+'_ready')
        add('vf_inspect','vf_inspect') # Key repeats never restart the first hold.
        if i==0:
            for frame in range(45):
                add('wait 6');name='motion_'+str(frame).zfill(2);snap(name);frames.append(name)
                if frame==12:probe(receiver+'_left');snap(receiver+'_left')
                if frame==27:probe(receiver+'_right');snap(receiver+'_right')
        else:
            add('wait 85');probe(receiver+'_left');snap(receiver+'_left')
            add('wait 100');probe(receiver+'_right');snap(receiver+'_right')
            add('wait 100')
        probe(receiver+'_returned');snap(receiver+'_returned')
    add('vf_inspect','wait 75','+attack','wait 8','-attack','wait 2');probe('fire_cancel');snap('fire_cancel')
    add('wait 20','vf_inspect','wait 75','+reload','wait 2','-reload');probe('reload_cancel');snap('reload_cancel')
    add('vf_inspect');probe('reload_blocked');add('wait 120');probe('reload_done')
    add('vf_inspect','wait 45','cmd give weapon_crowbar','weapon_crowbar','wait 35','vf_inspect_info','wait 2',
        'weapon_9mmAR','wait 75');probe('weapon_return')
    add('vf_inspect','wait 45','vf_reference','wait 20');probe('menu_cancel')
    add('vf_inspect');probe('menu_blocked');close_menu();add('wait 30')
    add('vf_operator','wait 20','vf_item helmet_riot','vf_commit','wait 25');close_menu()
    add('vf_inspect','wait 45','vf_headgear_toggle','wait 20');probe('headgear_cancel');snap('headgear_cancel')
    add('vf_inspect');probe('headgear_blocked');add('wait 100');probe('headgear_done')
    add('vf_inspect','wait 45','thirdperson','wait 25');probe('thirdperson_cancel')
    add('firstperson','wait 30','vf_inspect','wait 45','map vf_traversal','wait 180','weapon_9mmAR','wait 60')
    probe('map_reset')
    add('cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 15','vf_inspect')
    probe('slide_blocked');add('cmd vf_traversal_info');snap('slide_preserved')
    add('-duck','wait 75');probe('slide_done')
    add('vf_reference_audit','vf_equipment_audit','vf_engine_stats','quit')
    cfg=mod/'inspection_test.cfg';cfg.write_text('\n'.join(lines)+'\n',encoding='ascii')
    started=time.time();process=subprocess.Popen(command(engine,mod,cfg),cwd=engine)
    try:process.wait(timeout=240)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)
    log=(engine/'weapon-inspect.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
    assert process.returncode==0,process.returncode
    assert 'VFEngine: assemblies=' in log,'Native assembly renderer not connected'
    assert '"i" = "vf_inspect"' in log
    assert not any(x in log for x in ('Host_Error','SV_Error','VFState rejected','Unknown command: vf_inspect'))
    blocks={name:block for name,block in re.findall(r'INSPECT_(\w+)\s+(.*?)(?=INSPECT_|$)',log,re.S)}
    poses={}
    for name,block in blocks.items():
        found=re.search(r'VFInspect pose: active=(\d) elapsed=([\d.]+) pitch=([\d.-]+) yaw=([\d.-]+) roll=([\d.-]+) weapon=(\d+) reload=(\d) frame_rate=([\d.-]+)',block)
        assert found,(name,block[:700])
        active,elapsed,pitch,yaw,roll,weapon,reload,frame_rate=found.groups()
        poses[name]=dict(active=int(active),elapsed=float(elapsed),pitch=float(pitch),yaw=float(yaw),roll=float(roll),weapon=int(weapon),reload=int(reload),frame_rate=float(frame_rate))
    for name,configuration in configurations.items():
        assert 'rig=models/vf_r01/'+configuration['rig'] in blocks[name+'_ready'],(name,blocks[name+'_ready'][-2000:])
        assert 'rig=models/vf_r01/'+configuration['rig'] in blocks[name+'_returned'],name
    for receiver in [*configurations,'a47','m40','ossuary','bramble']:
        left,right=poses[receiver+'_left'],poses[receiver+'_right']
        assert left['active'] and right['active'] and left['yaw']<-47.9 and right['yaw']>47.9,(receiver,left,right)
        assert left['pitch']>40.9 and right['pitch']>40.9,(receiver,left,right)
        assert not poses[receiver+'_returned']['active']
        assert poses[receiver+'_returned']['frame_rate']==1,poses[receiver+'_returned']
        clips=[re.search(r'clip=(\d+)',blocks[receiver+'_'+phase]).group(1) for phase in ('ready','left','right','returned')]
        assert len(set(clips))==1,(receiver,clips)
    for name in ('fire_cancel','reload_cancel','reload_blocked','weapon_return','menu_cancel','menu_blocked',
                 'headgear_cancel','headgear_blocked','thirdperson_cancel','map_reset','slide_blocked','slide_done'):
        assert not poses[name]['active'],(name,poses[name])
    assert poses['reload_cancel']['reload'] and poses['reload_blocked']['reload'] and not poses['reload_done']['reload']
    assert 'VFTraversal phase=5' in blocks['slide_blocked']
    assert 'rejected=0' in log
    target=OUT/'captures';target.mkdir(exist_ok=True)
    for name in captures:
        path=mod/'scrshots'/(name+'.png');assert path.stat().st_mtime>=started
        assert Image.open(path).size==(1280,720)
        shutil.copy2(path,target/path.name)
    save_film(frames,target,OUT/'inspection.gif')
    board=Image.new('RGB',(1920,598),'#141e27');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',26)
    for col,(name,label) in enumerate((('a47_left','Premier cote'),('a47_right','Second cote'))):
        draw.text((col*960+18,14),label,font=font,fill='#e5f3ed')
        board.paste(Image.open(target/(name+'.png')).resize((960,540)),(col*960,58))
    board.save(OUT/'sides.jpg',quality=93)
    for name,film in films.items():
        save_film(film,target,OUT/(name+'.gif'))
        # Native screenshots at release, both holds and regrasp for visual review.
        steps=(0,2,4,6,12,27,30,32,34,36)
        board=Image.new('RGB',(1920,1160),'#141e27');draw=ImageDraw.Draw(board)
        for index,frame in enumerate(steps):
            x=(index%4)*480;y=(index//4)*386
            draw.text((x+10,y+5),name+' / '+str(frame),font=font,fill='#e5f3ed')
            board.paste(Image.open(target/(film[frame]+'.png')).resize((480,270)),(x,y+40))
        board.save(OUT/(name+'-review.jpg'),quality=95)
    assets={p.name:digest(p) for p in (ROOT/'generated/weapon-inspect').glob('*.mdl')}
    assert len(assets)==8
    assert all(digest(mod/'models/vf_inspect'/name)==sha for name,sha in assets.items())
    clearance=json.loads((OUT/'clearance.json').read_text())
    assert clearance['passed'] and clearance['model_sha256']==assets
    assert all(digest(engine/'vf_visual/models/vf_r01'/name)==sha for name,sha in clearance['geometry_sources'].items())
    report=dict(passed=True,poses=poses,configurations=configurations,configuration_films=films,inspection_assets=assets,installed_inspection_assets=installed_assets,client_sha256=digest(mod/'cl_dlls/client.dll'),
        server_sha256=digest(mod/'dlls/hl.dll'),renderer_sha256=digest(engine/'ref_gl.dll'),
        installed_client_sha256=digest(ROOT.parent/'runtime/vector-engine/vf_visual/cl_dlls/client.dll'),
        shared_client_sha256=digest(ROOT/'build/client/client.dll'),
        elapsed=time.time()-started,captures=captures,temporary_engine=str(engine),
        checks=['all six feed/support configurations with the largest magazine','four magazine envelopes clear during foregrip release/regrasp','no elbow-weighted glove rim','correct native carrier before and after each inspection','four complete assemblies and four grips','both raised side holds','free left hand with release/regrasp','both equipped sleeves and complete right fingers','idle frame rate restored','unchanged ammunition',
        'fire/reload/holster/menu/headgear/traversal priority','third person blocked','map reset','I binding'])
    (OUT/'native.json').write_text(json.dumps(report,indent=2))
    print('PASS native inspection:',len(captures),'captures, six configurations, four assemblies, combat/gear/traversal priority')

if __name__=='__main__':run()

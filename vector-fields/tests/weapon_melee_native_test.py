"""Actual native client/server: six mounts, standing/crouched body and one-hit combat."""
import json,re,shutil,subprocess,sys,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from play_weapon_melee import stage,command,OUT,BASE
from build_weapon_melee import sources,digest,build as build_candidate
ASSET_MODELS=ROOT/'generated/weapon-melee'

def deployed():
    paths=[BASE/'vf_visual/cl_dlls/client.dll',BASE/'vf_visual/dlls/hl.dll',ROOT/'build/client/client.dll',ROOT/'build/server/hl.dll']
    return {str(p):digest(p) if p.exists() else None for p in paths}

def film(names,target,path):
    frames=[Image.open(target/(n+'.png')).convert('RGB').resize((960,540)) for n in names]
    palette=frames[0].quantize(colors=256)
    frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=False)

def run():
    if not (OUT/'build.json').exists() or json.loads((OUT/'build.json').read_text())['sources']!=sources():build_candidate()
    build=json.loads((OUT/'build.json').read_text());assert sources()==build['sources']
    assert digest(OUT/'client/client.dll')==build['client_sha256'] and digest(OUT/'server/hl.dll')==build['server_sha256']
    before=deployed();engine,mod=stage();shots=[];films={};configurations={}
    lines=['wait 180','developer 1','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667',
           'god','weapon_9mmAR','wait 60','bind v "vf_melee"','bind v']
    def add(*commands):lines.extend(commands)
    def probe(name):add('echo MELEE_'+name,'vf_melee_info','cmd vf_melee_info','cmd vf_reload_info','vf_engine_stats','wait 2')
    def snap(name):shots.append(name);add('screenshot scrshots/'+name+'.png','wait 1')
    def close_menu():add('vf_ui_pointer 1220 40 1','wait 3','vf_ui_pointer 1220 40 0','wait 15')
    def motion(name):
        probe(name+'_ready');add('vf_melee','vf_melee');names=[]
        for frame in range(30):
            add('wait 2');shot=name+'_'+str(frame).zfill(2);snap(shot);names.append(shot)
            if frame==7:probe(name+'_impact')
        films[name]=names;probe(name+'_returned')
    for platform,receiver,suffix in (('bottom','a47',''),('side','side','_side'),('top','top','_top')):
        for grip in (False,True):
            name=platform+('_foregrip' if grip else '_standard')
            configurations[name]=dict(rig='r01_rig'+suffix+('_fg' if grip else '')+'.mdl')
            add('vf_reference','wait 20','vf_item r01_receiver_'+receiver+'__original','vf_item r01_feed_d__original',
                'vf_item r01_underbarrel_'+('a' if grip else 'b')+'__original','vf_commit','wait 25')
            close_menu();add('cmd vf_melee_place 0 -500 36 160 0','wait 25');motion(name)
    add('thirdperson','cam_idealyaw 140','cam_idealpitch 8','cam_idealdist 115','wait 60');motion('third_standing')
    add('+duck','wait 30');motion('third_crouching');add('-duck','wait 30','firstperson','wait 20')
    # Reach the torso of a reset range target; damage must occur at the keyed impact, once.
    add('cmd vf_range_reset 0','cmd vf_melee_place -300 -198 36 90 15','wait 20');probe('contact_ready')
    add('cmd vf_range_info','vf_melee','wait 12');probe('contact_early');add('cmd vf_range_info')
    add('wait 18');probe('contact_impact');snap('contact_impact');add('cmd vf_range_info')
    add('vf_melee','vf_melee','wait 45');probe('contact_done');add('cmd vf_range_info')
    # Cancel before the impact and restore the ordinary animation rate/model.
    add('cmd vf_range_reset 0','vf_melee','wait 10','cmd vf_melee_cancel','wait 70');probe('cancelled');add('cmd vf_range_info')
    # Outside range, then switch to a different weapon during the preparation.
    add('cmd vf_melee_place -300 -240 36 90 10','wait 20','vf_melee','wait 75');probe('out_of_range');add('cmd vf_range_info')
    add('vf_melee','wait 8','cmd give weapon_crowbar','weapon_crowbar','wait 75');probe('holstered')
    add('vf_melee','wait 5');probe('non_r1');add('weapon_9mmAR','wait 75')
    # Normal firearm resumes and reload owns its own sequence.
    add('+attack','wait 8','-attack','wait 15');probe('fire_resumed')
    add('+reload','wait 2','-reload','vf_melee','wait 12');probe('reload_blocked')
    add('wait 130');probe('reload_done')
    add('vf_reference','wait 20','vf_melee','wait 8');probe('menu_blocked');close_menu()
    add('vf_inspect','wait 30','vf_melee','wait 20');probe('inspect_replaced');add('vf_inspect_info','wait 75')
    add('vf_operator','wait 20','vf_item helmet_riot','vf_commit','wait 25');close_menu()
    add('vf_headgear_toggle','wait 12','vf_melee','wait 5');probe('headgear_blocked');add('vf_headgear_info','wait 100')
    add('vf_melee','wait 15','save vf_melee_cancel','wait 8','load vf_melee_cancel','wait 180');probe('save_restored')
    add('vf_melee','wait 10','cmd kill','wait 20');probe('death_cancelled');add('wait 60')
    # New map clears network action state; traversal keeps precedence.
    add('vf_melee','wait 8','map vf_traversal','wait 180','weapon_9mmAR','wait 60');probe('map_reset')
    add('cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 15','vf_melee','wait 2')
    probe('slide_blocked');add('cmd vf_traversal_info');snap('slide_preserved');add('-duck','wait 90','vf_equipment_audit','vf_reference_audit','vf_engine_stats','quit')
    cfg=mod/'melee_test.cfg';cfg.write_text('\n'.join(lines)+'\n',encoding='ascii')
    start=time.time();process=subprocess.Popen(command(engine,mod,cfg),cwd=engine)
    try:process.wait(timeout=230)
    finally:
        if process.poll() is None:process.terminate();process.wait(10)
    log=(engine/'weapon-melee.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
    assert process.returncode==0,process.returncode
    assert not any(x in log for x in ('Host_Error','SV_Error','VFState rejected','Unknown command: vf_melee'))
    assert 'VFEngine: assemblies=' in log and 'rejected=0' in log and '"v" = "vf_melee"' in log
    blocks=dict(re.findall(r'MELEE_(\w+)\s+(.*?)(?=MELEE_|$)',log,re.S));states={}
    for name,block in blocks.items():
        match=re.search(r'VFMelee server: active=(\d) age=([\d.]+) impact=(\d) hits=(\d+) entity=(\d+) damage=([\d.]+) clip=(-?\d+) model=(\S+)',block)
        assert match,(name,block[:1500])
        active,age,impact,hits,entity,damage,clip,model=match.groups()
        states[name]=dict(active=int(active),age=float(age),impact=int(impact),hits=int(hits),entity=int(entity),damage=float(damage),clip=int(clip),model=model)
    for name,config in configurations.items():
        assert states[name+'_impact']['active'] and not states[name+'_returned']['active'],(name,states)
        assert 'rendered_sequence=9 rig=models/vf_melee/'+config['rig'] in blocks[name+'_impact'],(name,blocks[name+'_impact'][-1500:])
        assert 'rig=models/vf_r01/'+config['rig'] in blocks[name+'_returned']
        assert states[name+'_ready']['clip']==states[name+'_returned']['clip']
    for name in ('third_standing','third_crouching'):
        assert states[name+'_impact']['active'] and '/vf_melee/' in states[name+'_impact']['model']
        assert not states[name+'_returned']['active'] and '/vf_r01/' in states[name+'_returned']['model']
    assert states['contact_early']['active'] and not states['contact_early']['impact']
    assert states['contact_impact']['active'] and states['contact_impact']['impact'] and states['contact_impact']['damage']>0
    assert states['contact_done']['hits']==states['contact_ready']['hits']+1
    assert states['contact_done']['clip']==states['contact_ready']['clip']
    assert states['cancelled']['hits']==states['contact_done']['hits'] and not states['cancelled']['impact']
    assert states['out_of_range']['damage']==0 and states['out_of_range']['hits']==states['cancelled']['hits']
    for name in ('cancelled','holstered','non_r1','reload_blocked','reload_done','menu_blocked','headgear_blocked','save_restored','death_cancelled','map_reset','slide_blocked'):
        assert not states[name]['active'],(name,states[name])
    assert states['fire_resumed']['clip']<states['out_of_range']['clip']
    assert states['inspect_replaced']['active'] and 'VFInspect pose: active=0' in blocks['inspect_replaced']
    assert 'VFTraversal phase=5' in blocks['slide_blocked']
    target=OUT/'captures';target.mkdir(exist_ok=True)
    for name in shots:
        source=mod/'scrshots'/(name+'.png');assert source.stat().st_mtime>=start
        assert Image.open(source).size==(1280,720);shutil.copy2(source,target/source.name)
    for name,names in films.items():film(names,target,OUT/(name+'.gif'))
    board=Image.new('RGB',(1920,1140),'#17212b');draw=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    for i,(name,label) in enumerate((('bottom_standard','Premiere personne'),('third_standing','Troisieme personne'))):
        for j,frame in enumerate((2,7,11,18)):
            x=j*480;y=i*570;draw.text((x+12,y+10),label+' / '+str(frame),font=font,fill='white')
            board.paste(Image.open(target/(films[name][frame]+'.png')).resize((480,270)),(x,y+45))
    board.save(OUT/'native-review.jpg',quality=95)
    assert sources()==build['sources'],'Concurrent source changes require a fresh candidate test'
    assets={p.name:digest(p) for p in ASSET_MODELS.glob('*.mdl')}
    assert assets==build['assets'] and all(digest(mod/'models/vf_melee'/n)==sha for n,sha in assets.items())
    report=dict(passed=True,states=states,configurations=configurations,assets=assets,installed_before=before,
        engine_binaries={n:digest(engine/n) for n in ('ref_gl.dll','xash.dll','xash3d.exe','xash.exe','SDL2.dll')},
        renderer_sha256=digest(engine/'ref_gl.dll'),client_sha256=digest(mod/'cl_dlls/client.dll'),server_sha256=digest(mod/'dlls/hl.dll'),
        elapsed=time.time()-start,captures=shots,checks=['six full feed/support configurations','standing/crouched third person',
        'single server-authoritative contact at keyed impact','no ammo consumed','spam blocked','early cancellation','range miss',
        'fire resumes','reload/menu/weapon/headgear/traversal priority','inspection replaced','save load cancels action','death sequence preserved','map reset','native assembly renderer'])
    (OUT/'native.json').write_text(json.dumps(report,indent=2));print('PASS native melee:',len(shots),'captures, six mounts, FP/TP and one-hit combat',flush=True)
if __name__=='__main__':run()

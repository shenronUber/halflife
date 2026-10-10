"""Sculpted receiver contracts and native integration with existing R-01 parts."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_reference_weapon import ROOT,OUT,Mesh,part as original_part
from build_reference_chassis import CHASSIS,part
from studio_assets import Studio
from reference_extensions_test import mesh_digest


def side_ray_hits(mesh,y,z):
    # Count intersections of a side-view ray through the actual triangle interiors.
    hits=0
    for _,tri in mesh:
        p=np.array([v['p']for v in tri]);a=(p[1:,1:]-p[0,1:]).T
        if abs(np.linalg.det(a))<1e-9:continue
        u,v=np.linalg.solve(a,np.array([y,z])-p[0,1:])
        if u>1e-6 and v>1e-6 and u+v<1-1e-6:hits+=1
    return hits


def assets():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    finishes=len(manifest['styles'])
    pool=json.loads((ROOT/'data/lootpool.json').read_text())
    old=Studio(OUT/'r01_receiver_a.mdl');reports={}
    rows=[r.split('|')for r in (ROOT/'data/equipment.txt').read_text().splitlines()if r.startswith('receiver|r01_') and len(r.split('|'))==14]
    assert len(rows)==9 and len(manifest['pieces'])==61 and len(pool['entries'])==948
    for key,spec in CHASSIS.items():
        ident='r01_receiver_'+key;mesh=part(key,Mesh);model=Studio(OUT/(ident+'.mdl'))
        record=next(r for r in manifest['pieces']if r['id']==ident)
        assert len(mesh)==len(model.mesh())==record['triangles']
        assert hashlib.sha256(model.data).hexdigest()==record['sha256']
        assert len(model.names)==1 and np.allclose(model.bind[0],old.bind[0])
        assert model.numskinfamilies==finishes and len(model.textures)<=100
        assert len({tuple(v['p'])for _,tri in model.mesh()for v in tri})<=2048
        for mat,tri in mesh:
            assert mat in ('r01_t00.bmp','r01_t02.bmp','r01_t03.bmp','r01_t05.bmp','r01_t07.bmp')
            uv=np.array([v['uv']for v in tri]);p=np.array([v['p']for v in tri])
            assert np.isfinite(p).all()and np.isfinite(uv).all()and uv.min()>=-1e-9 and uv.max()<=1+1e-9
            scales=np.linalg.svd((p[1:]-p[0]).T@np.linalg.inv((uv[1:]-uv[0]).T),compute_uv=False)
            assert scales[0]/scales[1]<1.00001,(key,mat,scales)
        if key=='gyre':
            identity=[v['p']for mat,tri in mesh if mat=='r01_t03.bmp'for v in tri]
            assert identity and all(abs(p[2]-1.695)<1e-6 and -2.501<=p[1]<=-.299 for p in identity),'Identity decoration must stay on its single plaque'
        digest=mesh_digest(model.mesh())
        for skin in range(finishes):assert mesh_digest(model.mesh(skin=skin))==digest
        entry=next(r for r in rows if r[1]==ident)
        assert entry[4]==spec['family'] and entry[6:12]==rows[0][6:12]
        assert len([r for r in pool['entries']if r.get('model')=='models/vf_r01/'+ident+'.mdl'])==finishes
        reports[key]=dict(triangles=len(mesh),vertices=len({tuple(v['p'])for _,tri in model.mesh()for v in tri}),finishes=finishes,sha256=record['sha256'])
    # These points lay inside the original rectangular receiver. Arche has real holes.
    arch=part('arch',Mesh)
    for y,z in [(9.6,.1),(10.2,.2),(9.8,.5)]:
        assert side_ray_hits(arch,y,z)==0,(y,z,'open window filled')
        assert side_ray_hits(original_part('receiver',0),y,z)>0
    assert mesh_digest(part('arch',Mesh))!=mesh_digest(part('gyre',Mesh))
    report=dict(receivers=reports,checks=['both shapes compile below the 2048-vertex model limit','real front window in Arche; no rectangular internal body','finite isotropic tiled UVs and all installed finishes','unchanged equipment costs and Bone76 frame','both IDs registered in all all installed cosmetic collections'])
    (ROOT/'build/reference-chassis-assets.json').write_text(json.dumps(report,indent=2))
    print('PASS sculpted chassis assets:',reports,flush=True)
    return report


def native():
    from library_engine_test import run_cfg,click,MOD
    captures=[]
    def snap(name):
        name='chassis_'+name;captures.append(name)
        return f'wait 8\nscreenshot scrshots/{name}.png\nwait 3\n'
    script='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_dev\nwait 25\nvf_reference 2\nwait 25\n'
    for key,x in [('arch',1123),('gyre',1213)]:
        # Actual player shortcut, then isolated geometry and an angled assembly.
        script+='vf_reference 2\nwait 16\nvf_select_slot 9\n'+click(x,171)+'vf_reference_style 0\nvf_animation 0\nvf_animation_time 0\n'+snap(key+'_assembly')
        script+='vf_reference_isolate\n'+snap(key+'_isolated')+click(749,171)+snap(key+'_isolated_angle')+'vf_reference_isolate\n'+snap(key+'_angle')
        script+='vf_reference_style 6\n'+snap(key+'_porcelain')+click(701,171)
        script+='vf_reference_hands 1\nvf_animation 3\nvf_animation_time 1.6\n'+snap(key+'_grip')+'vf_reference_hands 0\nvf_animation 0\nvf_animation_time 0\n'
        # Four complete module families, including all four magazines, on each chassis.
        for variant,letter in enumerate('abcd'):
            script+=f'vf_reference {variant}\nwait 16\nvf_select_slot 9\n'+click(x,171)+'vf_reference_style 0\nvf_commit\nwait 25\n'+snap(key+'_set_'+letter)
            script+=click(1220,40)+'wait 20\n'+snap(key+'_hand_'+letter)
            script+='+attack\nwait 15\n-attack\nwait 25\n+reload\nwait 20\n'+snap(key+'_reload_'+letter+'_early')+'wait 48\n'+snap(key+'_reload_'+letter+'_late')+'wait 130\n-reload\nvf_reference\nwait 20\n'
        # Verify each new stable ID and independently coloured optic survive save/load.
        script+='vf_reference_style 7\nvf_reference_style 4 16\nvf_commit\nwait 25\n'+click(1220,40)+f'save vf_chassis_{key}\nwait 30\nload vf_chassis_{key}\nwait 180\ndeveloper 1\nvf_reference\nwait 25\n'+snap(key+'_restored')
    script+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
    assert len(script.encode('ascii'))<24000
    log=run_cfg('vf_chassis_test',script,captures=captures,timeout=180)
    for key,label in [('arch','Arche'),('gyre','Gyre')]:
        assert 'VFUI click: '+label in log
        for letter in 'abcd':assert f'VFR01 applied: receiver=r01_receiver_{key} power=r01_power_{letter}'in log
        after=log.split(f'Loading game from save/vf_chassis_{key}.sav')[1]
        assert f'VFR01 applied: receiver=r01_receiver_{key} power=r01_power_d'in after
        assert 'VFR01 state: player=1 first=7 optic=4 feed=7'in after
    assert 'VFR01 audit: checked=1753 failed=0 parts=12 combinations=191102976'in log
    assert 'VFEquipment audit: objects=1113 passed=1113 failed=0'in log
    assert 'VFState rejected'not in log and 'rejected=0'in log
    # Review sheets are crops of native screenshots, not separate concept renders.
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    kinds=[('isolated_angle','Chassis seul'),('assembly','Montage Nomade'),('angle','Vue de trois quarts'),('hand_c','En main')]
    board=Image.new('RGB',(1440,len(kinds)*460+50),'#101922');draw=ImageDraw.Draw(board)
    for col,(key,label)in enumerate([('arch','Arche'),('gyre','Gyre')]):
        draw.text((col*720+20,12),label,font=font,fill='#eed597')
        for row,(kind,title)in enumerate(kinds):
            im=Image.open(MOD/'scrshots'/f'chassis_{key}_{kind}.png').convert('RGB')
            im=im.crop((490,305,1210,726)) if not kind.startswith('hand') else im.resize((720,405))
            y=50+row*460;draw.text((col*720+20,y),title,font=font,fill='white');board.paste(im,(col*720,y+32))
    board.save(ROOT/'build/r01-sculpted-chassis.jpg',quality=95)
    report=dict(captures=captures,assemblies=1753,equipment_objects=1113,reload_combinations=8,checks=['both shortcuts selected through native pointer input','four existing complete module sets on each chassis','first-person shooting and two reload phases for all eight magazine/chassis pairs','two stable chassis IDs and mixed finishes restored after save/load'],limits=['pairwise audit does not prove every combination free of visual clipping','existing MP5 gameplay and stock third-person weapon'])
    (ROOT/'build/reference-chassis-native.json').write_text(json.dumps(report,indent=2))
    print('PASS sculpted chassis native:',len(captures),'captures, eight reload combinations, two saves and 1753 assemblies',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native','all'],default='assets');args=p.parse_args()
    if args.mode in ('assets','all'):assets()
    if args.mode in ('native','all'):native()

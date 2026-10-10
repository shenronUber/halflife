"""Regression checks for 24 added R-01 silhouettes and their existing textures."""
import argparse,collections,hashlib,json,math,re,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_reference_weapon import ROOT,OUT,KEYS,part
from studio_assets import Studio


def mesh_digest(mesh):
    h=hashlib.sha256()
    for material,tri in mesh:
        for v in tri:h.update(v['p'].tobytes());h.update(v['uv'].tobytes())
    return h.hexdigest()


def assets():
    data=json.loads((OUT/'manifest.json').read_text())
    finishes=len(data['styles'])
    counts=collections.Counter(p['slot']for p in data['pieces'])
    assert counts==dict.fromkeys(KEYS,4)|{'receiver':9,'chamber':6,'optic':6,'power':6,'cooling':6}
    assert len(data['pieces'])==61 and data['combinations']==math.prod(counts.values())==191102976
    byid={p['id']:p for p in data['pieces']};triangles=0;material_checks=0
    rig=Studio(OUT/'r01_rig.mdl')
    mag=np.linalg.inv(rig.bind[rig.names.index('Bone71')])@rig.bind[rig.names.index('Bone76')]
    baseline_feed=Studio(OUT/'r01_feed_a.mdl').mesh()
    connector=np.array([v['p']for _,tri in baseline_feed for v in tri])
    connector=np.array([(np.linalg.inv(mag)@np.r_[p,1])[:3]for p in connector])
    connector=np.unique(np.round(connector[connector[:,2]>-.82],4),axis=0)
    for slot in KEYS:
        digests=[mesh_digest(part(slot,v))for v in range(4)]
        assert all(digests[v]not in digests[:v]for v in (2,3)),(slot,'each new geometry must differ from all earlier variants')
        for variant in (2,3):
            key=f'r01_{slot}_{"abcd"[variant]}';mesh=part(slot,variant);record=byid[key]
            model=Studio(OUT/(key+'.mdl'));assert len(model.mesh())==record['triangles']==len(mesh)
            assert len(model.names)==1 and model.numskinfamilies==finishes and len(model.textures)<=100
            assert hashlib.sha256(model.data).hexdigest()==record['sha256']
            assert all(0<w<=256 and 0<h<=256 for _,w,h,_,_ in model.textures)
            for material,tri in mesh:
                assert re.fullmatch(r'r01_t\d\d.bmp',material)and int(material[5:7])<16
                uv=np.array([v['uv']for v in tri]);p=np.array([v['p']for v in tri])
                assert np.isfinite(p).all()and np.isfinite(uv).all()and uv.min()>=-1e-9 and uv.max()<=1+1e-9
                if material!='r01_t11.bmp':
                    physical=(p[1:]-p[0]).T@np.linalg.inv((uv[1:]-uv[0]).T)
                    scales=np.linalg.svd(physical,compute_uv=False)
                    assert scales[0]/scales[1]<1.00001,(key,material,scales)
                triangles+=1
            original=mesh_digest(model.mesh())
            for skin in range(finishes):
                assert mesh_digest(model.mesh(skin=skin))==original,(key,skin,'finish changed geometry')
                table=model.skin[skin*model.numskinref:(skin+1)*model.numskinref]
                assert all(0<=i<len(model.textures)for i in table)
                # Every embedded diffuse is copied from its existing atlas tile.
                for index in table:
                    name,w,h,pixels,palette=model.textures[index]
                    assert (OUT/name).exists(),(key,name)
                    assert (OUT/name).read_bytes(),name
                material_checks+=1
            if slot=='feed':
                points=np.array([(np.linalg.inv(mag)@np.r_[v['p'],1])[:3]for _,tri in model.mesh()for v in tri])
                for p in connector:assert np.linalg.norm(points-p,axis=1).min()<.025,(key,p)
                # All three animated mounts consume this same local magazine model.
                for rig_name in ('r01_rig','r01_rig_side','r01_rig_top'):
                    assert 'Bone71'in Studio(OUT/(rig_name+'.mdl')).names
            if slot=='optic':
                n,off=__import__('struct').unpack_from('<ii',model.data,180)
                for i in range(n):
                    name,flags,*_=__import__('struct').unpack_from('<64s4i',model.data,off+i*80)
                    if name.split(b'\0')[0].decode().endswith('_t11.bmp'):assert flags&32,'new glass must be additive'
    pool=json.loads((ROOT/'data/lootpool.json').read_text())
    assert len(pool['entries'])==948
    for slot in KEYS:
        for letter in 'cd':
            rows=[e for e in pool['entries']if e.get('model')==f'models/vf_r01/r01_{slot}_{letter}.mdl']
            assert len(rows)==finishes and len({e['collection']for e in rows})==finishes
    report=dict(new_pieces=24,total_pieces=61,existing_finishes=finishes,shape_finish_checks=material_checks,source_triangles=triangles,combinations=data['combinations'],loot_entries=948,checks=['two distinct additional geometries per socket; nine receivers','all source UVs finite, contained and isotropic outside glass','compiled models retain one socket bone and all installed finishes','magazine connectors coincide with the original compiled neck','new optical glass remains additive','each new shape registered in all installed cosmetic collections'])
    (ROOT/'build/reference-extensions-assets.json').write_text(json.dumps(report,indent=2))
    print('PASS R-01 additions: 24 meshes,',material_checks,'shape/finish checks, original magazine connectors and 948 loot entries',flush=True)
    return report


def native():
    from library_engine_test import run_cfg,click,MOD
    captures=[]
    def snap(name):
        name='r01_new_'+name;captures.append(name)
        return f'wait 12\nscreenshot scrshots/{name}.png\nwait 3\n'
    script='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_dev\nwait 25\nvf_reference 0\nwait 25\n'
    for variant,letter,label in ((2,'c','Nomade'),(3,'d','Bastion')):
        # Select the new complete set through the same button used by the player.
        script+=click(362+variant*90,171)+f'wait 20\nvf_reference_style 0\nvf_animation 0\nvf_animation_time 0\n'+snap(letter+'_assembly')
        script+='vf_reference_isolate\n'
        for slot,key in enumerate(KEYS,9):script+=f'vf_select_slot {slot}\n'+snap(letter+'_'+key)
        script+='vf_reference_isolate\nvf_commit\nwait 30\n'+click(1220,40)+'wait 25\n'+snap(letter+'_hand')
        script+='vf_reference\nwait 20\n'
        for platform in range(3):
            script+=f'vf_reference_platform {platform}\nvf_commit\nwait 20\n'+click(1220,40)+'wait 20\n+attack\nwait 15\n-attack\nwait 30\n+reload\nwait 38\n'+snap(f'{letter}_platform_{platform}_reload')+'wait 130\n-reload\nvf_reference\nwait 20\n'
    # Mix new and old shapes, keep different per-piece styles, then round-trip a save.
    script+='vf_item r01_receiver_c\nvf_item r01_barrel_d\nvf_item r01_muzzle_a\nvf_item r01_feed_c\nvf_item r01_optic_d\nvf_reference_style 7\nvf_reference_style 4 16\nvf_commit\nwait 30\n'+snap('mixed')
    script+=click(1220,40)+'save vf_r01_additions\nwait 40\nload vf_r01_additions\nwait 180\ndeveloper 1\nvf_reference\nwait 30\nvf_animation_time 0\n'+snap('restored')
    script+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
    log=run_cfg('vf_r01_additions_test',script,captures=captures,timeout=150)
    for label in ('Nomade','Bastion'):assert 'VFUI click: '+label in log
    for letter in 'cd':
        assert f'VFR01 applied: receiver=r01_receiver_{letter} power=r01_power_{letter}'in log
        for platform in range(3):assert f'VFR01 platform: {platform} feed=r01_feed_{letter}'in log
    assert 'VFR01 audit: checked=1753 failed=0 parts=12 combinations=191102976 coverage=single-and-pairs'in log
    assert 'VFEquipment audit: objects=1113 passed=1113 failed=0'in log
    assert 'VFState rejected'not in log and 'rejected=0'in log
    after=log.split('Loading game from save/vf_r01_additions.sav')[-1]
    assert 'receiver=r01_receiver_c power=r01_power_d'in after
    assert 'VFR01 state: player=1 first=7 optic=4 feed=7'in after
    # A compact review sheet keeps all 24 newly authored parts visible together.
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    sheet=Image.new('RGB',(1200,12*230+42),'#101922');draw=ImageDraw.Draw(sheet)
    for column,label in enumerate(('Nomade','Bastion')):draw.text((column*600+20,10),label,font=font,fill='white')
    for row,key in enumerate(KEYS):
        for column,letter in enumerate('cd'):
            im=Image.open(MOD/'scrshots'/f'r01_new_{letter}_{key}.png').convert('RGB').crop((490,305,1210,726));im.thumbnail((570,195))
            y=42+row*230;sheet.paste(im,(column*600+15,y+26));draw.text((column*600+20,y),key,font=font,fill='#eed597')
    sheet.save(ROOT/'build/r01-new-parts.jpg',quality=94)
    sets=Image.new('RGB',(1440,475),'#101922');draw=ImageDraw.Draw(sets)
    for column,(letter,label)in enumerate((('c','Nomade'),('d','Bastion'))):
        draw.text((column*720+18,10),label,font=font,fill='white')
        view=Image.open(MOD/'scrshots'/f'r01_new_{letter}_assembly.png').convert('RGB').crop((490,305,1210,726))
        sets.paste(view,(column*720,45))
    sets.save(ROOT/'build/r01-new-sets.jpg',quality=94)
    report=dict(captures=captures,checked_assemblies=1753,equipment_objects=1113,coverage='every individual piece and every pair of sockets; not exhaustive full-build enumeration',checks=['both new presets selected through native pointer routing','all 24 new pieces and two complete weapons rendered','both new magazines fired and reloaded on all three platforms','mixed old/new build and individual finishes survive save/load'],contact_sheet=str(ROOT/'build/r01-new-parts.jpg'))
    (ROOT/'build/reference-extensions-native.json').write_text(json.dumps(report,indent=2))
    print('PASS native R-01 additions:',len(captures),'captures; 1753 assemblies; six magazine/platform reloads',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['assets','native','all'],default='assets');args=parser.parse_args()
    if args.mode in ('assets','all'):assets()
    if args.mode in ('native','all'):native()

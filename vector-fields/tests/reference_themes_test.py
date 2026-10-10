"""Shared-material themed modules: mesh contracts and native integration."""
import argparse,hashlib,json,math,re,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_reference_weapon import ROOT,OUT,Mesh,KEYS,part as core_part
from build_reference_themes import PARTS,part
from studio_assets import Studio
from reference_extensions_test import mesh_digest


def assets():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    pool=json.loads((ROOT/'data/lootpool.json').read_text())
    records={r['id']:r for r in manifest['pieces']};checks=0;report={}
    assert len(records)==61 and len(pool['entries'])==948
    assert manifest['animated_sockets']['chamber']=='R01_Bolt'
    rows=[r.split('|')for r in (ROOT/'data/equipment.txt').read_text().splitlines()if r and not r.startswith(('#','limits'))]
    assert len(rows)==1113 and len(rows)<2048
    for slot,specs in PARTS.items():
        digests=[mesh_digest(core_part(slot,i))for i in range(4)]
        for spec in specs:
            key=f"r01_{slot}_{spec['key']}";mesh=part(slot,spec['key'],Mesh);model=Studio(OUT/(key+'.mdl'))
            digest=mesh_digest(mesh);assert digest not in digests;digests.append(digest)
            assert len(model.mesh())==len(mesh)==records[key]['triangles']
            assert len(model.names)==1 and np.allclose(model.bind[0],np.eye(4))
            assert model.numskinfamilies==14 and len(model.textures)<=100
            vertices=len({tuple(v['p'])for _,tri in model.mesh()for v in tri});assert vertices<2048
            for material,tri in mesh:
                uv=np.array([v['uv']for v in tri]);points=np.array([v['p']for v in tri])
                assert np.isfinite(points).all()and np.isfinite(uv).all()and uv.min()>=-1e-9 and uv.max()<=1+1e-9
                if material!='r01_t11.bmp':
                    scales=np.linalg.svd((points[1:]-points[0]).T@np.linalg.inv((uv[1:]-uv[0]).T),compute_uv=False)
                    assert scales[0]/scales[1]<1.00001,(key,material,scales)
            original=mesh_digest(model.mesh())
            for skin in range(14):
                assert mesh_digest(model.mesh(skin=skin))==original
                table=model.skin[skin*model.numskinref:(skin+1)*model.numskinref]
                assert all(0<=i<len(model.textures)for i in table);checks+=1
            if slot=='optic':
                count,offset=struct.unpack_from('<ii',model.data,180)
                glass=0
                for i in range(count):
                    name,flags,*_=struct.unpack_from('<64s4i',model.data,offset+i*80)
                    if name.split(b'\0')[0].decode().endswith('_t11.bmp'):assert flags&32;glass+=1
                assert glass==14
            row=next(r for r in rows if r[1]==key);assert row[4]==spec['family']and row[6:12]==['4','4','4','4','0','0']
            assert len([e for e in pool['entries']if e.get('model')=='models/vf_r01/'+key+'.mdl'])==14
            report[key]=dict(triangles=len(mesh),vertices=vertices,skin_families=14)
    # Both chamber shapes consume the existing translating socket in every rig.
    for rig in ('r01_rig','r01_rig_side','r01_rig_top'):
        assert 'R01_Bolt'in Studio(OUT/(rig+'.mdl')).names
    for prefix in ('','side_','top_'):
        text=(OUT/(prefix+'shoot1.smd')).read_text(encoding='ascii')
        bone=int(re.search(r'(\d+) "R01_Bolt"',text)[1])
        values=[float(m[1])for m in re.finditer(r'^'+str(bone)+r' [^ ]+ ([\d.\-]+) ',text,re.M)]
        assert max(values)-min(values)>.5
    (ROOT/'build/reference-themes-assets.json').write_text(json.dumps(dict(pieces=report,shape_finish_checks=checks,total_objects=1113),indent=2))
    print('PASS themed modules: eight distinct meshes,',checks,'shape/finish checks, three moving bolt sockets',flush=True)


def native():
    from library_engine_test import run_cfg,click,MOD
    captures=[]
    def snap(name):
        name='themes_'+name;captures.append(name);return f'wait 10\nscreenshot scrshots/{name}.png\nwait 3\n'
    script='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_dev\nwait 25\nvf_reference\nwait 30\n'
    for theme,x,style,receiver in [('inventor',654,12,'arch'),('diesel',768,13,'gyre')]:
        script+=click(x,502)+'wait 15\nvf_animation 0\nvf_animation_time 0\n'+snap(theme+'_assembly')
        script+=click(749,171)+snap(theme+'_angle')+click(701,171)
        script+='vf_commit\nwait 25\n'+click(1220,40)+snap(theme+'_hand')
        # Developer isolation inspects both sides of all eight new meshes.
        script+='vf_dev\nwait 15\nvf_reference\nwait 25\nvf_reference_isolate\n'
        for slot in PARTS:
            script+=f'vf_select_slot {KEYS.index(slot)+9}\nvf_animation 0\nvf_animation_time 0\n'+snap(theme+'_'+slot)
            script+=click(749,171)+snap(theme+'_'+slot+'_angle')+click(701,171)
        script+='vf_reference_isolate\n'
        for platform in range(3):
            script+=f'vf_reference_platform {platform}\nvf_commit\nwait 25\n'+click(1220,40)+'+attack\nwait 15\n-attack\nwait 25\n+reload\nwait 50\n'+snap(f'{theme}_reload_{platform}')+'wait 130\n-reload\nvf_reference\nwait 25\n'
        # Restore sculpted receiver and mix an older optic finish; all new IDs persist.
        script+=f'vf_item r01_receiver_{receiver}\nvf_reference_style 4 16\nvf_commit\nwait 25\n'+snap(theme+'_mixed')+click(1220,40)
        script+=f'save vf_themes_{theme}\nwait 30\nload vf_themes_{theme}\nwait 180\ndeveloper 1\nvf_reference\nwait 25\n'+snap(theme+'_restored')
    script+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
    log=run_cfg('vf_reference_themes_test',script,captures=captures,timeout=180)
    for theme,label,style,receiver in [('inventor','Inventeur',12,'arch'),('diesel','Dieselpunk',13,'gyre')]:
        assert 'VFUI click: '+label in log
        assert f'VFR01 styles accepted: player=1 first={style} optic={style} feed={style}'in log
        after=log.split(f'Loading game from save/vf_themes_{theme}.sav')[-1]
        assert f'receiver=r01_receiver_{receiver} power=r01_power_{theme} chamber=r01_chamber_{theme} optic=r01_optic_{theme} cooling=r01_cooling_{theme}'in after
        assert f'VFR01 state: player=1 first={style} optic=4 feed={style}'in after
    assert 'VFR01 audit: checked=1753 failed=0 parts=12 combinations=191102976'in log
    assert 'VFEquipment audit: objects=1113 passed=1113 failed=0'in log
    assert 'VFState rejected'not in log and 'rejected=0'in log
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
    for board_name,views in [('modules',[('chamber_angle','Culasse'),('optic_angle','Optique'),('power_angle','Reserve'),('cooling_angle','Refroidissement')]),('sets',[('angle','Assemblage'),('hand','En main')])]:
        board=Image.new('RGB',(1440,465*len(views)+45),'#111820');draw=ImageDraw.Draw(board)
        for col,(theme,title)in enumerate([('inventor','Rome / Atelier d inventeur'),('diesel','Dieselpunk')]):
            draw.text((720*col+16,8),title,font=font,fill='#edd8ad')
            for row,(kind,label)in enumerate(views):
                im=Image.open(MOD/'scrshots'/f'themes_{theme}_{kind}.png').convert('RGB')
                im=im.crop((780,500,1920,1080)).resize((720,366),Image.Resampling.LANCZOS)if kind=='hand'else im.crop((490,305,1210,726))
                y=45+465*row;board.paste(im,(720*col,y+30));draw.text((720*col+16,y),label,font=font,fill='white')
        board.save(ROOT/f'build/r01-themed-{board_name}.jpg',quality=95,subsampling=0)
    (ROOT/'build/reference-themes-native.json').write_text(json.dumps(dict(captures=captures,reloads=6,assemblies=1753,equipment_objects=1113,checks=['two UI presets','eight meshes inspected from two sides','both sets fire and reload on three platforms','two saves preserve all four new IDs and mixed finishes']),indent=2))
    print('PASS themed modules native:',len(captures),'captures; six reloads; two saves; 1753 assemblies',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native','all'],default='assets');args=p.parse_args()
    if args.mode in ('assets','all'):assets()
    if args.mode in ('native','all'):native()

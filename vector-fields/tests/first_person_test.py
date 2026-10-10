"""Independent first-person appearance, preserved geometry and native reloads."""
import argparse,hashlib,json,re,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build_modular as base
import build_reference_platforms as pf
from studio_assets import Studio
OUT=ROOT/'generated/r01'


def assets():
    record=json.loads((OUT/'first-person.json').read_text())
    _,_,source=base.read_smd(OUT/'mp40_hands.smd')
    def vertices(tris):
        return {tuple(round(float(x),4)for x in row.split()[:4])for _,rows in tris for row in rows}
    # Independently identified accessory faces in the original MP40 import.
    cuff={201,202,203,204,205,206,207,208,209,210,211,212,298,299,300,301,302,303,
          337,338,339,340,341,342,343,344,345,346,414,415,416,417,418,419,432,433}
    discarded=cuff|set(range(467,474))|set(range(534,546))
    retained=[tri for i,tri in enumerate(source)if i not in discarded]
    expected=vertices(retained);combined=[];parts={}
    assert len(retained)==491 and record['texture_quality']=='classic'
    assert record['removed_source_triangles']==dict(display=12,wrist_frame=7,detached_cuff=36)
    assert record['uv_layout']=='anatomical charts'
    assert record['refinement']['new_bones']==0 and 0<record['refinement']['max_rounding_units']<=.100001
    assert 0<record['refinement']['added_triangles']<500
    rigs=[Studio(OUT/('r01_rig'+suffix+'.mdl'))for suffix in ('','_side','_top')]
    for kind in ('gloves','sleeves'):
        _,_,tris=base.read_smd(OUT/f'r01_fp_{kind}.smd');combined+=tris
        mdl=Studio(OUT/f'r01_fp_{kind}.mdl');parts[kind]=mdl
        assert len(mdl.mesh())==len(tris)>0
        assert mdl.numskinfamilies==14 and mdl.numskinref==1
        assert all(set(mdl.names)<=set(r.names)for r in rigs),'every merge bone must exist on each platform'
        for bone,name in enumerate(mdl.names):
            for rig in rigs:assert np.allclose(mdl.bind[bone],rig.bind[rig.names.index(name)],atol=2e-4),'merge bind changed'
        nt,off=struct.unpack_from('<ii',mdl.data,180)
        assert all(not(struct.unpack_from('<i',mdl.data,off+80*i+64)[0]&2)for i in range(nt)),'CHROME would override authored UVs'
        for _,rows in tris:
            uv=np.array([list(map(float,row.split()[7:9]))for row in rows])
            assert np.isfinite(uv).all() and np.min(uv)>=0 and np.max(uv)<=1
            assert abs(np.cross(uv[1]-uv[0],uv[2]-uv[0]))>1e-9,'UV end faces and seams must not collapse'
            normals=np.array([list(map(float,row.split()[4:7]))for row in rows])
            assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=1e-4),'smooth normals must remain unit vectors'
        assert len({hashlib.sha256(t[3]+t[4]).hexdigest()for t in mdl.textures})==14
    actual=vertices(combined)
    assert expected<=actual,'all original anatomical vertices and bone weights must be retained'
    assert actual&vertices(source)==expected,'display/frame/cuff vertices must not survive the cleanup'
    assert not any(33<=int(v[0])<=38 for v in actual),'detached elbow-driven cuff remains'
    assert len(combined)==491+record['refinement']['added_triangles']==record['triangles']
    assert len(combined)<1100,'targeted smoothing must remain lightweight'
    _,_,basebind=base.skeleton(OUT/'mp40_hands.smd');local=np.linalg.inv(basebind[12])
    natural=[]
    for _,rows in retained:
        a=np.array([list(map(float,r.split()[1:4]))for r in rows])
        if a[:,0].mean()>0:natural.append(np.array([(local@np.r_[v,1])[:3]for v in a]))
    for x in (-1.,0.,1.):
        for y in (1.2,2.5,4.):
            hits=[]
            for a in natural:
                try:w=np.linalg.solve(np.column_stack([a[1,:2]-a[0,:2],a[2,:2]-a[0,:2]]),np.array([x,y])-a[0,:2])
                except np.linalg.LinAlgError:continue
                w=np.r_[1-w.sum(),w]
                if w.min()>=-1e-5:hits.append(w@a[:,2])
            assert hits and max(hits)>.5,'removing the display must expose the existing closed glove surface'
    assert all(int(v[0])in ({6,12}|set(range(7,10))|set(range(13,32)))for v in actual-expected),'added geometry must stay on hands and fingers'
    # New finger vertices must round existing same-bone edges by at most .1,
    # never invent a weight in the middle of an animated joint.
    edge_midpoints={}
    for _,rows in retained:
        a=np.array([list(map(float,r.split()[:4]))for r in rows])
        for i in range(3):
            v,w=a[i],a[(i+1)%3]
            if v[0]==w[0]:edge_midpoints.setdefault(int(v[0]),[]).append((v[1:4]+w[1:4])/2)
    for v in actual-expected:
        bone=int(v[0])
        if bone!=12:
            mids=np.array(edge_midpoints[bone])
            assert np.min(np.linalg.norm(mids-np.array(v[1:4]),axis=1))<=.1002,'finger refinement changed joint weights or expanded the silhouette too far'
    _,_,bind=base.skeleton(OUT/'mp40_hands.smd')
    _,_,gloves=base.read_smd(OUT/'r01_fp_gloves.smd')
    for _,rows in gloves:
        for row in rows:
            a=list(map(float,row.split()))
            inv=np.linalg.inv(bind[12 if a[1]>0 else 6]);q=(inv@np.r_[a[1:4],1])[:3]
            assert q[1]>-3,'long under-sleeve panels must follow the torso, not the glove'

    # Verify paired skin references against both compiled models, including cross-outfit pairs.
    for glove in range(14):
        for sleeve in range(14):
            for kind,index in [('gloves',glove),('sleeves',sleeve)]:
                mdl=parts[kind];tex=mdl.textures[mdl.skin[index]]
                assert tex[0]==f'fp_{kind}_{index:02}.bmp' and tex[1:3]==mdl.textures[0][1:3] and all(0<n<=512 for n in tex[1:3])
    _,parents,_=base.skeleton(OUT/'mp40_hands.smd')
    _,idle=pf.read_frames(OUT/'side_idle.smd')
    idle_bend=Rotation.from_matrix(idle[0][12][:3,:3]).magnitude()*180/np.pi
    assert idle_bend<30,'lateral wrist must remain relaxed'
    g=pf.globals_of(idle[0],parents);elbow=(np.linalg.inv(g[40])@g[10])[:3,3]
    assert elbow[2]<-10,'elbow must remain below the weapon to keep the view clear'
    _,reload=pf.read_frames(OUT/'side_reload.smd');rot=[f[10][:3,:3]for f in reload]
    max_step=max(Rotation.from_matrix(a.T@b).magnitude()*180/np.pi for a,b in zip(rot,rot[1:]))
    assert max_step<12,'elbow pole must not flip during magazine exchange'
    # Judge the compiled finger against the cassette shell, rather than requiring
    # identical rotations on differently positioned fingers.
    from animation_workshop_assets_test import grip_checks
    index_clearance=grip_checks()
    _,original=pf.read_frames(OUT/'reload.smd')
    _,top=pf.read_frames(OUT/'top_reload.smd')
    rolls=[];heights=[]
    for t,(old,new) in enumerate(zip(original,top)):
        o=pf.globals_of(old,parents);g=pf.globals_of(new,parents)
        # Contact with the right grip is checked from serialized poses, independently
        # of the IK report. Rolling cannot pull the weapon out of that hand.
        assert np.allclose(np.linalg.inv(g[40])@g[6],np.linalg.inv(o[40])@o[6],atol=2e-5),'right hand lost its grip during the roll'
        lengths=[np.linalg.norm(g[4][:3,3]-g[3][:3,3]),np.linalg.norm(g[6][:3,3]-g[4][:3,3])]
        expected_lengths=[np.linalg.norm(o[4][:3,3]-o[3][:3,3]),np.linalg.norm(o[6][:3,3]-o[4][:3,3])]
        assert np.allclose(lengths,expected_lengths,atol=2e-5),'right arm stretched during the roll'
        if 18<=t<=99:
            unrolled=o[40]@np.linalg.inv(g[40])@g[12]
            heights.append((g[12][2,3],unrolled[2,3]))
        delta=o[40][:3,:3].T@g[40][:3,:3]
        angle=Rotation.from_matrix(delta).as_euler('xyz',degrees=True)
        assert abs(angle[0])<1e-4 and abs(angle[2])<1e-4,'top reload must roll around the forward axis'
        rolls.append(angle[1])
        if t in (0,129,139):assert np.allclose(new[40],old[40],atol=2e-7),'reload must return to the original weapon pose'
    assert np.allclose(rolls[18:100],-65,atol=1e-4),'top must rotate toward the left through extraction'
    assert max(abs(np.diff(rolls)))<5.5,'top roll must ease in and out'
    peaks=np.max(heights,axis=0)
    assert peaks[1]-peaks[0]>15,'left hand must stay lower through top extraction'
    unchanged=None;baseline=ROOT/'build/first-person-baseline/weapon-hashes.json'
    if baseline.exists():
        hashes=json.loads(baseline.read_text());unchanged=len(hashes)
        assert all(hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h for p,h in hashes.items()),'weapon meshes/textures changed while updating hands'
    return dict(triangles=len(combined),added_finger_triangles=record['refinement']['added_triangles'],skin_pairs=196,weapon_models_unchanged=unchanged,idle_wrist_degrees=idle_bend,max_reload_elbow_step_degrees=max_step,top_reload_roll_degrees=min(rolls),top_wrist_height_reduction_units=float(peaks[1]-peaks[0]),removed_accessory_triangles=len(discarded),index_clearance=index_clearance,
                checks=['original glove surface and joint vertices retained; complete display/frame and detached cuff removed; fingers rounded without new bones','merge bones and bind pose compatible with all three rigs','14 non-CHROME skin families on each part, noncollapsed anatomical UVs, smooth glove normals','all 196 glove/sleeve skin pairs resolve','relaxed lateral wrist and low elbow','no elbow pole flip in reload','compiled index clears the shared cassette shell on all three feeds','smooth left top-reload roll, right grip and both arm lengths preserved'])


def native():
    from library_engine_test import run_cfg,click,MOD
    bank=json.loads((OUT/'first-person.json').read_text())['themes'];captures=[]
    def snap(label):
        name='fp_'+label;captures.append(name)
        return f'wait 12\nscreenshot scrshots/{name}.png\nwait 4\n'
    def equip(gloves,torso):
        return f'vf_item gign_gloves_{gloves}\nvf_item gign_torso_{torso}\nvf_commit\nwait 24\n'
    s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_reference\nwait 25\nvf_item r01_receiver_side__original\n'
    for t in bank:
        s+=f'echo FP_THEME_{t["skin"]}\n'+equip(t['key'],t['key'])+click(1220,40)+'wait 25\nvf_engine_stats\n'+snap(t['key'])+'vf_reference\nwait 15\n'
    # Change gloves alone, then torso alone. Immutable weapon items remain identical.
    s+='echo FP_GLOVES_ONLY\nvf_item gign_gloves_roman_inventor\nvf_commit\nwait 25\n'+click(1220,40)+'vf_engine_stats\n'+snap('mixed_roman_gloves')+'vf_reference\nwait 15\n'
    s+='echo FP_TORSO_ONLY\nvf_item gign_torso_diver\nvf_commit\nwait 25\n'+click(1220,40)+'vf_engine_stats\n'+snap('mixed_diver_sleeves')+'save vf_first_person_020\nwait 30\nload vf_first_person_020\nwait 180\ndeveloper 1\necho FP_RESTORED\nvf_engine_stats\n'+snap('restored')+'vf_reference\nwait 15\n'
    for receiver in ('a','side','arch_top'):
        s+=f'vf_item r01_receiver_{receiver}__original\n'+equip('roman_inventor','roman_inventor')
        for mag in 'abcd':
            s+=f'vf_item r01_feed_{mag}__original\nvf_commit\nwait 20\n'+click(1220,40)+'wait 25\n+attack\nwait 15\n-attack\nwait 25\n+reload\nwait 30\n'+snap(f'{receiver}_{mag}_out')+'wait 70\n'+snap(f'{receiver}_{mag}_in')+'wait 85\n-reload\nvf_reference\nwait 20\n'
    s+='vf_reference_hands 1\nvf_animation 0\nvf_animation_time 0\n'+snap('preview_hands')+'vf_reference_hands 0\n'+snap('preview_clean')
    # Fully loaded hands use the same cached assemblies across normal gameplay frames.
    s+=click(1220,40)+'vf_engine_stats\nwait 120\nvf_engine_stats\nvf_reference_audit\nvf_engine_stats\nquit\n'
    log=run_cfg('vf_first_person_test',s,captures=captures,timeout=190)
    def section(key):
        match=re.search(re.escape(key)+r'\s*\n',log);assert match,key
        return log[match.end():].split('FP_',1)[0]
    for t in bank:
        assert f'gloves={t["skin"]} sleeves={t["skin"]} parts=14 rig=models/vf_r01/r01_rig_side.mdl' in section(f'FP_THEME_{t["skin"]}'),t
    for label,glove,sleeve in [('FP_GLOVES_ONLY',12,13),('FP_TORSO_ONLY',12,11),('FP_RESTORED',12,11)]:
        assert f'gloves={glove} sleeves={sleeve} parts=14' in section(label),label
    assert 'VFR01 audit: checked=1753 failed=0' in log
    assert 'VFState rejected'not in log and 'VF equipment: result=6'not in log
    stats=re.findall(r'VFEngine: assemblies=.*?loads=(\d+).*?rejected=(\d+).*?texture_bytes=(\d+)',log)
    assert stats and all(int(r[1])==0 for r in stats)
    assert stats[-3][0]==stats[-2][0],'idle viewmodel should not continually reload models'
    return dict(captures=captures,resolution=[1920,1080],last_texture_bytes=int(stats[-1][2]),checks=['14 complete outfits rendered in first person','changing gloves and torso independently','mixed appearance survives save/load','all four magazines fire and reload on bottom, side and top rigs','optional preview hands and clean player preview','1753 pairwise assemblies with the new hands','no rejected assemblies or recurring model loads'])


def sweep():
    """Dense native reload captures; inspect the proximal sleeve edge visually."""
    from library_engine_test import run_cfg,click
    captures=[]
    s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_reference\nwait 25\nvf_item r01_receiver_arch_top__original\nvf_item gign_gloves_gign\nvf_item gign_torso_gign\nvf_commit\nwait 24\n'+click(1220,40)+'wait 25\n+attack\nwait 15\n-attack\nwait 25\n+reload\n'
    for i in range(23):
        name=f'fp_fix_top_{i:02}';captures.append(name)
        s+=f'wait 6\nscreenshot scrshots/{name}.png\nwait 2\n'
    s+='wait 60\n-reload\nvf_reference\nwait 20\nvf_item r01_receiver_side__original\nvf_commit\nwait 20\n'+click(1220,40)+'wait 25\n+attack\nwait 15\n-attack\nwait 25\n+reload\n'
    for i in range(12):
        name=f'fp_fix_side_{i:02}';captures.append(name)
        s+=f'wait 10\nscreenshot scrshots/{name}.png\nwait 3\n'
    s+='wait 80\n-reload\nvf_engine_stats\nquit\n'
    log=run_cfg('vf_hands_0201_sweep',s,captures=captures,timeout=60)
    assert 'rejected=0' in log
    return dict(captures=captures,resolution=[1920,1080],checks=['dense top and side reload capture sweep','no rejected assemblies'],
                limits=['sleeve end visibility and finger silhouette require visual inspection of captures'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native','sweep','all'],default='all');a=p.parse_args();report={}
    if a.mode in ('assets','all'):report['assets']=assets()
    if a.mode in ('native','all'):report['native']=native()
    if a.mode in ('sweep','all'):report['sweep']=sweep()
    (ROOT/'build'/f'first-person-{a.mode}-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS first-person',a.mode,json.dumps({k:v if k=='assets' else dict(captures=len(v['captures']),checks=v['checks'])for k,v in report.items()}))

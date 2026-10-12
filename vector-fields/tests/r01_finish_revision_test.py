"""Reviewed native surfaces, real grip seats and model-specific texture bindings."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_r01_finish as finish
from studio_assets import Studio
from r01_finish_policy import policy

def run():
    revisions=finish.approved();assert len(revisions)==15
    metas=json.loads((ROOT/'generated/r01/manifest.json').read_text());models={r['id']:r for r in metas['pieces']}
    specs=policy()['models'];styles={s['id']:s['skin'] for s in metas['styles']};maps=set()
    def key(rows):return tuple(sorted(tuple(np.round(r['p'],5)) for r in rows))
    def nonzero(rows):
        p=np.array([r['p'] for r in rows]);return np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-9
    for ident,r in revisions.items():
        src=finish.WORKSHOP/ident/'baseline.mdl';path=ROOT/'generated/r01'/(ident+'.mdl');mdl=Studio(path);baseline=Studio(src)
        assert finish.is_current(path) and models[ident]['sha256']==r['sha256']
        assert len(mdl.mesh())==models[ident]['triangles'] and mdl.names==['module_root']
        assert np.allclose(mdl.bind[0],np.eye(4),atol=1e-6) and mdl.sequences==baseline.sequences
        assert (mdl.numskinref,mdl.numskinfamilies,len(mdl.textures))==(1,14,2)
        indices=[mdl.skin[styles[s]] for s in specs[ident]['styles']];assert sorted(indices)==[0,1]
        assert set(mdl.skin)=={0,1} and all(t[1:3]==(512,512) for t in mdl.textures)
        for tex in mdl.textures:maps.add(hashlib.sha256(tex[3]+tex[4]).hexdigest())
        points=np.array([v['p'] for _,rs in mdl.mesh() for v in rs]);assert np.isfinite(points).all()
        assert len(np.unique(points,axis=0))<=2048 and r['uv_audit']['overlap_samples']==0
        before=Counter(key(rs) for _,rs in baseline.mesh() if nonzero(rs));after=Counter(key(rs) for _,rs in mdl.mesh() if nonzero(rs))
        if r['retained_native_geometry']:assert before==after,ident
        if ident.startswith('r01_grip_'):
            kept=Counter(key(rs) for _,rs in baseline.mesh() if nonzero(rs) and not (min(v['p'][1] for v in rs)>-4.2 and max(v['p'][2] for v in rs)<-1.5))
            assert not (kept-after),'Retained stock surface moved'
            handle=points[(points[:,1]>-4.2)&(points[:,2]<-1.1)]
            assert handle[:,0].min()>-1.3 and handle[:,0].max()<1.3
            assert -9.1<handle[:,2].min()<-8.5 and -1.4<handle[:,2].max()<-1.1
            assert r['handle_structure']['all_required_connected']
        live=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'/path.name;assert path.read_bytes()==live.read_bytes()
    assert len(maps)==30,'Each model and finish has its own baked texture'
    # The A47 is the only receiver with revised surface geometry this pass.
    points=np.unique(np.array([v['p'] for _,rs in Studio(ROOT/'generated/r01/r01_receiver_a47.mdl').mesh() for v in rs]),axis=0)
    axial=json.loads((ROOT/'chassis-workshop/identity-2026-10-11/a47/axial-source.json').read_text());sections=0
    for part in axial:
        for section in part['axial_sections']:
            for radius in (section['outer'],section['inner']):
                expected=np.array([[radius*np.cos(2*np.pi*j/part['sides']),section['y'],1.3+radius*np.sin(2*np.pi*j/part['sides'])]for j in range(part['sides'])])
                actual=points[[np.linalg.norm(points-p,axis=1).argmin() for p in expected]]
                assert np.max(np.linalg.norm(actual-expected,axis=1))<3e-6
                assert np.linalg.norm(actual.mean(0)[[0,2]]-[0,1.3])<3e-6;sections+=1
    # Native culling follows the compiled winding, including the small
    # chamfers preserved past StudioMDL's decimal-grid conversion.
    ak=Studio(ROOT/'generated/r01/r01_receiver_a47.mdl')
    facing=[np.dot(np.cross(rs[1]['p']-rs[0]['p'],rs[2]['p']-rs[0]['p']),sum((r['n'] for r in rs))) for _,rs in ak.mesh()]
    assert np.mean(np.array(facing)>0)>.999
    seam=json.loads((finish.WORKSHOP/'seam-audit.json').read_text())
    assert len(seam)==15 and all(r['after']['max_uv_error_texels']<.501 and r['after']['missing_authored_triangles']==0 for r in seam.values())
    hold=json.loads((finish.WORKSHOP/'hold-proof/contacts.json').read_text());assert hold['attachment_cases']==52
    assert all(c['contact'] for c in hold['contacts']) and not hold['source_hand_mesh_changed'] and not hold['source_hand_pose_changed']
    installed=json.loads((finish.WORKSHOP/'installation.json').read_text())
    assert installed['animated_models_written']==installed['player_models_written']==installed['dlls_written']==0
    assert installed['non_weapon_catalogue_rows_preserved'] and installed['non_weapon_pool_metadata_preserved']
    print('PASS R1 finish revision: 15 native models, 30 dedicated maps, 52 grip seats,',sections,'A47 concentric sections; stock surfaces retained')

if __name__=='__main__':run()

"""Conservative magazine-envelope regression for the six inspection carriers.

Socket meshes use Bone71; merged hand meshes match bones by name, because
StudioMDL removes unused bones. Existing grasp contact is allowed. The envelope
is deliberately conservative; native screenshots remain the visual authority.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from build_weapon_inspect import digest
OUT=ROOT/'build/weapon-inspect'
BASE=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'
GENERATED=ROOT/'generated/weapon-inspect'

def review(folder):
    hand=Studio(folder/'inspect_gloves.mdl');base=Studio(BASE/'r01_rig.mdl')
    byname={name:i for i,name in enumerate(base.names)};unique={}
    for _,triangle in hand.mesh():
        for vertex in triangle:
            target=byname[hand.names[vertex['b']]]
            if 10<=target<=31:
                unique[(target,*np.round(vertex['p'],5))]=(target,np.linalg.inv(hand.bind[vertex['b']])@np.r_[vertex['p'],1])
    bones=np.array([row[0] for row in unique.values()]);points=np.array([row[1] for row in unique.values()])
    reports={}
    for path in sorted(folder.glob('r01_rig*.mdl')):
        rig=Studio(path);frames=sequence_frames(rig,0);g0=globals_of(frames[0],rig.parents)
        gun=rig.names.index('Bone76');feed=rig.names.index('Bone71');mount=np.linalg.inv(g0[gun])@g0[feed]
        posed=[]
        for frame in frames:
            g=globals_of(frame,rig.parents)
            world=np.einsum('nij,nj->ni',g[bones],points)
            posed.append((np.linalg.inv(g[gun])@world.T).T[:,:3])
        magazines=[]
        for letter in 'abcd':
            model=Studio(BASE/f'r01_feed_{letter}.mdl')
            raw=np.array([np.r_[vertex['p'],1] for _,triangle in model.mesh() for vertex in triangle])
            equations=ConvexHull((mount@raw.T).T[:,:3]).equations
            depths=np.array([-np.max(p@equations[:,:3].T+equations[:,3],axis=1) for p in posed])
            maxima=np.maximum(0,depths.max(axis=1));transition=np.r_[4:24,108:132]
            worst=int(transition[np.argmax(maxima[transition])])
            magazines.append(dict(magazine=letter,initial_depth=float(maxima[0]),transition_depth=float(maxima[worst]),
                time=worst/30,vertex_bone=rig.names[int(bones[depths[worst].argmax()])],
                free_hand_depth=float(maxima[24:109].max())))
        reports[path.name]=magazines
    assert len(reports)==6
    return reports

def run():
    after=review(GENERATED)
    before=review(OUT/'before-clearance') if (OUT/'before-clearance/inspect_gloves.mdl').exists() else None
    hand=Studio(GENERATED/'inspect_gloves.mdl')
    assert not any(hand.names[v['b']]=='Bone40' for _,triangle in hand.mesh() for v in triangle),'Glove rim must follow the wrist'
    for name,rows in after.items():
        for new in rows:
            assert new['free_hand_depth']==0,(name,new)
            # A foregrip starts clear of the magazine; releasing it must stay
            # clear. Direct magazine grasps already have authored contact.
            if '_fg' in name:assert new['transition_depth']<.001,(name,new)
        print(name,[(r['magazine'],round(r['transition_depth'],3)) for r in rows],flush=True)
    report=dict(passed=True,before=before,after=after,
        model_sha256={p.name:digest(p) for p in GENERATED.glob('*.mdl')},
        geometry_sources={p.name:digest(p) for p in BASE.glob('r01_feed_*.mdl')},
        method='Conservative convex magazine envelope, all four magazine shapes, per-frame merged bones matched by name',
        checks=['six carriers and four magazines','no elbow-weighted glove rim','no foregrip-hand magazine penetration','free hand clear during both holds'],
        limits=['Direct magazine grasps retain existing contact; envelope proximity is supplemented by native visual review'])
    (OUT/'clearance.json').write_text(json.dumps(report,indent=2))
    print('PASS six inspection carriers: wrist rims attached, four magazine envelopes, foregrip and free-hand clearance')

if __name__=='__main__':run()

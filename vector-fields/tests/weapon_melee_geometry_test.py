"""Barrel-led downward contact, grounded feet, grip and released-hand clearance."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from build_weapon_melee import digest
OUT=ROOT/'build/weapon-melee';MODELS=ROOT/'generated/weapon-melee';BASE=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'
MANIFEST=MODELS/'manifest.json'
def run(output=None):
    source_models={r['file']:Path(r['source'])for r in json.loads(MANIFEST.read_text())['models']}
    glove=Studio(MODELS/'melee_gloves.mdl');base=Studio(BASE/'r01_rig.mdl');byname={n:i for i,n in enumerate(base.names)};unique={}
    for _,triangle in glove.mesh():
        for v in triangle:
            b=byname[glove.names[v['b']]]
            if 10<=b<=31:unique[(b,*np.round(v['p'],5))]=(b,np.linalg.inv(glove.bind[v['b']])@np.r_[v['p'],1])
    bones=np.array([v[0] for v in unique.values()]);points=np.array([v[1] for v in unique.values()]);reports={}
    for path in sorted(MODELS.glob('r01_*.mdl')):
        rig=Studio(path);fp='rig' in path.stem;right,gun=(6,40) if fp else (24,28)
        for sequence in ('vf_melee',) if fp else ('vf_melee','vf_melee_crouch'):
            frames=sequence_frames(rig,sequence);g=np.array([globals_of(f,rig.parents) for f in frames]);bind=np.linalg.inv(g[0,right])@g[0,gun]
            error=float(max(np.abs(np.linalg.inv(f[right])@f[gun]-bind).max() for f in g));assert error<.02,(path,error)
            assert np.abs(frames[0]-frames[-1]).max()<.001
            ordinary=Studio(source_models[path.name])
            neutral=sequence_frames(ordinary,'idle' if fp else 'ref_aim_mp5')[0].copy()
            if sequence=='vf_melee_crouch':
                spine=ordinary.names.index('Bip01 Spine')
                neutral[:spine]=sequence_frames(ordinary,'crouch_idle')[0,:spine]
            endpoint_error=float(np.max(np.abs(frames[[0,-1]]-neutral)))
            assert endpoint_error<.001,(path,sequence,'gesture does not rejoin gameplay stance',endpoint_error)
            lengths={}
            for a,b in ((3,4),(4,6),(3,10),(10,12)) if fp else ((15,16),(16,17),(22,23),(23,24)):
                lengths[str((a,b))]=float(np.ptp(np.linalg.norm(g[:,a,:3,3]-g[:,b,:3,3],axis=1)))
                assert lengths[str((a,b))]<.03,(path,sequence,a,b,lengths)
            if not fp:assert np.abs(g[:,:8]-g[0,:8]).max()<.001,'Feet and pelvis must remain grounded'
            # Local +Y runs towards the muzzle; -Y runs towards the stock.
            # Check the actual compiled trajectory rather than the control keys.
            scale=1 if fp else .68
            muzzle=np.einsum('nij,j->ni',g[:,gun],np.array([0,35.2*scale,1.3*scale,1]))[:,:3]
            stock=np.einsum('nij,j->ni',g[:,gun],np.array([0,-16.5*scale,0,1]))[:,:3]
            axis=g[:,gun,:3,1]
            assert axis[9,2]>.9,(path,sequence,'muzzle was not raised')
            assert axis[13,0]>.85,(path,sequence,'stock turned towards the target')
            assert axis[16,2]<-.35,(path,sequence,'missing downward follow-through')
            assert muzzle[9,2]-muzzle[13,2]>15*scale,(path,sequence,'not a downward strike')
            assert muzzle[12,2]>muzzle[13,2]>muzzle[14,2],(path,sequence,'impact outside descent')
            assert muzzle[13,0]-stock[13,0]>40*scale,(path,sequence,'stock leads contact')
            left=12 if fp else 17
            free=np.max(np.abs(g[4:28,left,:3,3]-g[4,left,:3,3]))
            assert free<3,(path,sequence,'free guard must stay compact and independent of the weapon')
            fore=10 if fp else 16;axis=1 if fp else 0
            direction=g[9:24,left,:3,3]-g[9:24,fore,:3,3]
            direction/=np.linalg.norm(direction,axis=1)[:,None]
            cosine=np.sum(direction*g[9:24,left,:3,axis],axis=1)
            wrist_bend=float(np.degrees(np.arccos(np.clip(cosine,-1,1))).max())
            assert wrist_bend<1,(path,sequence,'bent free wrist',wrist_bend)
            if fp:
                assert g[13,left,2,3]<g[13,right,2,3]-3,(path,sequence,'free fist is not below strike')
                for knuckle,tip in [(16,19),(20,23),(24,27),(28,31)]:
                    point=(np.linalg.inv(g[13,left])@g[13,tip])[:3,3]
                    basepoint=(np.linalg.inv(g[13,left])@g[13,knuckle])[:3,3]
                    assert point[2]<basepoint[2]-1 and point[1]<basepoint[1]+1,(path,tip,'fingers must curl into palm')
            else:
                assert g[13,left,0,3]>12 and g[13,left,2,3]>g[13,11,2,3]-10,(path,sequence,'free fist must guard in front of torso')
                hand=np.linalg.inv(g[13,left]);finger=hand@g[13,20];thumb=hand@g[13,18]
                assert finger[1,3]>.5 and thumb[1,0]>.2,(path,'TP fingers and thumb must close on the palm side')
            report=dict(wrist_attachment_error=error,arm_length_variation=lengths,gameplay_stance_endpoint_error=endpoint_error,
                raised_muzzle_z=float(muzzle[9,2]),impact_muzzle=muzzle[13].tolist(),
                muzzle_drop_to_impact=float(muzzle[9,2]-muzzle[13,2]),
                muzzle_ahead_of_stock=float(muzzle[13,0]-stock[13,0]),released_hand_drift=float(free),free_wrist_bend_degrees=wrist_bend)
            if fp:
                posed=[];feed=41
                mount=np.linalg.inv(g[0,gun])@g[0,feed]
                for f in g:
                    world=np.einsum('nij,nj->ni',f[bones],points);posed.append((np.linalg.inv(f[gun])@world.T).T[:,:3])
                magazines=[]
                for letter in 'abcd':
                    mesh=Studio(BASE/f'r01_feed_{letter}.mdl');raw=np.array([np.r_[v['p'],1] for _,tri in mesh.mesh() for v in tri])
                    equations=ConvexHull((mount@raw.T).T[:,:3]).equations
                    depths=np.array([-np.max(p@equations[:,:3].T+equations[:,3],axis=1) for p in posed])
                    maxima=np.maximum(0,depths.max(axis=1));free=float(maxima[4:28].max())
                    assert free<.001,(path.name,letter,free,int(np.argmax(maxima[4:28]))+4)
                    magazines.append(dict(shape=letter,free_hand_depth=free))
                report['magazines']=magazines
            reports[path.name+'/'+sequence]=report
    assert len(reports)==12
    report=dict(passed=True,rigs=reports,assets={p.name:digest(p) for p in MODELS.glob('*.mdl')},
        magazine_inputs={str(p):digest(p) for p in BASE.glob('r01_feed_*.mdl')},
        checks=['raised barrel, descending at keyed contact and downward follow-through','muzzle ahead of stock at impact',
        'released hand stays free below strike','rigid weapon/right wrist','arm segment lengths preserved',
        'stationary third-person pelvis/feet','endpoints match the actual standing/crouch gait composition',
        'four magazines clear of released left hand on six mounts'])
    target=Path(output) if output else OUT;target.mkdir(parents=True,exist_ok=True)
    (target/'geometry.json').write_text(json.dumps(report,indent=2));print('PASS melee geometry: twelve downward barrel strikes, wrist/feet/lengths and six-mount magazine clearance')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);run(parser.parse_args().output)

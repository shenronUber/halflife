"""Author R-01 third-person arm poses on the fitted carrier; keep locomotion intact.

Recipes use compiled GoldSrc coordinates (+X forward, +Y left, +Z up).
Weapon sockets reuse the actual first-person module meshes, at uniform scale.
Only the six arm joints and finger rotations are edited in existing sequences.
"""
import argparse,hashlib,json,math,re
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from studio_assets import Studio
from animation_assets import globals_of,sequence_frames,sequence_info,packed_frames
from build_reference_platforms import rotation_between,blend
from build_modular import compile_model
import build_cache
from model_contract import load as model_contract,check_skeleton

ROOT=Path(__file__).resolve().parent
TP=ROOT/'generated/personas'
FP=ROOT/'generated/r01'
OUT=ROOT/'generated/third-person'
RECIPE=ROOT/'assets/animations/r01-third-person.json'
CONTRACT=model_contract()
SOCKETS=[CONTRACT['sockets']['third_person'][key] for key in ('weapon','feed','chamber')]
ARMS=[15,16,17,18,19,20,22,23,24,25,26,27]
KEEP=[i for i in range(28) if i not in ARMS]


def transform(position=(0,0,0),angles=(0,0,0)):
    m=np.eye(4);m[:3,:3]=Rotation.from_euler('xyz',angles,degrees=True).as_matrix();m[:3,3]=position;return m


def sample(frames,t):
    a=int(t)%len(frames);b=min(a+1,len(frames)-1)
    return np.array([blend(x,y,t-int(t)) for x,y in zip(frames[a],frames[b])])


def solve(local,parents,side,goal,pole):
    """Analytic two-link IK: rotations only, no stretch or changed clavicle."""
    upper,fore,hand=(15,16,17) if side=='left' else (22,23,24)
    g=globals_of(local,parents);s=g[upper][:3,3];e=g[fore][:3,3];w=g[hand][:3,3]
    a=np.linalg.norm(e-s);b=np.linalg.norm(w-e);delta=goal[:3,3]-s;d=np.linalg.norm(delta)
    if not abs(a-b)+1e-5<d<a+b-1e-5:raise ValueError(f'{side} wrist unreachable: {d:.3f} / {a+b:.3f}')
    v=delta/d;p=np.array(pole)-s;p-=v*(p@v);p/=np.linalg.norm(p)
    along=(a*a-b*b+d*d)/(2*d);new_e=s+along*v+math.sqrt(max(0,a*a-along*along))*p
    desired=g[upper].copy();desired[:3,:3]=rotation_between(e-s,new_e-s)@g[upper][:3,:3]
    local[upper][:3,:3]=g[parents[upper]][:3,:3].T@desired[:3,:3]
    g=globals_of(local,parents)
    desired=rotation_between(g[hand][:3,3]-g[fore][:3,3],goal[:3,3]-g[fore][:3,3])@g[fore][:3,:3]
    local[fore][:3,:3]=g[upper][:3,:3].T@desired
    g=globals_of(local,parents);local[hand][:3,:3]=g[fore][:3,:3].T@goal[:3,:3]
    actual=globals_of(local,parents)[hand]
    return float(np.max(np.abs(actual-goal)))


class Author:
    def __init__(self,recipe=None):
        self.recipe=recipe or json.loads(RECIPE.read_text(encoding='utf-8'))
        self.rig=Studio(TP/'persona_rig.mdl')
        check_skeleton(self.rig.names,'third_person',CONTRACT)
        if len(self.rig.sequences)!=CONTRACT['persona_sequences']:raise ValueError('Persona sequence contract changed')
        from build_personas import donor,ASSETS
        self.source=Studio(donor(json.loads((ASSETS/'personas.json').read_text()))['path'])
        from inspect_animations import retarget
        self.donor_aim=retarget(self.source,self.rig,'ref_aim_mp5')[0]
        self.neutral=sequence_frames(self.rig,'ref_aim_mp5')[0]
        self.chest=globals_of(self.neutral,self.rig.parents)[11]
        self.scale=self.recipe['weapon']['scale']
        self.gun=transform(self.recipe['weapon']['position'],self.recipe['weapon']['angles'])
        self.hand_rot={s:globals_of(self.donor_aim,self.rig.parents)[i][:3,:3] for s,i in [('left',17),('right',24)]}
        f=Studio(FP/'r01_rig.mdl');g=globals_of(sequence_frames(f,'idle')[0],f.parents)
        self.mag=np.linalg.inv(g[f.names.index(CONTRACT['sockets']['first_person']['weapon'])])@g[f.names.index(CONTRACT['sockets']['first_person']['feed'])]
        self.mag[:3,3]*=self.scale
        self.model=SimpleNamespace(names=self.rig.names+SOCKETS,parents=self.rig.parents+[24,28,28])
        self.max_error=0.

    def goal(self,gun,side):
        cfg=self.recipe[side];m=np.eye(4);m[:3,:3]=gun[:3,:3]@self.gun[:3,:3].T@self.hand_rot[side]@Rotation.from_euler('xyz',cfg['angles'],degrees=True).as_matrix()
        point=(gun@np.r_[np.array(cfg['contact'])*self.scale,1])[:3]
        m[:3,3]=point-m[:3,:3]@cfg['palm'];return m

    def frame(self,base,platform,t=0,reload=None,shoot=False):
        local=base.copy();g=globals_of(local,self.rig.parents)
        follow=g[11]@np.linalg.inv(self.chest);gun=follow@self.gun
        # Tiny custom recoil; both hands stay constrained to the gun.
        if shoot:
            recoil=math.sin(math.pi*min(1,t))
            gun[:3,3]-=gun[:3,1]*self.recipe['recoil']['distance']*recoil
            gun[:3,:3]=gun[:3,:3]@Rotation.from_euler('x',self.recipe['recoil']['pitch']*recoil,degrees=True).as_matrix()
        mag=self.mag.copy()
        if platform!='bottom':
            from build_reference_platforms import mount_matrix
            mount=mount_matrix(platform);mount[:3,3]*=self.scale;mag=mount@mag
        left=self.goal(gun,'left');right=self.goal(gun,'right')
        if reload is not None:
            # The CS arm gesture supplies timing and wrist attitude. The final
            # wrists are fitted to our actual gun/magazine, without its leg pose.
            donor=sample(reload,t*(len(reload)-1));dg=globals_of(donor,self.rig.parents)
            start=globals_of(reload[0],self.rig.parents)
            weight=math.sin(math.pi*t)**2
            gun[:3,3]+=follow[:3,:3]@((dg[24][:3,3]-start[24][:3,3])*.06+np.array([-.7,0,-1.1]))*weight
            # Roll around the firing-hand contact, exposing the feed to the
            # support hand without sliding the right palm along the grip.
            pivot=np.r_[np.array(self.recipe['right']['contact'])*self.scale,1]
            anchor=(gun@pivot)[:3]
            angles=self.recipe.get('reload',{}).get(platform,{}).get('angles',[0,-8,0])
            gun[:3,:3]=gun[:3,:3]@Rotation.from_euler('xyz',np.array(angles)*weight,degrees=True).as_matrix()
            gun[:3,3]=anchor-gun[:3,:3]@pivot[:3]
            right=self.goal(gun,'right');left=self.goal(gun,'left')
            keys=[(0,[0,0,0]),(.18,[0,0,0]),(.34,[-5,0,0] if platform=='side' else [0,0,5] if platform=='top' else [0,0,-5]),(.48,[-4,-8,-5]),(.63,[-4,-8,-5]),(.78,[-5,0,0] if platform=='side' else [0,0,5] if platform=='top' else [0,0,-5]),(.9,[0,0,0]),(1,[0,0,0])]
            offset=np.zeros(3)
            for (t0,a),(t1,b) in zip(keys,keys[1:]):
                if t<=t1:
                    u=np.clip((t-t0)/(t1-t0),0,1);u=u*u*(3-2*u);offset=(np.array(a)*(1-u)+np.array(b)*u)*self.scale;break
            mag[:3,3]+=offset
            # Grab the outer side of the actual magazine. At both endpoints the
            # hand returns to the support socket, giving a continuous transition.
            contact=np.array([2.25,13.6,-6.0])*self.scale
            if platform!='bottom':contact=(mount@np.r_[contact,1])[:3]
            contact+=offset
            grab=left.copy()
            if platform!='bottom':grab[:3,:3]=gun[:3,:3]@mount[:3,:3]@gun[:3,:3].T@grab[:3,:3]
            attitude=Rotation.from_matrix(dg[17][:3,:3]@start[17][:3,:3].T).as_rotvec()
            grab[:3,:3]=Rotation.from_rotvec(attitude*.08*weight).as_matrix()@grab[:3,:3]
            # Apply attitude before fitting the palm, keeping the magazine
            # contact exact through extraction and insertion on every feed.
            grab[:3,3]=(gun@np.r_[contact,1])[:3]-grab[:3,:3]@self.recipe['left']['palm']
            mix=min(1,t/.18,(1-t)/.1);left=blend(left,grab,mix)
        for side,ids in [('left',[18,19,20]),('right',[25,26,27])]:
            for i in ids:local[i][:3,:3]=self.donor_aim[i][:3,:3]
            cfg=self.recipe[side];pole=(follow@np.r_[cfg['elbow'],1])[:3]
            self.max_error=max(self.max_error,solve(local,self.rig.parents,side,left if side=='left' else right,pole))
        g=globals_of(local,self.rig.parents)
        assert np.array_equal(local[KEEP],base[KEEP]),'Locomotion/body changed'
        return np.concatenate([local,[np.linalg.inv(g[24])@gun,mag,np.eye(4)]])

    def motion(self,name,platform,blend_index=None):
        raw=sequence_frames(self.rig,name,blend=blend_index)
        shoot='shoot' in name
        return np.array([self.frame(f,platform,i/max(1,len(raw)-1),shoot=shoot) for i,f in enumerate(raw)])

    def reload(self,name,platform):
        from inspect_animations import retarget
        donor=retarget(self.source,self.rig,name)
        base=sequence_frames(self.rig,'crouch_aim_mp5' if name.startswith('crouch') else 'ref_aim_mp5')[0]
        # Static lower body is deliberately taken from our existing stance.
        return np.array([self.frame(base,platform,i/(len(donor)-1),reload=donor) for i in range(len(donor))])


def smd(model,frames,path,triangles=None):
    undo=transform(angles=(0,0,-90));lines=['version 1','nodes']+[f'{i} "{n}" {model.parents[i]}' for i,n in enumerate(model.names)]+['end','skeleton']
    for t,frame in enumerate(frames):
        lines.append('time '+str(t))
        for i,m in enumerate(frame):
            m=undo@m if model.parents[i]<0 else m
            values=[*m[:3,3],*Rotation.from_matrix(m[:3,:3]).as_euler('xyz')]
            lines.append(str(i)+' '+' '.join(f'{v:.8f}' for v in values))
    lines+=['end']
    if triangles is not None:lines+=['triangles',*triangles,'end']
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def input_paths(recipe_path=RECIPE):
    from build_personas import donor,ASSETS
    config=json.loads((ASSETS/'personas.json').read_text(encoding='utf-8'))
    paths=[Path(__file__),Path(recipe_path),ROOT/'model_contract.py',ROOT/'data/model_contract.json',
           ROOT/'animation_assets.py',ROOT/'inspect_animations.py',ROOT/'build_reference_platforms.py',
           ROOT/'build_personas.py',ASSETS/'personas.json',ROOT/'generated/visual_skins/cs-skins.json',
           Path(donor(config)['path']),FP/'r01_rig.mdl']+build_cache.compiler_inputs()
    paths += [p for p in TP.iterdir() if p.suffix in ('.mdl','.qc','.smd','.bmp')]
    return paths


def build(recipe_path=RECIPE,ensure=False):
    recipe=json.loads(Path(recipe_path).read_text(encoding='utf-8'));OUT.mkdir(parents=True,exist_ok=True)
    digest=build_cache.fingerprint(input_paths(recipe_path))
    if ensure and (OUT/'manifest.json').exists():
        old=build_cache.read(OUT/'manifest.json')
        if build_cache.current(old.get('build_cache'),digest):
            print('Third-person carriers are current.');return old
    a=Author(recipe)
    all_records=[]
    for platform,suffix in [('bottom',''),('side','_side'),('top','_top')]:
        initial=a.frame(a.neutral,platform);g=globals_of(initial,a.model.parents)
        undo=transform(angles=(0,0,-90));tri=[]
        for i,m in enumerate(g):
            tri.append('persona_original.bmp')
            for d in ([0,0,0],[.002,0,0],[0,.002,0]):
                p=(undo@np.r_[m[:3,3]+d,1])[:3]
                tri.append(str(i)+' '+' '.join(f'{v:.8f}' for v in [*p,0,0,1,.5,.5]))
        anchor='tp_anchors'+suffix;smd(a.model,[initial],OUT/(anchor+'.smd'),tri)
        qc=(TP/'persona_rig.qc').read_text().replace('"persona_rig.mdl"',f'"r01_tp{suffix}.mdl"').replace('$cdtexture "./"','$cdtexture "../personas"')
        for path in TP.glob('*.smd'):qc=qc.replace('"'+path.stem+'"','"../personas/'+path.stem+'"')
        qc=qc.replace('"../personas/persona_anchors"','"'+anchor+'"')
        qc=re.sub(r'(\$sequence ")../personas/',r'\1',qc)
        authored={}
        # Preserve the original sequence indices, blend channels, flags, events,
        # controllers and every unedited locomotion/death animation.
        names=['ref_aim_mp5','ref_shoot_mp5','crouch_aim_mp5','crouch_shoot_mp5']
        for name in names:
            info=sequence_info(a.rig,name)
            block=re.search(r'\$sequence "'+name+r'" \{.*?\}',qc,re.S)[0]
            refs=re.findall(r'"../personas/([^"\n]+)"',block)
            for i,ref in enumerate(refs):
                frames=a.motion(name,platform,i);key=platform+'_'+ref
                smd(a.model,frames,OUT/(key+'.smd'));qc=qc.replace('"../personas/'+ref+'"','"'+key+'"')
                authored[(name,i)]=frames
        for name in ['ref_reload_mp5','crouch_reload_mp5','ref_reload_rifle','crouch_reload_rifle']:
            frames=a.reload(name,platform);key=platform+'_'+name;smd(a.model,frames,OUT/(key+'.smd'))
            qc+=f'\n$sequence "{name}" {{\n "{key}"\n fps {sequence_info(a.source,name)["fps"]}\n}}\n'
            authored[(name,0)]=frames
        # Muzzle events now use real weapon coordinates instead of old MP5 offsets.
        qc=re.sub(r'^\$attachment .*$', '',qc,flags=re.M)
        for i in range(4):qc+=f'\n$attachment {i} "{SOCKETS[0]}" 0 {36.5*a.scale:.8f} 0\n'
        path=OUT/('r01_tp'+suffix+'.qc');path.write_text(qc,encoding='ascii');model=Studio(compile_model(path))
        assert model.names==a.model.names,(model.names,a.model.names)
        assert model.sequences[:CONTRACT['persona_sequences']]==a.rig.sequences
        err=0.
        for (name,bi),expected in authored.items():
            actual=sequence_frames(model,name,blend=bi)
            err=max(err,float(np.max(np.abs(np.array([globals_of(f,model.parents) for f in actual])-np.array([globals_of(f,a.model.parents) for f in expected])))))
        assert err<.03,(platform,err)
        unchanged=0.
        for name in a.rig.sequences:
            info=sequence_info(a.rig,name)
            for bi in range(info['blends']):
                old=sequence_frames(a.rig,name,blend=bi);new=sequence_frames(model,name,blend=bi)
                ids=KEEP if name in names else list(range(28))
                unchanged=max(unchanged,float(np.max(np.abs(old[:,ids]-new[:,ids]))))
        assert unchanged<.01,(platform,unchanged)
        all_records.append(dict(platform=platform,path=str(model.path),sha256=hashlib.sha256(model.data).hexdigest(),bones=len(model.names),sequences=len(model.sequences),max_compiler_global_error=err,max_preserved_local_error=unchanged))
    (ROOT.parent/'cl_dll/vf_third_person_scale.h').write_text('// Generated by third_person.py; shared with compiled R-01 sockets.\n#define VF_THIRD_PERSON_SCALE '+str(a.scale)+'f\n',encoding='ascii')
    result=dict(inputs_sha256=digest,recipe=recipe,recipe_path=str(recipe_path),models=all_records,ik_error=a.max_error,edited_bones=[a.rig.names[i] for i in ARMS],preserved_bones=[a.rig.names[i] for i in KEEP],sources=dict(body=str(a.rig.path),reload=str(a.source.path),reload_sha256=hashlib.sha256(a.source.data).hexdigest()),status='compiled assets; runtime installation is a separate step')
    outputs=[p for p in OUT.iterdir() if p.suffix in ('.mdl','.qc','.smd')]+[ROOT.parent/'cl_dll/vf_third_person_scale.h']
    result['build_cache']=build_cache.record(digest,outputs)
    build_cache.write(OUT/'manifest.json',result);print('PASS third person:',json.dumps(all_records));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,default=RECIPE);p.add_argument('--ensure',action='store_true');args=p.parse_args();build(args.recipe,args.ensure)


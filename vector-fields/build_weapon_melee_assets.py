"""Prepare installed geometry, author in Blender, then append isolated MDL tracks."""
import argparse,hashlib,json,os,struct,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
from studio_assets import Studio
from animation_assets import sequence_info,sequence_frames,globals_of,channel
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
WORK=ROOT/'melee-workshop';OUT=ROOT/'generated/weapon-melee';REVIEW=ROOT/'build/weapon-melee'
BASE=PROJECT/'runtime/vector-engine/vf_visual/models'
SOURCE_GENERATED=False
_mesh_cache={};_written_textures=set()

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source(folder,name):
    if not SOURCE_GENERATED:path=BASE/folder/name
    else:
        group='weapon-inspect' if folder=='vf_inspect' else 'personas' if folder=='vf_skins' else 'third-person' if name.startswith('r01_tp') else 'r01'
        path=ROOT/'generated'/group/name
    if name.startswith('r01_tp')or name=='persona_scout.mdl':
        from thumb_articulation import source_with_thumb
        return source_with_thumb(path)
    return path

def input_paths():
    result=[source('vf_r01',name+'.mdl') for name in ('r01_rig','r01_rig_fg','r01_rig_side','r01_rig_side_fg','r01_rig_top','r01_rig_top_fg','r01_tp','r01_tp_side','r01_tp_top',
        'r01_receiver_m40','r01_barrel_a','r01_muzzle_a','r01_feed_a','r01_chamber_a','r01_ammo_a','r01_projectile_a','r01_optic_a','r01_underbarrel_a','r01_underbarrel_b','r01_grip_a','r01_power_a','r01_cooling_a')]
    result += [source('vf_inspect','inspect_'+n+'.mdl') for n in ('gloves','sleeves')]
    result += [source('vf_skins','persona_scout.mdl'),Path(__file__),WORK/'author_melee.py',ROOT/'animation_assets.py',ROOT/'studio_assets.py',ROOT/'prepare_blender_workshop.py']
    result.append(WORK/'fist-poses.json')
    result.append(ROOT/'thumb_articulation.py')
    return sorted(result)

def mesh_data(path,rig,socket=None,scale=1):
    if str(path) not in _mesh_cache:
        model=Studio(path)
        choices={i:1 for i,(_,count,_) in enumerate(model.parts) if count>1} if path.name=='persona_scout.mdl' else None
        _mesh_cache[str(path)]=(model,model.mesh(choices))
    model,source_triangles=_mesh_cache[str(path)]
    byname={name:i for i,name in enumerate(rig.names)};materials=[];indices={}
    folder=WORK/'textures';folder.mkdir(parents=True,exist_ok=True)
    for i in sorted({texture for texture,_ in source_triangles}):
        _,w,h,pixels,palette=model.textures[i]
        target=folder/(path.stem+'_'+str(i)+'.png')
        if str(target) not in _written_textures:
            image=Image.frombytes('P',(w,h),pixels);image.putpalette(palette);image.convert('RGB').save(target)
            _written_textures.add(str(target))
        indices[i]=len(materials);materials.append(str(target))
    triangles=[]
    for texture,triangle in source_triangles:
        rows=[]
        for v in triangle:
            bone=socket if socket is not None else byname[model.names[v['b']]]
            binding=rig.bind[bone] if socket is not None else rig.bind[bone]@np.linalg.inv(model.bind[v['b']])
            p=binding@np.r_[v['p']*scale if socket is not None else v['p'],1]
            n=binding[:3,:3]@v['n']
            rows.append(dict(bone=bone,p=p[:3].tolist(),n=n.tolist(),uv=v['uv'].tolist()))
        triangles.append([indices[texture],rows])
    return dict(name=path.stem,materials=materials,triangles=triangles)

def prepare():
    WORK.mkdir(exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    inputs={str(p):digest(p) for p in input_paths()};rigs=[]
    for kind in ('fp','tp'):
        files=[p for p in input_paths() if p.name.startswith('r01_rig' if kind=='fp' else 'r01_tp')]
        for path in files:
            model=Studio(path);inputs[str(path)]=digest(path)
            for crouch in ((False,True) if kind=='tp' else (False,)):
                key=path.stem+('_crouch' if crouch else '')
                idle=sequence_frames(model,'ref_aim_mp5' if kind=='tp' else 'idle')[0].copy()
                if crouch:
                    # Gameplay keeps ref_aim_mp5 above the spine and overlays
                    # crouch_idle on the legs/pelvis. Author that same composite
                    # instead of the donor crouch_aim track's bent upper body.
                    gait=sequence_frames(model,'crouch_idle')[0]
                    spine=model.names.index('Bip01 Spine');idle[:spine]=gait[:spine]
                rig=dict(key=key,kind=kind,crouch=crouch,source=str(path),names=model.names,parents=model.parents,
                    bind=np.array(model.bind).tolist(),idle=idle.tolist(),meshes=[])
                if kind=='fp':
                    for name in ('inspect_gloves','inspect_sleeves'):
                        mesh_source=source('vf_inspect',name+'.mdl');inputs[str(mesh_source)]=digest(mesh_source)
                        rig['meshes'].append(mesh_data(mesh_source,model))
                    gun,feed=40,41;scale=1
                else:
                    mesh_source=source('vf_skins','persona_scout.mdl');inputs[str(mesh_source)]=digest(mesh_source)
                    rig['meshes'].append(mesh_data(mesh_source,model));gun,feed=28,29;scale=.68
                for name in ('r01_receiver_m40','r01_barrel_a','r01_muzzle_a','r01_feed_a','r01_chamber_a','r01_ammo_a',
                             'r01_projectile_a','r01_optic_a','r01_underbarrel_a' if '_fg' in key else 'r01_underbarrel_b',
                             'r01_grip_a','r01_power_a','r01_cooling_a'):
                    mesh_source=source('vf_r01',name+'.mdl');inputs[str(mesh_source)]=digest(mesh_source)
                    rig['meshes'].append(mesh_data(mesh_source,model,feed if name.startswith('r01_feed') else gun,scale))
                rigs.append(rig)
    assert len(rigs)==12
    (WORK/'input.json').write_text(json.dumps(dict(rigs=rigs,inputs=inputs)))
    return inputs

def append_tracks(model,tracks):
    """Keep every existing sequence/event/blend, and rescale old RLE if needed."""
    data=bytearray(model.data);count,boneoff=struct.unpack_from('<ii',data,140)
    original_count,original_off=struct.unpack_from('<ii',data,164)
    old_scales=np.array([struct.unpack_from('<6f',data,boneoff+i*112+88) for i in range(count)])
    defaults=np.array([struct.unpack_from('<6f',data,boneoff+i*112+64) for i in range(count)])
    deltas=[]
    for _,frames in tracks:
        angles=Rotation.from_matrix(frames[:,:,:3,:3].reshape(-1,3,3)).as_euler('xyz').reshape(len(frames),count,3)
        angles+=np.round((defaults[None,:,3:]-angles)/(2*np.pi))*2*np.pi
        deltas.append(np.concatenate((frames[:,:,:3,3],angles),axis=2)-defaults)
    scales=np.maximum(old_scales,np.maximum.reduce([np.abs(delta).max(axis=0)/30000 for delta in deltas]))
    visited={}
    for index in range(original_count):
        info=sequence_info(model,index);assert info['group']==0
        for blend in range(info['blends']):
            for bone in range(count):
                header=info['animation']+(blend*count+bone)*12
                for axis,offset in enumerate(struct.unpack_from('<6H',model.data,header)):
                    if not offset or scales[bone,axis]==old_scales[bone,axis]:continue
                    start=header+offset;ratio=old_scales[bone,axis]/scales[bone,axis]
                    if start in visited:assert abs(visited[start]-ratio)<1e-9;continue
                    visited[start]=ratio;frame=0
                    while frame<info['frames']:
                        valid,total=struct.unpack_from('<BB',model.data,start);assert 0<valid<=total
                        for v in range(valid):
                            old=struct.unpack_from('<h',model.data,start+2+2*v)[0]
                            struct.pack_into('<h',data,start+2+2*v,int(round(old*ratio)))
                        start+=2+2*valid;frame+=total
    for bone in range(count):struct.pack_into('<6f',data,boneoff+112*bone+88,*scales[bone])
    while len(data)%4:data.append(0)
    seqoff=len(data);data.extend(model.data[original_off:original_off+176*original_count]);data.extend(bytes(176*len(tracks)))
    for index,((name,frames),delta) in enumerate(zip(tracks,deltas)):
        entry=seqoff+176*(original_count+index)
        descriptor=bytearray(model.data[original_off:original_off+176]);descriptor[:32]=name.encode().ljust(32,b'\0')
        struct.pack_into('<f',descriptor,32,30);struct.pack_into('<5i',descriptor,36,0,0,0,0,0)
        struct.pack_into('<i',descriptor,56,len(frames));struct.pack_into('<i',descriptor,120,1);struct.pack_into('<i',descriptor,156,0)
        struct.pack_into('<6f',descriptor,96,-70,-70,-48,70,70,70)
        animoff=len(data);struct.pack_into('<i',descriptor,124,animoff);data[entry:entry+176]=descriptor
        data.extend(bytes(count*12));quantized=np.round(delta/scales).astype('<i2')
        for bone in range(count):
            header=animoff+bone*12
            for axis in range(6):
                values=quantized[:,bone,axis]
                if not values.any():continue
                struct.pack_into('<H',data,header+axis*2,len(data)-header)
                data.extend(bytes([len(frames),len(frames)]));data.extend(values.tobytes())
    struct.pack_into('<ii',data,164,original_count+len(tracks),seqoff);struct.pack_into('<i',data,72,len(data))
    return bytes(data)

def compile_assets():
    payload=json.loads((WORK/'input.json').read_text());assert all(digest(path)==sha for path,sha in payload['inputs'].items())
    records=[]
    for rig_source in sorted({rig['source'] for rig in payload['rigs']}):
        model=Studio(rig_source);stem=Path(rig_source).stem;tracks=[]
        for key,name in ((stem,'vf_melee'),(stem+'_crouch','vf_melee_crouch')):
            path=WORK/(key+'.npy')
            if any(rig['key']==key for rig in payload['rigs']):tracks.append((name,np.load(path)))
        target=OUT/Path(rig_source).name;target.write_bytes(append_tracks(model,tracks));compiled=Studio(target)
        assert compiled.names==model.names and compiled.parents==model.parents
        assert compiled.sequences[:len(model.sequences)]==model.sequences
        error=0
        for index in range(len(model.sequences)):
            info=sequence_info(model,index)
            for blend in range(info['blends']):
                before=sequence_frames(model,index,blend=blend);after=sequence_frames(compiled,index,blend=blend)
                error=max(error,float(np.max(np.abs(before-after))))
        assert error<.001,(target,error)
        authored_error=0
        for name,frames in tracks:
            after=sequence_frames(compiled,name)
            a=np.array([globals_of(f,model.parents) for f in frames]);b=np.array([globals_of(f,model.parents) for f in after])
            authored_error=max(authored_error,float(np.abs(a-b).max()))
        assert authored_error<.02,(target,authored_error)
        records.append(dict(file=target.name,source=rig_source,source_sha256=digest(rig_source),sha256=digest(target),
            added=[name for name,_ in tracks],old_sequences_preserved=len(model.sequences),old_animation_error=error,compiled_error=authored_error))
    for name in ('gloves','sleeves'):
        mesh_source=source('vf_inspect','inspect_'+name+'.mdl');target=OUT/('melee_'+name+'.mdl');target.write_bytes(mesh_source.read_bytes())
    (OUT/'manifest.json').write_text(json.dumps(dict(models=records,inputs=payload['inputs'],duration=1.1,impact=13/30,
        gesture='right-handed overhead barrel strike; left hand released through follow-through',
        authoring='Explicit Blender finger/knuckle/thumb poses, staggered closure, neutral wrist and guard keyframes',blend_file=str(WORK/'Frappe-au-canon-R1-poing.blend')),indent=2))
    print('PASS nine independent melee carriers; all original sequences, blends and events preserved',flush=True)

def build(ensure=False):
    manifest=OUT/'manifest.json'
    if ensure and manifest.exists() and (WORK/'Frappe-au-canon-R1-poing.blend').exists():
        old=json.loads(manifest.read_text());current={str(p):digest(p) for p in input_paths()}
        # Installed/generated copies may have different paths and identical bytes.
        same=sorted((Path(k).name,v) for k,v in old['inputs'].items())==sorted((Path(k).name,v) for k,v in current.items())
        ready=len(old['models'])==9 and all((OUT/r['file']).exists() and digest(OUT/r['file'])==r['sha256'] for r in old['models'])
        ready=ready and all(digest(OUT/('melee_'+n+'.mdl'))==digest(source('vf_inspect','inspect_'+n+'.mdl')) for n in ('gloves','sleeves'))
        if same and ready:print('PASS authored melee assets current; no regeneration');return
    prepare()
    success=WORK/'blender-export.json'
    if success.exists():success.unlink()
    install=json.loads((PROJECT/'devtools/blender/installation.json').read_text())
    command=[install['executable'],'--background','--factory-startup','--python',str(WORK/'author_melee.py')]
    with (REVIEW/'blender.log').open('w') as log:
        result=subprocess.run(command,cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode or not success.exists():raise RuntimeError((REVIEW/'blender.log').read_text(errors='replace')[-8000:])
    compile_assets()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compile-only',action='store_true');p.add_argument('--source-generated',action='store_true');p.add_argument('--ensure',action='store_true');args=p.parse_args()
    SOURCE_GENERATED=args.source_generated
    compile_assets() if args.compile_only else build(args.ensure)

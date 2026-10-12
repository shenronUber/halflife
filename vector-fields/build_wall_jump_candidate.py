"""Append only the new Blender tracks to private copies of current carriers.

Checks every previous compiled track, preserving concurrent authoring output.
"""
import hashlib,json,re,shutil,os
from pathlib import Path
import numpy as np
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info
from traversal_editor import read,override
from third_person import smd
from build_modular import compile_model
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'build/wall-jump'
GESTURES=('vf_wall_jump','vf_wall_jump_turn')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build():
    from third_person import Author,RECIPE
    from traversal_animations import tp_pose
    from build_traversal import pose
    author=Author(json.loads(RECIPE.read_text()))
    records=[];runtime=ROOT.parent/'runtime/vector-engine/vf_visual'
    for view,folder,target,models in [
        ('first-person','traversal','vf_traversal',[p.stem for p in sorted((ROOT/'generated/traversal').glob('r01*_tr.mdl'))]),
        ('third-person','third-person','vf_r01',[p.stem for p in sorted((ROOT/'generated/third-person').glob('r01_tp*.mdl'))])]:
        source=ROOT/'generated'/folder;dest=OUT/'generated'/folder;dest.mkdir(parents=True,exist_ok=True)
        for p in source.glob('*.smd'):shutil.copy2(p,dest/p.name)
        for model in models:
            old=Studio(source/(model+'.mdl'))
            if view=='first-person':
                from traversal_hands import extend
                rig=extend(Studio(ROOT/'generated/r01'/(model.replace('_tr','')+'.mdl')))
            installed=runtime/'models'/target/(model+'.mdl')
            if sha(installed)!=sha(old.path):raise RuntimeError('Generated/installed model mismatch: '+model)
            if all(g in old.sequences for g in GESTURES):
                # A concurrent full build may already have consumed our SMD
                # overrides. Reuse that complete model, including its latest
                # meshes and every other agent's animation tracks.
                compiled_path=dest/old.path.name;shutil.copy2(old.path,compiled_path)
                records.append(dict(model=model,view=view,relative='models/'+target+'/'+model+'.mdl',
                    source_sha256=sha(old.path),runtime_sha256=sha(installed),candidate=str(compiled_path),sha256=sha(compiled_path),
                    preserved_tracks=sum(sequence_info(old,n)['blends']for n in old.sequences if n not in GESTURES),
                    max_preserved_error=0,gestures=list(GESTURES),reused_concurrent_build=True))
                print('PASS reused current complete carrier',model,flush=True);continue
            if any(g in old.sequences for g in GESTURES):raise RuntimeError('Partial wall-jump integration: '+model)
            qc=(source/(model+'.qc')).read_text()
            # Dependencies stay read-only in their current generated folders.
            fp=Path(os.path.relpath(ROOT/'generated/r01',dest)).as_posix()
            tp=Path(os.path.relpath(ROOT/'generated/personas',dest)).as_posix()
            qc=qc.replace('"../r01/', '"'+fp+'/')
            qc=qc.replace('"../personas/', '"'+tp+'/')
            qc=qc.replace('$cdtexture "../r01"','$cdtexture "'+fp+'"')
            qc=qc.replace('$cdtexture "../personas"','$cdtexture "'+tp+'"')
            for g in GESTURES:
                frames=read(ROOT/'assets/animations/traversal-edits'/view/(g+'_0.smd'),old)
                if view=='first-person':default=np.array([pose(rig,g,t)for t in np.linspace(0,1,len(frames))])
                else:
                    platform='side'if model.endswith('_side')else'top'if model.endswith('_top')else'bottom'
                    default=np.array([tp_pose(author,platform,g,t)for t in np.linspace(0,1,len(frames))])
                frames=override(rig if view=='first-person'else old,default,view,g,0)
                if view=='first-person':frames=frames[:,[rig.names.index(n)for n in old.names]]
                key=model+'_'+g;smd(old,frames,dest/(key+'.smd'))
                qc+='\n$sequence "'+g+'" "'+key+'" fps '+str((len(frames)-1)/.65)+'\n'
            path=dest/(model+'.qc');path.write_text(qc,encoding='ascii')
            compiled=Studio(compile_model(path))
            assert compiled.names==old.names and compiled.parents==old.parents
            assert compiled.sequences==old.sequences+list(GESTURES)
            error=0.;preserved=0
            for name in old.sequences:
                info=sequence_info(old,name)
                for bi in range(info['blends']):
                    a=sequence_frames(old,name,blend=bi);b=sequence_frames(compiled,name,blend=bi)
                    assert a.shape==b.shape,(model,name)
                    error=max(error,float(np.max(np.abs(a-b))));preserved+=1
            assert error<.001,(model,error)
            relative='models/'+target+'/'+model+'.mdl'
            records.append(dict(model=model,view=view,relative=relative,source_sha256=sha(old.path),
                runtime_sha256=sha(installed),candidate=str(compiled.path),sha256=sha(compiled.path),
                preserved_tracks=preserved,max_preserved_error=error,gestures=list(GESTURES)))
            print('PASS candidate',model,'preserved',preserved,'error',error,flush=True)
    (OUT/'assets.json').write_text(json.dumps(records,indent=2))
    return records

if __name__=='__main__':build()

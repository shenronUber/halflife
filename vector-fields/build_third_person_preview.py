"""Compile four CS reloads on the current carrier, as an isolated preview model."""
import hashlib,json,re
from pathlib import Path
import numpy as np
from studio_assets import Studio
from build_personas import donor,ASSETS
from inspect_animations import TP,OUT,retarget,smd_motion
from animation_assets import sequence_info,sequence_frames,globals_of
from build_modular import compile_model


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    source=Studio(donor(json.loads((ASSETS/'personas.json').read_text()))['path'])
    target=Studio(TP/'persona_rig.mdl')
    names=['ref_reload_mp5','crouch_reload_mp5','ref_reload_rifle','crouch_reload_rifle']
    authored={}
    for name in names:
        authored[name]=retarget(source,target,name)
        smd_motion(target,name,authored[name])
    qc=(TP/'persona_rig.qc').read_text()
    qc=qc.replace('"persona_rig.mdl"','"persona_rig_cs_preview.mdl"')
    qc=qc.replace('$cdtexture "./"',f'$cdtexture "{TP.as_posix()}"')
    for path in TP.glob('*.smd'):
        qc=qc.replace('"'+path.stem+'"', '"'+path.with_suffix('').as_posix()+'"') if path.stem in ('persona_body','persona_anchors') else qc
    rows=[]
    for line in qc.splitlines():
        match=re.fullmatch(r'(\s*)"([^"\n]+)"\s*',line)
        if match and (TP/(match[2]+'.smd')).exists():
            line=match[1]+'"'+(TP/match[2]).as_posix()+'"'
        rows.append(line)
    qc='\n'.join(rows)+'\n'
    for name in names:
        qc+=f'$sequence "{name}" {{\n "{name}"\n fps {sequence_info(source,name)["fps"]}\n}}\n'
    qc=qc.replace(TP.as_posix(),'../personas')
    path=OUT/'persona_rig_cs_preview.qc';path.write_text(qc,encoding='ascii')
    model=Studio(compile_model(path))
    assert model.sequences[:len(target.sequences)]==target.sequences
    assert model.names==target.names
    assert len(model.sequences)==len(target.sequences)+4
    errors={}
    for name in names:
        compiled=sequence_frames(model,name)
        actual=np.array([globals_of(f,model.parents) for f in compiled])
        expected=np.array([globals_of(f,target.parents) for f in authored[name]])
        error=float(np.max(np.abs(actual-expected)));assert error<.025,(name,error)
        errors[name]=error
    info=dict(source=str(source.path),source_sha256=hashlib.sha256(source.data).hexdigest(),
        output=str(model.path),sha256=hashlib.sha256(model.data).hexdigest(),
        bones=len(model.names),old_sequences_preserved=len(target.sequences),added_sequences=names,max_global_transform_errors=errors,
        status='offline preview only; no runtime deployment',
        sources={'motion':'Installed Counter-Strike GIGN model','code_reference':'https://github.com/rehlds/ReGameDLL_CS/blob/master/regamedll/dlls/player.cpp'})
    (OUT/'third-person-preview.json').write_text(json.dumps(info,indent=2))
    print('PASS CS reload preview',json.dumps(info))


if __name__=='__main__':build()

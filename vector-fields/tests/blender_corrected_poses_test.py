"""Validate the reviewed hand exports through the actual GoldSrc compiler."""
import json
from pathlib import Path
import shutil
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from traversal_editor import read
from animation_assets import sequence_frames
from build_modular import compile_model


def main():
    base=ROOT/'animation-workshop/traversal'
    report_path=Path(sys.argv[1]) if len(sys.argv)>1 else base/'blender/verification/postures/corrections.json'
    verification=report_path.parent
    report=json.loads(report_path.read_text())
    exports=Path(report['export_directory'])
    view=report.get('view','first-person')
    original=Studio(ROOT/('generated/traversal/r01_rig_tr.mdl' if view=='first-person' else 'generated/third-person/r01_tp.mdl'))
    folder=base/view
    target=verification/('compile-'+view);target.mkdir(parents=True,exist_ok=True)
    for name in ('reference.smd','skeleton_keep.smd'):
        shutil.copy2(folder/name,target/name)
    qc_lines=['$modelname "postures.mdl"','$cd "."',f'$cdtexture "{folder.as_posix()}"',
        '$body mesh "reference"','$bodygroup keep_bones {',' blank',' studio "skeleton_keep"','}']
    inputs={}
    for key in report['gestures']:
        path=exports/(key+'.smd')
        frames=read(path,original)
        inputs[key]=frames
        assert np.isfinite(frames).all(),key
        shutil.copy2(path,target/path.name)
        loop=key.startswith(('vf_hang_both_','vf_hang_aim_')) or key in ('vf_hang_idle_0','vf_slide_loop_0')
        if loop:
            assert np.max(np.abs(frames[0]-frames[-1]))<.005,(key,'loop seam')
        qc_lines.append(f'$sequence "{key}" "{key}" fps 30'+(' loop' if loop else ''))
    qc=target/'postures.qc';qc.write_text('\n'.join(qc_lines)+'\n',encoding='ascii')
    compiled=Studio(compile_model(qc))
    assert set(compiled.names)==set(original.names)
    for i,n in enumerate(original.names):
        p=original.parents[i]
        if p>=0:
            assert compiled.names[compiled.parents[compiled.names.index(n)]]==original.names[p]
    errors={}
    for key,expected in inputs.items():
        actual=sequence_frames(compiled,key)
        reordered=np.array([[frame[compiled.names.index(n)] for n in original.names]for frame in actual])
        if key.startswith(('vf_hang_both_','vf_hang_aim_')) or key in ('vf_hang_idle_0','vf_slide_loop_0'):
            expected=expected.copy();expected[-1]=expected[0]
        error=float(np.max(np.abs(reordered-expected)))
        assert error<.01,(key,error)
        errors[key]=error
    result=dict(gestures=len(inputs),frames=sum(len(f) for f in inputs.values()),bones=len(compiled.names),
        max_matrix_error_after_goldsrc_compile=max(errors.values()),loop_seams_checked=True,
        skeleton_hierarchy_preserved=True,game_files_deployed=False)
    (verification/('game-validation-'+view+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS',json.dumps(result))


if __name__=='__main__':main()

"""Validate Blender-exported test tracks with the game importer and GoldSrc compiler."""
from pathlib import Path
import json
import shutil
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_modular import compile_model
from studio_assets import Studio
from traversal_editor import read
from animation_assets import sequence_frames


def main():
    verification=ROOT/'animation-workshop/traversal/blender/verification'
    out=verification/'compile';out.mkdir(parents=True,exist_ok=True)
    imports={};compiles={}
    for view,asset in [('first-person','generated/traversal/r01_rig_tr.mdl'),
                       ('third-person','generated/third-person/r01_tp.mdl')]:
        original=Studio(ROOT/asset);default=sequence_frames(original,'vf_hang_idle')
        files=[view+'-baseline.smd']+(['first-person-edited.smd'] if view=='first-person' else [])
        for file in files:
            frames=read(verification/file,original)
            error=float(np.max(np.abs(np.linalg.norm(frames[:,1:,:3,3],axis=-1)-np.linalg.norm(default[:,1:,:3,3],axis=-1))))
            assert error<.15,(file,error)
            imports[file]=dict(frames=len(frames),bone_count=len(original.names),length_error=error)
        folder=ROOT/'animation-workshop/traversal'/view
        for name in ['reference.smd','skeleton_keep.smd']:
            shutil.copy2(folder/name,out/(view+'-'+name))
        animation=view+'-'+('edited' if view=='first-person' else 'baseline')
        shutil.copy2(verification/(animation+'.smd'),out/(animation+'.smd'))
        qc=out/(view+'.qc')
        qc.write_text('$modelname "'+view+'.mdl"\n$cd "."\n$cdtexture "'+folder.as_posix()+'"\n'
                      '$body mesh "'+view+'-reference"\n$bodygroup keep_bones {\n blank\n studio "'+view+'-skeleton_keep"\n}\n'
                      '$sequence vf_hang_idle "'+animation+'" fps 30 loop\n',encoding='ascii')
        model=Studio(compile_model(qc))
        assert set(model.names)==set(original.names)
        actual=sequence_frames(model,'vf_hang_idle');expected=read(out/(animation+'.smd'),original)
        # GoldSrc enforces loop closure by copying the first pose to the last.
        expected[-1]=expected[0]
        reordered=np.array([[frame[model.names.index(n)]for n in original.names]for frame in actual])
        error=float(np.max(np.abs(reordered-expected)))
        assert error<.01,(view,error)
        compiles[view]=dict(bones=len(model.names),frames=len(actual),matrix_error_after_goldsrc_compile=error,loop_closed=True)
    (verification/'game-import.json').write_text(json.dumps(imports,indent=2))
    (verification/'compile-results.json').write_text(json.dumps(compiles,indent=2))
    print('PASS game importer and GoldSrc compiler',json.dumps(compiles))


if __name__=='__main__':
    main()

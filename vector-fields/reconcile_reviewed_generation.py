"""Retain reviewed models while updating their verified authoring/cache state."""
import json,shutil
from pathlib import Path
import build_cache,third_person,build_traversal,build_traversal_body
from build_weapon_melee import ROOT,digest
from external_traversal_animations import inputs as source_inputs
from traversal_editor import inputs as edit_inputs
OUT=ROOT/'build/completion-audit'

def reconcile():
    equivalent=json.loads((OUT/'repaired-regeneration-diff.json').read_text());assert equivalent['passed']
    fp=json.loads((OUT/'fp-regeneration-diff.json').read_text());assert len(fp)==9 and all(r['identical']for r in fp)
    for group,source in [('third-person',OUT/'rebuilt-third-person'),('traversal',OUT/'rebuilt-traversal')]:
        target=ROOT/'generated'/group
        for p in source.iterdir():
            if p.suffix not in('.qc','.smd'):continue
            if(target/p.name).exists()and digest(p)==digest(target/p.name):continue
            saved=OUT/'generation-backup'/group/p.name;saved.parent.mkdir(parents=True,exist_ok=True)
            if(target/p.name).exists()and not saved.exists():shutil.copy2(target/p.name,saved)
            shutil.copy2(p,target/p.name)
    # Source poses now include the installed transition fixes. Published
    # compressed models stay byte-identical; cold builds differ by at most
    # one Studio position quantum, as proven by the comparison above.
    path=third_person.OUT/'manifest.json';state=build_cache.read(path)
    saved=OUT/'generation-backup/third-person/manifest.json';saved.parent.mkdir(parents=True,exist_ok=True)
    if not saved.exists():shutil.copy2(path,saved)
    outputs=[p for p in third_person.OUT.iterdir()if p.suffix in('.mdl','.qc','.smd')]+[ROOT.parent/'cl_dll/vf_third_person_scale.h']
    identity=build_cache.fingerprint(third_person.input_paths())
    state['inputs_sha256']=identity;state['build_cache']=build_cache.record(identity,outputs)
    state['reviewed_generation_equivalence']=equivalent
    state['published_models_retained']=True
    for r in state['models']:r['sha256']=digest(r['path'])
    build_cache.write(path,state)
    paths=source_inputs()+edit_inputs('first-person')+[Path(build_traversal.__file__),ROOT/'traversal_vault.py',ROOT/'traversal_animations.py',ROOT/'traversal_aim.py',ROOT/'third_person.py',ROOT/'animation_assets.py',ROOT/'build_reference_platforms.py',ROOT/'traversal_hands.py']+list(build_traversal.SOURCE.glob('*.mdl'))+list(build_traversal.SOURCE.glob('*.qc'))+build_cache.compiler_inputs()
    path=build_traversal.OUT/'manifest.json';state=build_cache.read(path)
    saved=OUT/'generation-backup/traversal/manifest.json';saved.parent.mkdir(parents=True,exist_ok=True)
    if not saved.exists():shutil.copy2(path,saved)
    identity=build_cache.fingerprint(paths)
    state['build_cache']=build_cache.record(identity,[Path(p)for p in state['build_cache']['outputs']])
    state['reviewed_generation_equivalence']=dict(passed=True,models=fp)
    build_cache.write(path,state)
    paths=[ROOT/'traversal_hands.py',Path(build_traversal_body.__file__),ROOT/'traversal_animations.py',ROOT/'traversal_aim.py',ROOT/'third_person.py',ROOT/'animation_assets.py',ROOT/'generated/personas/persona_scout.mdl',ROOT/'generated/personas/persona_rig.mdl',ROOT/'generated/r01/r01_rig.mdl',ROOT/'generated/r01/r01_fp_gloves.mdl',ROOT/'generated/r01/r01_fp_gloves.qc',ROOT/'generated/r01/r01_fp_sleeves.mdl',ROOT/'generated/r01/r01_fp_sleeves.qc']+list((ROOT/'generated/r01').glob('fp_gloves_*.bmp'))+list((ROOT/'generated/r01').glob('fp_sleeves_*.bmp'))+build_cache.compiler_inputs()
    path=build_traversal_body.OUT/'body_manifest.json';state=build_cache.read(path)
    saved=OUT/'generation-backup/traversal/body_manifest.json'
    if not saved.exists():shutil.copy2(path,saved)
    state['build_cache']=build_cache.record(build_cache.fingerprint(paths),[Path(p)for p in state['build_cache']['outputs']])
    state['reviewed_generation_equivalence']=dict(passed=True,models=[r for r in fp if r['model']in('ledge_gloves.mdl','ledge_sleeves.mdl','slide_legs.mdl')])
    build_cache.write(path,state)
    print('PASS reviewed TP and FP generation caches reconciled without changing published models',flush=True)
if __name__=='__main__':reconcile()

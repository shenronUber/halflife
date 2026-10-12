"""Install the reviewed clips and renderer, preserving the existing engine core."""
import hashlib,json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release import deployment_files,verify_deployment,check_native_interface
from studio_assets import Studio

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 out=ROOT/'docs/validation/traversal/posture-review';proof=json.loads((out/'capture.json').read_text())
 assert proof['posture'] and proof['frames']==785 and Path(proof['video']).is_file()
 assert len(proof['timeline'])==11
 combat=json.loads((out.parent/'slide-combat/capture.json').read_text())
 assert combat['combat'] and combat['frames']==440
 for field in ('client_sha256','server_sha256','renderer_sha256','engine_core','assets'):
  assert combat[field]==proof[field],('Combat review differs from posture review',field)
 for event in proof['timeline']:
  if event['gesture']in('vault','stepup'):assert event['planted_palm_error']<.001
  if event['gesture']=='crouch':assert event['shots']>=4 and event['reload_started'] and event['minimum_aim_alignment']>.9999
 assets=json.loads((out/'compiled-assets.json').read_text());assert assets['skin_families']==23 and assets['preserved_tracks']>=1000
 checks=re.search(r'Traversal movement: (\d+) checks, 0 failures',(ROOT/'build/policy-tests/traversal/result.log').read_text());assert checks
 engine=ROOT.parent/'runtime/vector-engine';destination=engine/'vf_visual';candidate_dir=ROOT/'build/engine-candidate'
 candidate=json.loads((candidate_dir/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
 assert candidate['body_renderer_version']==1
 if candidate.get('extension_version')==4:
  assert candidate.get('headgear_verified'),'Concurrent helmet renderer must pass its own validation before integration'
 for source,field in [(ROOT/'engine/gl_vf.inc','renderer_source_sha256'),(ROOT/'engine/first-person-body.patch','body_patch_sha256'),(ROOT.parent/'network/delta.lst','delta_sha256')]:
  assert digest(source)==proof[field],('Source changed after review',source)
 for name,sha in proof['source_hashes'].items():assert digest(ROOT.parent/name)==sha,('Renderer input changed after review',name)
 assert candidate['renderer_sha256'].lower()==proof['renderer_source_sha256']
 assert candidate['body_patch_sha256'].lower()==proof['body_patch_sha256']
 metadata=json.loads((engine/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
 core_changes=[]
 for name,sha in proof['engine_core'].items():
  if digest(engine/name)==sha:continue
  # ABI 4 changes the renderer bridge in xash.dll. Keep the other installed
  # core binaries; upgrade that bridge only to the binary actually filmed.
  assert name=='xash.dll' and metadata['extension_version']!=candidate['extension_version'],('Unexpected engine core drift',name)
  assert digest(candidate_dir/name)==sha,('Engine bridge changed after review',name)
  core_changes.append((candidate_dir/name,engine/name,sha))
 allowed={Path('cl_dlls/client.dll'),Path('dlls/hl.dll'),Path('delta.lst')}
 allowed|={Path('vf/equipment.txt'),Path('models/vf_headgear/headgear.mdl')}
 allowed|={Path('models/vf_r01')/(n+'.mdl')for n in('r01_tp','r01_tp_side','r01_tp_top')}
 allowed|={Path('models/vf_traversal')/(n+'.mdl')for n in('r01_rig_tr','r01_rig_side_tr','r01_rig_top_tr','r01_rig_fg_tr','r01_rig_side_fg_tr','r01_rig_top_fg_tr','slide_legs')}
 expected={Path(k):v for k,v in proof['assets'].items()}|{Path('cl_dlls/client.dll'):proof['client_sha256'],Path('dlls/hl.dll'):proof['server_sha256'],Path('delta.lst'):proof['delta_sha256']}
 # The later assembly probe includes the concurrent helmet model and checks
 # an equipped helmet, its action and both traversal contacts. Earlier videos
 # keep their original asset manifest rather than claiming to include it.
 integration=json.loads((out.parent/'body-probe/bundle.json').read_text())
 assert integration['bundle_checked']
 for field in ('client_sha256','server_sha256','renderer_sha256'):assert integration[field]==proof[field],('Assembly probe differs from footage',field)
 for name,sha in integration['assets'].items():
  target=Path(name)
  if target in expected:assert expected[target]==sha,('Assembly asset differs',name)
  else:assert target==Path('models/vf_headgear/headgear.mdl'),('Unexpected additional asset',name)
  expected[target]=sha
 candidates=[]
 for source,target in deployment_files():
  if target in expected:assert digest(source)==expected[target],('Asset changed after review',target)
  if (destination/target).exists() and digest(source)==digest(destination/target):continue
  assert target in allowed,('Unrelated deployment drift',target)
  candidates.append((source,destination/target,expected[target]))
 for field in('extension_version','headgear_renderer_version','traversal_renderer_version','status_viewmodel_version','body_renderer_version','body_patch_sha256','patch_sha256','built_utc','renderer_sha256'):
  metadata[field]=candidate[field]
 for name,sha in proof['engine_core'].items():metadata['binaries'][name]=sha.upper()
 metadata['binaries']['ref_gl.dll']=proof['renderer_sha256'].upper()
 metadata['body_verified']=True;metadata['posture_validation']='vector-fields/docs/validation/traversal/posture-review/capture.json'
 metadata['slide_combat_verified']=True;metadata['slide_combat_validation']='vector-fields/docs/validation/traversal/slide-combat/capture.json'
 if candidate.get('headgear_verified'):
  metadata['headgear_verified']=True
  metadata['headgear_validation']=candidate['headgear_validation']
  metadata['headgear_source_sha256']=candidate['headgear_source_sha256']
 staged=out/'engine-build.json';staged.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
 candidates.extend(core_changes+[(candidate_dir/'ref_gl.dll',engine/'ref_gl.dll',proof['renderer_sha256']),(staged,engine/'vector-engine-build.json',digest(staged))])
 before=out.parent/'posture-review-before';changes=[]
 for source,target,expected_sha in candidates:
  assert digest(source)==expected_sha,source
  if target.exists() and digest(target)==expected_sha:continue
  with target.open('r+b'):pass
  old=before/target.relative_to(engine);old.parent.mkdir(parents=True,exist_ok=True)
  if old.exists():assert digest(old)==digest(target),('Backup conflict',target)
  else:shutil.copy2(target,old)
  pending=target.with_name(target.name+'.posture-review');shutil.copy2(source,pending)
  assert digest(pending)==expected_sha;changes.append((target,pending,old,expected_sha))
 replaced=[]
 try:
  for target,pending,old,expected_sha in changes:
   os.replace(pending,target);replaced.append((target,old));assert digest(target)==expected_sha
  check_native_interface(engine,destination/'cl_dlls/client.dll');deployment=verify_deployment(destination)
 except Exception:
  for target,old in reversed(replaced):shutil.copy2(old,target)
  raise
 report=dict(files={str(t.relative_to(engine)):sha for t,_,_,sha in changes},deployment=deployment,movement_checks=int(checks[1]),skin_families=23,video=proof['video'],engine_core_preserved=not core_changes,engine_bridge_upgraded=bool(core_changes))
 (out/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS installed posture review',len(changes),'files;',deployment)

if __name__=='__main__':main()

"""Seed ignored local dependencies into this checkout without sharing writes."""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vector-fields'))
from native_workspace import copy_resources,private_copy
def run(seed):
 seed=Path(seed).resolve()
 if seed==ROOT:raise ValueError('Run the copy inside the new worktree, with the original project as --seed.')
 receipt=seed/'runtime/vector-engine/vf_visual/vf/release-bundle.json'
 state=json.loads(receipt.read_text());assert state['passed'],'Seed must contain a validated main release'
 copied=[]
 for relative in ['vector-fields/generated','weapon-lab/generated','weapon-lab/extracted','asset-probe/tools','asset-probe/sdhlt','devtools/SDL2-sdk']:
  source=seed/relative;target=ROOT/relative
  if source.is_dir():
   copy_resources(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.log','*.obj','*.pdb','*.ilk'))
   copied.append(relative)
 # Engine sources are mutable and must never share hardlinks across branches.
 if(seed/'runtime/engine-source').exists():
  shutil.copytree(seed/'runtime/engine-source',ROOT/'runtime/engine-source',dirs_exist_ok=True,
                  ignore=shutil.ignore_patterns('.git','build','build-*','__pycache__','*.obj','*.pdb'))
 # Only the active release and fallback libraries, never old release backups,
 # experiments, native test sessions or the user's save files.
 engine=ROOT/'runtime/vector-engine';engine.mkdir(parents=True,exist_ok=True)
 for p in(seed/'runtime/vector-engine').iterdir():
  if p.is_file()and(p.suffix in('.dll','.exe')or p.name=='vector-engine-build.json'):private_copy(p,engine/p.name)
 for name in('vf_visual','valve','tfc_assets','cs_assets'):
  source=seed/'runtime/vector-engine'/name
  if source.exists():copy_resources(source,engine/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('save','scrshots','*.log','release-bundle.json','config.cfg'))
 for name in('client/client.dll','server/hl.dll'):
  source=seed/'vector-fields/build'/name;target=ROOT/'vector-fields/build'/name
  target.parent.mkdir(parents=True,exist_ok=True);private_copy(source,target)
 for relative in ['asset-probe/generate_assets.py']:
  source=seed/relative;target=ROOT/relative
  if source.exists()and not target.exists():target.parent.mkdir(parents=True,exist_ok=True);private_copy(source,target)
 for name,value in state['files'].items():
  if Path(name).parts[0]!='vf_visual':continue
  p=engine/name
  assert p.is_file()and hashlib.sha256(p.read_bytes()).hexdigest()==value,('Seed copy differs',name)
 record=dict(seed=str(seed),destination=str(ROOT),seed_release=state['id'],source_identity=state['source_identity'],copied=copied,first_launch='python vector-fields/build_release.py',immutable_media='Independent content-hash cache; mutable files are private copies.')
 out=ROOT/'vector-fields/build/bootstrap.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(record,indent=2))
 print('Local dependencies copied and verified. Build this worktree before its first launch.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seed',type=Path,required=True);run(p.parse_args().seed)

"""Bound generated release history; preserve authorship, saves and diagnostics."""
import argparse,json,re,shutil
from pathlib import Path
from native_workspace import checked_child,remove_tree,file_lock,EVIDENCE,compact_captures
ROOT=Path(__file__).resolve().parent
ID=re.compile(r'^\d{8}-\d{6}-[0-9a-f]{8}$')
BACKUP=re.compile(r'^\.vf_visual-before-[0-9a-f]{10}$')
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def plan(releases,live):
 releases=Path(releases);live=Path(live);receipt=live/'vf_visual/vf/release-bundle.json'
 if not receipt.is_file():raise RuntimeError('Retention requires an installed release receipt.')
 state=read(receipt)
 if not state.get('passed'):raise RuntimeError('Do not prune while the installed release is unvalidated.')
 current=Path(state['candidate']).resolve();checked_child(current,releases)
 candidates=[]
 for p in releases.iterdir():
  if p.is_dir()and ID.fullmatch(p.name)and(p/'source-inputs.json').is_file():
   checked_child(p,releases)
   candidates.append(p)
 passed=sorted((p for p in candidates if(p/'bundle.json').is_file()and read(p/'bundle.json').get('passed')and p.resolve()!=current),key=lambda p:p.name,reverse=True)
 keep={current}|{p.resolve()for p in passed[:1]}
 backups=sorted((p for p in live.iterdir()if p.is_dir()and BACKUP.fullmatch(p.name)and(p/'gameinfo.txt').is_file()),key=lambda p:p.stat().st_mtime_ns,reverse=True)
 for p in backups:checked_child(p,live)
 return dict(keep=sorted(str(p)for p in keep),remove_candidates=[str(p)for p in candidates if p.resolve()not in keep],remove_backups=[str(p)for p in backups[1:]])
def archive(source,archive_root):
 source=Path(source);dest=Path(archive_root)/source.name;dest.mkdir(parents=True,exist_ok=True)
 # Reports bind old binaries to source hashes. Player state is never discarded.
 for p in source.rglob('*'):
  if not p.is_file():continue
  relative=p.relative_to(source)
  keep=p.suffix.lower()in('.log','.json')and 'source'not in relative.parts
  keep=keep or 'save'in relative.parts or p.name in('config.cfg','vf_voice_behavior.cfg')
  if keep:
   checked_child(p,source);target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 # Keep a bounded visual sample with the archived reports.
 captures=sorted(p for p in source.rglob('*.png')if 'sdk'not in p.relative_to(source).parts and 'source'not in p.relative_to(source).parts)
 for p in select_captures(captures,32):
  checked_child(p,source);target=dest/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 return dest
def select_captures(paths,limit):
 if len(paths)<=limit:return paths
 return [paths[round(i*(len(paths)-1)/(limit-1))]for i in range(limit)]
def cleanup(releases,live,archive_root,evidence=None):
 releases=Path(releases);live=Path(live);result=plan(releases,live);removed=[]
 for key,parent in [('remove_candidates',releases),('remove_backups',live)]:
  for name in result[key]:
   path=checked_child(name,parent)
   # Refuse embedded repositories and every directory redirect before archiving.
   for p in path.rglob('*'):
    if p.name=='.git'or p.is_symlink()or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Unsafe generated tree: '+str(p))
   archive(path,archive_root);remove_tree(path,parent);removed.append(name)
 trimmed=compact_captures(Path(evidence))if evidence and Path(evidence).exists()else 0
 return dict(**result,removed=removed,discarded_capture_files=trimmed)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 with file_lock(ROOT/'build/release.lock'):
  releases=ROOT/'build/releases';live=ROOT.parent/'runtime/vector-engine'
  report=cleanup(releases,live,ROOT/'build/retention',EVIDENCE)if args.apply else plan(releases,live)
  print(json.dumps(report,indent=2))
  if args.apply:(ROOT/'build/retention/cleanup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

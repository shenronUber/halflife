"""Read-only project size report, counting NTFS hardlinks only once."""
import json,os,sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parent.parent

def scan(root=PROJECT):
 root=Path(root).resolve();pending=[root];seen=set();folders={};logical=distinct=count=0;errors=[]
 while pending:
  folder=pending.pop()
  try:
   with os.scandir(folder) as entries:
    for entry in entries:
     try:
      # Full os.stat is deliberate: cached DirEntry.stat can report inode 0
      # on Windows, incorrectly collapsing unrelated files into one identity.
      stat=os.stat(entry.path,follow_symlinks=False)
      if getattr(stat,'st_file_attributes',0)&0x400:continue
      if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path));continue
      if not entry.is_file(follow_symlinks=False):continue
      count+=1;logical+=stat.st_size
      name=Path(entry.path).relative_to(root).parts[0]
      folders[name]=folders.get(name,0)+stat.st_size
      identity=(stat.st_dev,stat.st_ino) if stat.st_ino else entry.path
      if identity not in seen:seen.add(identity);distinct+=stat.st_size
     except OSError as error:errors.append(dict(path=entry.path,error=str(error)))
  except OSError as error:errors.append(dict(path=str(folder),error=str(error)))
 return dict(project=str(root),files=count,logical_bytes=logical,distinct_file_bytes=distinct,
             hardlink_savings_bytes=logical-distinct,folders=dict(sorted(folders.items(),key=lambda pair:-pair[1])),errors=errors)

if __name__=='__main__':
 report=scan()
 if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2))

"""Append Counter-Strike humanoids without changing existing skin IDs."""
import hashlib,json,shutil
from pathlib import Path
import build_skins as skin
from studio_assets import Studio,canonical
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/visual_skins';STEAM=Path('F:/SteamLibrary/steamapps/common/Half-Life')
def main():
 skin.OUT=OUT
 for name in ['look_idle','walk']:shutil.copy2(ROOT/'generated/tfc-soldier'/(name+'.smd'),OUT/(name+'.smd'))
 path=OUT/'skins.txt';lines=path.read_text(encoding='ascii').splitlines();seen=set();records=[];rejected=[]
 old=OUT/'cs-skins.json'
 if old.exists():
  previous=json.loads(old.read_bytes());records=previous['records']
  for r in records:
   expected=f'{r["id"]}|{r["key"]}|CS / {r["name"]}'
   if r['id']==len(lines):lines.append(expected)
   elif r['id']<len(lines):assert lines[r['id']]==expected, 'Existing skin index changed'
   else:raise RuntimeError('Missing base skin catalog')
  seen={r['sha256']for r in records}
 for game in ['cstrike','cstrike_hd']:
  for p in sorted((STEAM/game/'models').rglob('*.mdl')):
   if p.stem.startswith(('v_','p_','w_')):continue
   try:s=Studio(p)
   except (AssertionError,ValueError,IndexError):continue
   names={canonical(n)for n in s.names}
   if not {'head','l hand','r hand','l foot','r foot','pelvis'}.issubset(names)or not s.parts:continue
   sha=hashlib.sha256(p.read_bytes()).hexdigest()
   if sha in seen:continue
   try:
    entry=dict(path=str(p),game='CS',name=p.stem+(' HD'if game.endswith('_hd')else''),choices={},sha256=sha,also_in=[])
    index=len(lines);assert index<240
    r=skin.build_character(entry,index,conform=True,key=f'cs_skin_{index}',export=False)
    lines.append(f'{index}|{r["key"]}|CS / {entry["name"]}');records.append(r);seen.add(sha);print('CS skin',index,entry['name'],flush=True)
   except (AssertionError,ValueError,RuntimeError)as e:rejected.append(dict(path=str(p),reason=str(e)))
 path.write_text('\n'.join(lines)+'\n',encoding='ascii');old.write_text(json.dumps(dict(records=records,rejected=rejected),indent=2),encoding='utf-8');print('CS skins added',len(records),'rejected',len(rejected),'total',len(lines))
if __name__=='__main__':main()

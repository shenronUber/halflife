"""Stage installed/community GoldSrc content, with stable keys and MP5 animation adapters."""
import collections,hashlib,json,os,re,shutil,struct,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;LAB=PROJECT/'weapon-lab';OUT=ROOT/'generated/library';MODELS=OUT/'models/vf_library';MODELS.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));from studio_assets import Studio
STEAM=Path('F:/SteamLibrary/steamapps/common/Half-Life')
def ascii(s):return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().replace('|',' ').replace('"',"'")
def putstr(d,off,size,text):
 b=text.encode('ascii');assert len(b)<size,text;d[off:off+size]=b+bytes(size-len(b))
def sequence_adapter(d):
 count,off=struct.unpack_from('<ii',d,164);seq=[bytearray(d[off+i*176:off+(i+1)*176])for i in range(count)];names=[q[:32].split(b'\0')[0].decode('latin1').lower()for q in seq]
 def find(pattern,default=0):return next((i for i,n in enumerate(names)if re.search(pattern,n)),default)
 idle=find(r'^idle_unsil$|^idle$|^idle1$|^longidle$');fire=find(r'shoot|fire',-1);reload=find(r'reload',-1);draw=find(r'^draw|deploy|deploy1',idle)
 if fire<0 or reload<0:return None
 fires=[i for i,n in enumerate(names)if re.search('shoot|fire',n)];mapping=[idle,idle,fire,reload,draw]+[fires[i%len(fires)]for i in range(3)]
 newoff=len(d)
 for j,i in enumerate(mapping):
  q=bytearray(seq[i]);putstr(q,0,32,['vf_idle','vf_idle2','vf_secondary','vf_reload','vf_draw','vf_fire1','vf_fire2','vf_fire3'][j])
  # Match the existing MP5 reload timer; originals remain available after index 8.
  if j==3:struct.pack_into('<f',q,32,max(1,(struct.unpack_from('<i',q,56)[0]-1)/1.5))
  if j<2:struct.pack_into('<i',q,36,struct.unpack_from('<i',q,36)[0]|1)
  d.extend(q)
 d.extend(b''.join(seq));struct.pack_into('<ii',d,164,count+8,newoff);struct.pack_into('<i',d,72,len(d))
 return dict(mapping=[names[i]for i in mapping],original_sequence_start=8,reload_seconds=1.5)
def main():
 candidates=[];metadata={}
 for directory in [LAB/'catalog',LAB/'catalog/expansion',LAB/'catalog/ww2']:
  for p in directory.glob('*-raw.json'):
   try:r=json.loads(p.read_bytes());metadata[str(r['_idRow'])]=r
   except (ValueError,KeyError):pass
 for folder in sorted((LAB/'extracted').iterdir()):
  if not folder.name.isdigit():continue
  md=metadata.get(folder.name,{});packname=ascii(md.get('_sName','Pack '+folder.name));group='WW2'if folder.name in ('179714','351127','226527','36058')else'GameBanana'
  for p in sorted(folder.rglob('*')):
   if p.suffix.lower()=='.mdl':candidates.append((p,group,packname,folder.name,folder))
 for game,group in [('cstrike','CS 1.6'),('cstrike_hd','CS HD')]:
  folder=STEAM/game/'models'
  if folder.exists():
   for p in sorted(folder.rglob('*.mdl')):candidates.append((p,group,'Counter-Strike',game,folder.parent))
 for r in json.loads((ROOT/'generated/skins/arsenal.json').read_bytes()):candidates.append((Path(r['source']),'TFC','Team Fortress Classic','tfc',STEAM/'tfc'))
 source=LAB/'generated/source-goldsrc/source_m4.mdl'
 if source.exists():candidates.append((source,'Source converti','M4 RIS / Source -> GoldSrc','source_m4',source.parent))
 # Complete isolated pieces retain their original coordinates for inspection.
 accessories=json.loads((LAB/'generated/accessories/manifest.json').read_bytes())
 for a in accessories:candidates.append((LAB/a['mdl'],'Pieces',ascii(a['name']),'part_'+a['key'],LAB/'generated/accessories'/a['key']))
 result=[];rejected=[];duplicates=[];seen={};sound_cache={}
 def sound_option(pack,folder,source,option):
  clean=option.replace('\\','/').strip('"').lower()
  if not clean.endswith('.wav')or'..'in clean:return option
  cachekey=(str(folder),clean)
  if cachekey not in sound_cache:
   matches=[p for p in folder.rglob('*.wav')if p.as_posix().lower().endswith('/sound/'+clean)]
   if matches:
    matches.sort(key=lambda p:len(os.path.commonpath([source,p])),reverse=True);p=matches[0];name=hashlib.sha256(p.read_bytes()).hexdigest()[:16]+'.wav';rel='vflib/'+name;target=OUT/'sound'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(p,target)
    sound_cache[cachekey]=rel
   else:sound_cache[cachekey]=option
  return sound_cache[cachekey]
 for p,group,label,pack,folder in candidates:
  try:
   original=p.read_bytes()
   if original[:8]!=b'IDST\x0a\0\0\0':continue
   s=Studio(p)
   if not s.parts or not s.names or not s.textures:continue
   sha=hashlib.sha256(original).hexdigest()
   if sha in seen:duplicates.append(dict(file=str(p),same_as=seen[sha]));continue
   key=('a'+sha[:16]);seen[sha]=key;d=bytearray(original);native='models/vf_library/'+key+'.mdl';putstr(d,8,64,native)
   isview=p.name.lower().startswith('v_') or pack=='source_m4'
   isperson='player'in p.parts or p.stem.lower()in ['hostage','scientist','vip']
   kind=0 if isview else 2 if isperson else 1
   if group=='Pieces':kind=3
   adapter=None
   # Sound references are isolated per content hash so packs cannot overwrite each other.
   nc,so=struct.unpack_from('<ii',d,164)
   for j in range(nc):
    ec,eo=struct.unpack_from('<ii',d,so+j*176+48)
    for k in range(ec):
     event=eo+k*76;option=d[event+12:event+76].split(b'\0')[0].decode('latin1')
     if option.endswith('.wav'):
      name=sound_option(pack,folder,p,option)
      if len(name.encode('ascii',errors='ignore'))<64:putstr(d,event+12,64,ascii(name))
   if isview:adapter=sequence_adapter(d)
   # Companion texture files and external animation groups are copied under the new stem.
   if struct.unpack_from('<i',d,180)[0]==0:
    companion=next((q for q in p.parent.iterdir()if q.name.lower()==p.stem.lower()+'t.mdl'),None)
    if companion is None:raise ValueError('missing texture companion')
    shutil.copy2(companion,MODELS/(key+'t.mdl'))
   ng,go=struct.unpack_from('<ii',d,172)
   for j in range(1,ng):
    old=d[go+j*104+32:go+j*104+96].split(b'\0')[0].decode('latin1').replace('\\','/')
    companion=p.parent/Path(old).name
    if not companion.exists():companion=p.with_name(p.stem+f'{j:02}.mdl')
    if not companion.exists():raise ValueError('missing animation companion '+old)
    target=key+f'{j:02}.mdl';shutil.copy2(companion,MODELS/target);putstr(d,go+j*104+32,64,'models/vf_library/'+target)
   target=MODELS/(key+'.mdl');target.write_bytes(d);check=Studio(target);assert len(check.names)==len(s.names)
   slot=-1
   if group=='Pieces':
    a=next(a for a in accessories if 'part_'+a['key']==pack);slot={'Optique':0,'Bouche':1,'Crosse':2,'Poignee':3,'Chargeur':4}[ascii(a['kind'])];name=ascii(a['name'])
   elif group in ('CS 1.6','CS HD'):name=ascii(p.stem.replace('v_','').replace('p_','').replace('w_','').replace('_',' ').upper())+' / '+('en main'if isview else'modele')
   elif group=='TFC':name=ascii(p.stem)
   elif pack=='source_m4':name='M4 RIS / Source converti'
   else:
    parents=[x for x in p.relative_to(folder).parts[:-1] if x.lower() not in ('models','valve','cstrike')]
    variant=' / '.join(parents[-2:]) if parents else 'standard'
    name=ascii(label)[:52]+' / '+p.stem[:22]
    if variant!='standard':name+=' / '+ascii(variant)[:42]
   r=dict(id=len(result),key=key,name=name,collection=group,pack=pack,source=str(p),source_sha256=sha,model=native,kind=kind,playable=bool(adapter),accessory_slot=slot,sequences=len(check.sequences),animation_adapter=adapter,bytes=len(d))
   result.append(r)
  except (ValueError,AssertionError,IndexError,struct.error,FileNotFoundError)as e:rejected.append(dict(source=str(p),reason=str(e)))
 for p in sorted((PROJECT/'runtime/vector-engine/vf_visual/maps').glob('vf_cs_*.bsp')):
  result.append(dict(id=len(result),key=p.stem,name=p.stem.removeprefix('vf_cs_'),collection='Cartes CS',model=p.stem,kind=4,playable=False,accessory_slot=-1))
 (OUT/'manifest.json').write_text(json.dumps(dict(entries=result,rejected=rejected,duplicates=duplicates,metadata_files=['weapon-lab/catalog','weapon-lab/catalog/expansion','weapon-lab/catalog/ww2']),indent=2),encoding='utf-8')
 def q(s):return json.dumps(ascii(str(s)),ensure_ascii=True)
 header='// Generated by vector-fields/build_library.py; content loaded only on selection.\nstatic const VF_LibraryEntry vfLibrary[]={\n'
 for r in result:header+=' {'+','.join([q(r['key']),q(r['name']),q(r['collection']),q(r['model']),str(r['kind']),str(int(r['playable'])),str(r['accessory_slot'])])+'},\n'
 header+='};\n';(PROJECT/'cl_dll/vf_library_data.h').write_text(header,encoding='ascii')
 print(json.dumps(dict(entries=len(result),playable=sum(r['playable']for r in result),collections=dict(collections.Counter(r['collection']for r in result)),rejected=len(rejected),duplicates=len(duplicates))))
if __name__=='__main__':main()

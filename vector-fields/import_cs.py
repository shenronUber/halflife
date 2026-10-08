"""Local Counter-Strike art snapshot; converted exploration maps, never game DLLs."""
import hashlib,json,shutil,struct
from pathlib import Path
from import_tfc import entities,write_entities
ART_DIRS={'models','maps','sound','sprites','gfx','events','overviews','resource','classes','logos'}
def install(source,engine,destination):
 library=engine/'cs_assets';marker=library/'vector-fields-cs.marker'
 if library.exists() and not marker.exists():raise RuntimeError('Unrecognized CS library')
 library.mkdir(exist_ok=True);marker.write_text('Local Counter-Strike resources; no game binaries or user configuration.\n',encoding='ascii')
 files=[]
 for p in sorted(source.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(source)
  if not (rel.parts[0].lower() in ART_DIRS or p.suffix.lower()=='.wad'):continue
  if p.suffix.lower() in ('.dll','.exe','.cfg','.dem','.log','.sav','.asi'):continue
  mounted=rel.parts[0].lower() not in ('resource','classes','logos')
  target=library/rel if mounted else library/'reference'/rel
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists() or target.stat().st_size!=p.stat().st_size or target.stat().st_mtime!=p.stat().st_mtime:shutil.copy2(p,target)
  files.append(dict(file=rel.as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mounted=mounted))
 # Xash mounts one fallback directory. Preserve TFC-only resources in the same
 # mounted snapshot; never overwrite a CS resource or load class-specific UI.
 tfc=engine/'tfc_assets';tfc_added=[]
 for p in sorted(tfc.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(tfc)
  if not (rel.parts[0] in ART_DIRS or p.suffix.lower()=='.wad'):continue
  target=library/rel
  if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);tfc_added.append(rel.as_posix())
 # Union decal dictionaries, preserving original mip payloads and palette data.
 lumps={}
 for wad in [source.parent/'valve/decals.wad',tfc/'decals.wad',source/'decals.wad']:
  if not wad.exists():continue
  d=wad.read_bytes();assert d[:4]==b'WAD3';n,off=struct.unpack_from('<ii',d,4)
  for i in range(n):
   pos,size,raw,typ,comp,pad,name=struct.unpack_from('<iiiBBH16s',d,off+i*32);assert not comp
   lumps[name.rstrip(b'\0').lower()]=(d[pos:pos+size],raw,typ,comp,pad,name)
 payload=bytearray(b'WAD3'+bytes(8));directory=[]
 for data,raw,typ,comp,pad,name in lumps.values():
  directory.append(struct.pack('<iiiBBH16s',len(payload),len(data),raw,typ,comp,pad,name));payload.extend(data)
 offset=len(payload);payload.extend(b''.join(directory));struct.pack_into('<ii',payload,4,len(directory),offset);(destination/'decals.wad').write_bytes(payload)

 (library/'gameinfo.txt').write_text('title "Counter-Strike - ressources locales"\nbasedir "valve"\n',encoding='ascii')
 maps=[];skipped=[];(destination/'maps').mkdir(exist_ok=True)
 for p in sorted((source/'maps').glob('*.bsp')):
  data=p.read_bytes();items=entities(data);spawns=[x for x in items if x.get('classname') in ('info_player_start','info_player_deathmatch')]
  if not spawns:skipped.append(dict(file=p.name,reason='no player spawn'));continue
  spawn=spawns[0];result=[];removed={}
  for x in items:
   cls=x.get('classname','')
   if cls in ('info_player_start','env_rain','func_hostage_rescue','info_hostage_rescue','func_bomb_target','info_bomb_target','func_buyzone','func_escapezone','func_vip_safetyzone','info_vip_start','info_map_parameters','armoury_entity'):
    removed[cls]=removed.get(cls,0)+1;continue
   if cls=='item_generic':x={**x,'classname':'cycler'};x.pop('sequencename',None)
   if cls=='hostage_entity':x=dict(classname='cycler',model='models/hostage.mdl',origin=x.get('origin','0 0 0'),angle=x.get('angle','0'))
   result.append(x)
  result.append(dict(classname='info_player_start',origin=spawn['origin'],angles=spawn.get('angles','0 '+spawn.get('angle','0')+' 0')))
  name='vf_cs_'+p.stem
  overview=source/'overviews'/(p.stem+'.txt')
  if overview.exists():
   (destination/'overviews').mkdir(exist_ok=True);shutil.copy2(overview,destination/'overviews'/(name+'.txt'))
  (destination/'maps'/(name+'.bsp')).write_bytes(write_entities(data,result))
  cfg='map '+name+'\nwait 180\ngive item_suit\ngive weapon_9mmAR\ngive ammo_9mmbox\nweapon_9mmAR\n'
  (destination/('vf_visit_'+p.stem+'.cfg')).write_text(cfg,encoding='ascii')
  maps.append(dict(name=name,source=str(p),spawn=spawn['origin'],removed=removed,mode='exploration; no Counter-Strike match rules'))
 report=dict(source=str(source),count=len(files),bytes=sum(x['bytes']for x in files),files=files,maps=maps,skipped=skipped,local_only=True,tfc_overlay=tfc_added,merged_decals=len(lumps))
 (library/'import-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(destination/'cs-maps.json').write_text(json.dumps(maps,indent=2),encoding='utf-8')
 return report
if __name__=='__main__':
 root=Path(__file__).resolve().parent.parent;r=install(Path('F:/SteamLibrary/steamapps/common/Half-Life/cstrike'),root/'runtime/vector-engine',root/'runtime/vector-engine/vf_visual');print('CS resources',r['count'],'maps',len(r['maps']),'bytes',r['bytes'])

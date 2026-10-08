"""Import installed TFC art and create non-destructive exploration maps."""
import hashlib
import json
import re
import shutil
import struct

def entities(data):
    assert struct.unpack_from('<i',data)[0]==30,'GoldSrc BSP v30 required'
    offset,length=struct.unpack_from('<2i',data,4)
    assert offset>=124 and offset+length<=len(data)
    text=data[offset:offset+length].rstrip(b'\0').decode('latin1')
    # Texture names such as "{shot1" contain braces inside quoted strings.
    # Tokenize quoted values before treating braces as entity delimiters.
    result=[];item=None;key=None
    for m in re.finditer(r'"([^"\r\n]*)"|([{}])',text):
        value,brace=m.groups()
        if brace=='{':
            assert item is None,'Nested entity';item={};key=None
        elif brace=='}':
            assert item is not None and key is None,'Malformed entity';result.append(item);item=None
        elif item is not None:
            if key is None:key=value
            else:item[key]=value;key=None
    assert item is None,'Unclosed entity'
    return result

def write_entities(data,items):
    result=bytearray(data)
    text='\n'.join('{\n'+''.join(f'"{k}" "{v}"\n' for k,v in item.items())+'}' for item in items)
    lump=text.encode('latin1')+b'\0'
    struct.pack_into('<2i',result,4,len(result),len(lump));result.extend(lump)
    return result

def install(source,engine,destination):
    library=engine/'tfc_assets';marker=library/'vector-fields-tfc.marker'
    if library.exists() and not marker.exists():raise RuntimeError('Unrecognized TFC library directory')
    library.mkdir(parents=True,exist_ok=True);marker.write_text('Local TFC art snapshot; no game binaries.\n')
    inventory=[]
    for p in sorted(source.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(source)
        if rel.parts[0].lower() in ('dlls','cl_dlls'):continue
        if p.suffix.lower() in ('.dll','.exe','.cfg') or p.name.lower() in ('liblist.gam','valve.rc','steam.inf','steam_appid.txt'):continue
        # TFC's command menus instantiate class-specific UI absent from HLSDK.
        # Preserve documentation/UI as reference, outside engine lookup paths.
        art=rel.parts[0].lower() in ('models','maps','sound','sprites','gfx','events','overviews') or p.suffix.lower()=='.wad'
        target=library/rel if art else library/'reference'/rel
        old=library/rel
        if not art and old.is_file():
            assert old.resolve().is_relative_to(library.resolve())
            old.unlink()
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or target.stat().st_size!=p.stat().st_size or target.stat().st_mtime!=p.stat().st_mtime:shutil.copy2(p,target)
        inventory.append({'file':rel.as_posix(),'mounted':art,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (library/'gameinfo.txt').write_text('title "TFC - bibliotheque locale"\nbasedir "valve"\n',encoding='ascii')
    maps=[]
    for p in sorted((source/'maps').glob('*.bsp')):
        data=p.read_bytes();items=entities(data)
        spawns=[i for i in items if i.get('classname')=='info_player_start'] or [i for i in items if i.get('classname') in ('info_player_teamspawn','info_player_deathmatch')]
        if not spawns:raise RuntimeError(f'No exploration spawn in {p.name}')
        spawn=spawns[0];items=[i for i in items if i.get('classname')!='info_player_start']
        items.append(dict(classname='info_player_start',origin=spawn['origin'],angles=spawn.get('angles','0 '+spawn.get('angle','0')+' 0')))
        name='vf_tfc_'+p.stem
        (destination/'maps'/(name+'.bsp')).write_bytes(write_entities(data,items))
        maps.append({'name':name,'source':str(p),'spawn':spawn['origin'],'mode':'exploration; TFC objectives not implemented'})
    manifest={'source':str(source),'files':inventory,'count':len(inventory),'bytes':sum(i['bytes'] for i in inventory),'maps':maps,'local_only':True}
    (library/'import-manifest.json').write_text(json.dumps(manifest,indent=2))
    (destination/'tfc-maps.json').write_text(json.dumps(maps,indent=2))
    return manifest

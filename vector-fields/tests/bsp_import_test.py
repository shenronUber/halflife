"""Protect actual BSP semantics: braces in decal names must survive an import."""
import struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_tfc import entities,write_entities
text=b'{\n"classname" "infodecal"\n"texture" "{shot1"\n"origin" "1 2 3"\n}\n{\n"classname" "worldspawn"\n"wad" "c:\\half-life\\test.wad"\n}\n\0'
data=bytearray(124);struct.pack_into('<i',data,0,30);struct.pack_into('<ii',data,4,124,len(text));data.extend(text)
expected=[dict(classname='infodecal',texture='{shot1',origin='1 2 3'),dict(classname='worldspawn',wad='c:\\half-life\\test.wad')]
assert entities(data)==expected
assert entities(write_entities(data,expected))==expected
source=Path('F:/SteamLibrary/steamapps/common/Half-Life/cstrike/maps');count=0
for p in source.glob('*.bsp'):
 for e in entities(p.read_bytes()):
  if e.get('classname')=='infodecal':assert e.get('texture'),p;count+=1
print('PASS BSP quoted braces and',count,'installed CS decals')

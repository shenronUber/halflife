"""Room generation is repeatable, cached and independent of installed runtime maps."""
import json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch as mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_test_room as room
from import_tfc import entities

def bsp():
 text='{\n"classname" "worldspawn"\n}\n{\n"classname" "cycler"\n"model" "models/vf_tfc/scout.mdl"\n}\n'
 data=bytearray(124);struct.pack_into('<i',data,0,30)
 for i in range(15):
  chunk=text.encode()+b'\0' if i==0 else bytes([i])*8
  struct.pack_into('<ii',data,4+i*8,len(data),len(chunk));data.extend(chunk)
 return bytes(data)

class RoomTests(unittest.TestCase):
 def test_patch_is_idempotent_and_preserves_geometry(self):
  source=bsp();out=room.patch(source);self.assertEqual(out,room.patch(out))
  self.assertEqual(len([e for e in entities(out) if e.get('classname')=='vf_range_target']),4)
  for i in range(1,15):
   a,n=struct.unpack_from('<ii',source,4+i*8);b,m=struct.unpack_from('<ii',out,4+i*8)
   self.assertEqual((a,n),(b,m));self.assertEqual(source[a:a+n],out[b:b+m])
 def test_default_build_uses_authored_base(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'base.bsp';source.write_bytes(bsp())
   with mock.object(room,'OUT',Path(temp)/'generated'),mock.object(room,'base_room',return_value=source) as authored:
    out=room.build(ensure=True);authored.assert_called_once()
    record=json.loads(out.with_name('manifest.json').read_text(encoding='utf-8'))
    self.assertEqual(record['source'],str(source))
 def test_unchanged_build_does_not_rewrite_output(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'base.bsp';source.write_bytes(bsp())
   with mock.object(room,'OUT',Path(temp)/'generated'):
    out=room.build(source,ensure=True);stamp=out.stat().st_mtime_ns
    self.assertEqual(room.build(source,ensure=True),out);self.assertEqual(out.stat().st_mtime_ns,stamp)
 def test_corrupt_map_is_rebuilt(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'base.bsp';source.write_bytes(bsp())
   with mock.object(room,'OUT',Path(temp)/'generated'):
    out=room.build(source,ensure=True);expected=out.read_bytes();out.write_bytes(b'corrupt')
    room.build(source,ensure=True);self.assertEqual(out.read_bytes(),expected)

if __name__=='__main__':unittest.main()

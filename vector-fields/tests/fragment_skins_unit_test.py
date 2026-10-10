"""Independent skin references preserve existing uniform families and model bytes."""
import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fragment_skins import skin_pairs,pair_skin,expand_skin_table

class FragmentSkinTests(unittest.TestCase):
 def test_every_pair_has_a_unique_native_index(self):
  pairs=skin_pairs();self.assertEqual(len(pairs),196)
  self.assertEqual([pair_skin(a,b) for a,b in pairs],list(range(196)))
 def test_uniform_indices_remain_compatible(self):
  for i in range(14):self.assertEqual(pair_skin(i,i),i)
 def test_invalid_finishes_are_rejected(self):
  for a,b in [(-1,0),(0,-1),(14,0),(0,14)]:
   with self.assertRaises(ValueError):pair_skin(a,b)
 def fixture(self):
  data=bytearray(800);data[:4]=b'IDST';struct.pack_into('<i',data,4,10)
  struct.pack_into('<ii',data,180,4,260);struct.pack_into('<iii',data,192,2,2,700)
  for i,name in enumerate(['persona_original.bmp','fragment_detail_original.bmp','persona_alt.bmp','fragment_detail_alt.bmp']):
   raw=name.encode();data[260+i*80:260+i*80+len(raw)]=raw
  struct.pack_into('<4h',data,700,0,1,2,3);return bytes(data)
 def test_mixed_rows_reuse_the_correct_material_banks(self):
  before=self.fixture();after=expand_skin_table(before,2);refs,count,start=struct.unpack_from('<iii',after,192)
  self.assertEqual((refs,count),(2,4));self.assertEqual(struct.unpack_from('<8h',after,start),(0,1,2,3,0,3,2,1))
  # Only length/skin-table header fields change; prior model/texture bytes stay intact.
  expected=bytearray(before);expected[72:76]=after[72:76];expected[192:204]=after[192:204]
  self.assertEqual(after[:len(before)],expected);self.assertEqual(struct.unpack_from('<i',after,72)[0],len(after))
 def test_missing_detail_bank_is_rejected(self):
  data=bytearray(self.fixture());data[340:404]=bytes(64)
  with self.assertRaisesRegex(ValueError,'detail material'):expand_skin_table(data,2)
 def test_wrong_compiled_family_count_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'families'):expand_skin_table(self.fixture())

if __name__=='__main__':unittest.main()

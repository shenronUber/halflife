"""Compiled fragments resolve every clothing/detail pair without duplicating geometry."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fragment_skins import FINISH_COUNT,skin_pairs,pair_skin
from studio_assets import Studio

def run():
 model=Studio(ROOT/'generated/deaths/persona_death_gibs.mdl')
 assert model.parts[0][1]==20 and model.numskinfamilies==FINISH_COUNT**2
 manifest=json.loads((ROOT/'generated/deaths/manifest.json').read_text(encoding='utf-8'))
 assert manifest['fragment_skin_pairs']==[list(p) for p in skin_pairs()]
 uniform=[model.skin[i*model.numskinref:(i+1)*model.numskinref] for i in range(FINISH_COUNT)]
 detail_slots=[i for i,t in enumerate(uniform[0]) if model.textures[t][0].startswith('fragment_detail_')]
 assert len(detail_slots)==1
 for primary,detail in skin_pairs():
  row=model.skin[pair_skin(primary,detail)*model.numskinref:(pair_skin(primary,detail)+1)*model.numskinref]
  for i,t in enumerate(row):
   expected=uniform[detail if i in detail_slots else primary][i]
   assert model.textures[t]==model.textures[expected],(primary,detail,i)
 # A whole arm and leg contain both materials. Mixed families change only the detail.
 for body in (16,17,18,19):
  tri=model.mesh({0:body},skin=pair_skin(2,0));names={model.textures[t][0] for t,_ in tri}
  assert any(n.startswith('fragment_detail_') for n in names) and any(n.startswith('persona_') for n in names)
  assert any(n.startswith('death_') for n in names)
 # Pixel banks grow with finish count, not with its square; all 20 meshes are shared.
 assert len(model.textures)<=FINISH_COUNT*2+5
 print('PASS fragment finishes: 196 compiled pairs, independent glove/boot bank, fixed wounds, 20 shared meshes')

if __name__=='__main__':run()

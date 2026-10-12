"""Refresh only reviewed clips, reusing the existing fitted meshes/textures."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info
from third_person import smd
from traversal_animations import TIMES
from traversal_editor import WORKSHOP,EDITS
records=json.loads((WORKSHOP/'gestures.json').read_text())
for view,path,names in [
 ('first-person','generated/traversal/r01_rig_tr.mdl',('vf_vault','vf_stepup')),
 ('third-person','generated/third-person/r01_tp.mdl',('vf_vault','vf_stepup','vf_slide_start','vf_slide_loop','vf_slide_end'))]:
 model=Studio(ROOT/path);folder=WORKSHOP/view
 for name in names:
  frames=sequence_frames(model,name);key=name+'_0';info=sequence_info(model,name)
  smd(model,frames,folder/(key+'.smd'))
  records=[r for r in records if not(r['view']==view and r['gesture']==name)]
  records.append(dict(view=view,gesture=name,corner=0,frames=len(frames),seconds=TIMES[name],fps=info['fps'],editable=str(folder/(key+'.smd')),override=str(EDITS/view/(key+'.smd'))))
(WORKSHOP/'gestures.json').write_text(json.dumps(records,indent=2))
print('Updated seven fitted clips; existing meshes and texture banks reused.')

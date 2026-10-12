"""Confirm the filmed native resources are precisely those installed in main."""
import json
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest
candidate=ROOT/'build/animation-feedback/candidate';live=PROJECT/'runtime/vector-engine'
path=ROOT/'docs/videos/parcours-2026-10-12/video.json';proof=json.loads(path.read_text());checked={}
for source,sha in proof['sources'].items():
    relative=Path(source).relative_to(candidate)
    if relative.parts[0]=='engine':target=live/Path(*relative.parts[1:])
    elif relative.parts[0]=='client':target=live/'vf_visual/cl_dlls/client.dll'
    elif relative.parts[0]=='server':target=live/'vf_visual/dlls/hl.dll'
    else:target=live/'vf_visual'/relative
    assert digest(target)==sha,(target,'filmed asset differs from main')
    checked[str(target)]=sha
proof['installed_main_sources']=checked;proof['installed_in_main']=True
path.write_text(json.dumps(proof,indent=2))
print('PASS delivered videos match installed main:',len(checked),'resources')
print([(key,round(v['duration_seconds'],2))for key,v in proof['videos'].items()])

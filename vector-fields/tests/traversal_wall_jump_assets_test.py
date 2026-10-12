"""Authored push-offs survive the standard pipeline and all carrier variants."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info
from traversal_editor import override
from build_traversal import pose,VARIANTS
from traversal_animations import tp_pose
from third_person import Author,RECIPE

def run():
    records=json.loads((ROOT/'build/wall-jump/assets.json').read_text());author=Author(json.loads(RECIPE.read_text()))
    for record in records:
        model=Studio(record['candidate']);view=record['view']
        if view=='first-person':
            from traversal_hands import extend
            original=extend(Studio(ROOT/'generated/r01'/(record['model'].replace('_tr','')+'.mdl')))
        else:original=author.model
        for gesture in ('vf_wall_jump','vf_wall_jump_turn'):
            frames=sequence_frames(model,gesture);info=sequence_info(model,gesture)
            assert len(frames)==21 and abs((len(frames)-1)/info['fps']-.65)<.0001
            assert np.isfinite(frames).all()
            if view=='first-person':default=np.array([pose(original,gesture,t)for t in np.linspace(0,1,21)])
            else:
                platform='side'if record['model'].endswith('_side')else'top'if record['model'].endswith('_top')else'bottom'
                default=np.array([tp_pose(author,platform,gesture,t)for t in np.linspace(0,1,21)])
            authored=override(original,default,view,gesture,0)
            assert np.max(np.abs(default-authored))>.1,'Authored track was ignored'
            compiled=frames[:,[model.names.index(n)for n in original.names]]
            # Studio quantizes animated translations in steps of 1/256 unit.
            assert np.max(np.abs(compiled-authored))<.005,(record['model'],gesture)
    print('PASS wall-jump assets: standard overrides, two gestures and all nine carriers',flush=True)

if __name__=='__main__':run()

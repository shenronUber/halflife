import json
from pathlib import Path
import bpy
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
scene=bpy.context.scene;source,controls,result=addon.objects(scene)
rows=[]
for name in ('vf_hang_idle_0','vf_climb_0','vf_slide_loop_0'):
    addon.select_track(scene,name)
    track=next(t for t in addon.tracks(scene)if t['key']==name)
    for t in (0,.25,.5,.75,1):
        scene.frame_set(round(1+(track['frames']-1)*t));bpy.context.view_layer.update()
        addon.update(scene,force=True);bpy.context.view_layer.update()
        rows.append(dict(track=name,t=t,controls={n:list(controls.pose.bones[n].matrix.translation)for n in ('Main_G','Main_D','Coude_G','Coude_D')if n in controls.pose.bones},bones={b:list(result.pose.bones[b].matrix.translation)for b in ('Bone04','Bone05','Bone06','Bone07','Bone40','Bone41','Bone42','Bip01 Head','Bip01 Neck')if b in result.pose.bones}))
path=Path(__file__).resolve().parents[1]/'build'/('probe-climb-'+scene['vf_view']+'.json')
path.write_text(json.dumps(rows,indent=2));print('PROBE',path)

"""Run inside Blender to check the saved pose revision and interpolation."""
import json
import math
from pathlib import Path
import bpy
import vf_workshop as addon

scene=bpy.context.scene
source,controls,result=addon.objects(scene)
assert scene['vf_current']=='vf_hang_idle_0'
assert controls.animation_data.action.name in ('POSES|vf_hang_idle_0','POUCES|vf_hang_idle_0')
assert source.animation_data.action.name=='SOURCE|vf_hang_idle_0'
max_half_frame_error=0.;max_step=0.
for track in addon.tracks(scene):
    if 'slide' in track['key']:continue
    addon.select_track(scene,track['key'])
    frames=[]
    for f in range(1,track['frames']+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        frames.append({pb.name:pb.rotation_euler.to_quaternion().copy() for pb in controls.pose.bones if pb.name.startswith(('G_','D_'))})
    for f in range(1,track['frames']):
        scene.frame_set(f,subframe=.5);bpy.context.view_layer.update()
        for n,q in frames[f-1].items():
            next_q=frames[f][n]
            interpolated=controls.pose.bones[n].rotation_euler.to_quaternion()
            angle=interpolated.rotation_difference(q.slerp(next_q,.5)).angle
            angle=min(angle,abs(2*math.pi-angle))
            max_half_frame_error=max(max_half_frame_error,angle)
            step=q.rotation_difference(next_q).angle
            max_step=max(max_step,min(step,abs(2*math.pi-step)))
assert max_half_frame_error<.03,('Euler interpolation jump',max_half_frame_error)
addon.select_track(scene,'vf_hang_idle_0')
bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
assert not result.get('vf_reach_warning')
mesh=bpy.data.objects[scene['vf_mesh']].evaluated_get(bpy.context.evaluated_depsgraph_get())
assert all(math.isfinite(v) for vertex in mesh.data.vertices for v in vertex.co)
report=dict(saved_project_loads=True,source_and_revision_actions_connected=True,
    max_half_frame_quaternion_error_radians=max_half_frame_error,max_keyframe_step_radians=max_step,
    hand_reach_valid=True,mesh_finite=True)
out=Path(bpy.data.filepath).parent/'verification/postures/saved-project-validation.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS',json.dumps(report),flush=True)

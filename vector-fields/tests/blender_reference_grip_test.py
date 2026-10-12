"""Check the saved R1 grip using the evaluated mesh, independently of its authoring fit."""
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
import vf_workshop as addon

scene=bpy.context.scene
source,controls,result=addon.objects(scene)
out=Path(bpy.data.filepath).parent/'verification/reference-rebord'
authoring=json.loads((out/'corrections.json').read_text(encoding='utf-8'))
assert hashlib.sha256(Path(authoring['baseline']).read_bytes()).hexdigest()==authoring['baseline_sha256']
assert scene['vf_current']==scene.vf_gesture=='vf_hang_idle_0'
assert controls.animation_data.action.name=='REFERENCE|vf_hang_idle_0'
assert source.animation_data.action.name=='SOURCE|vf_hang_idle_0'
assert any(image.packed_file and image.name.startswith('REFERENCE UTILISATEUR') for image in bpy.data.images)
assert Path(bpy.path.abspath(scene['vf_exports'])).resolve()==Path(authoring['export_directory']).resolve()

mesh=bpy.data.objects[scene['vf_mesh']]
groups={}
for vertex in mesh.data.vertices:
    for assignment in vertex.groups:
        if assignment.weight>.99:
            groups.setdefault(mesh.vertex_groups[assignment.group].name,[]).append(vertex.index)
mapping=json.loads(controls['vf_mapping'])
maximum_gap=0.;maximum_penetration=0.;maximum_thumb_gap=0.
minimum_dorsal_alignment=1.;minimum_inward_thumb_distance=100.
for frame in range(1,scene.frame_end+1):
    scene.frame_set(frame);bpy.context.view_layer.update()
    assert not result.get('vf_reach_warning'),frame
    evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points=[evaluated.matrix_world@vertex.co for vertex in evaluated.data.vertices]
    assert all(math.isfinite(v) for point in points for v in point)
    for side,wrist_name in [('G','Bone42'),('D','Bone07')]:
        wrist=result.pose.bones[wrist_name].matrix
        dorsal=wrist.to_3x3()@Vector((0,0,1))
        minimum_dorsal_alignment=min(minimum_dorsal_alignment,dorsal.normalized().dot(Vector((-1,0,0))))
        for finger in ('Index','Majeur','Annulaire','Auriculaire'):
            tip=[points[i] for i in groups[mapping[f'{side}_{finger}_4']] if points[i].x>18.12]
            assert tip,(side,finger,frame)
            maximum_gap=max(maximum_gap,abs(min(p.z for p in tip)-9.))
            all_points=[points[i] for segment in range(2,5) for i in groups[mapping[f'{side}_{finger}_{segment}']] if points[i].x>18.12]
            maximum_penetration=max(maximum_penetration,9.-min(p.z for p in all_points))
        thumb=[points[i] for i in groups[mapping[f'{side}_Pouce_3']] if points[i].z<8.8]
        assert thumb,(side,frame)
        maximum_thumb_gap=max(maximum_thumb_gap,abs(18.-max(p.x for p in thumb)))
        thumb_tip=result.pose.bones[mapping[f'{side}_Pouce_3']].matrix.translation
        inward=(wrist.translation.y-thumb_tip.y)*(1 if side=='G' else -1)
        minimum_inward_thumb_distance=min(minimum_inward_thumb_distance,inward)
assert maximum_gap<.12,('finger gap',maximum_gap)
assert maximum_penetration<.08,('finger penetration',maximum_penetration)
assert maximum_thumb_gap<.10,('thumb gap',maximum_thumb_gap)
assert minimum_dorsal_alignment>.9,minimum_dorsal_alignment
assert minimum_inward_thumb_distance>2.,minimum_inward_thumb_distance

# Fractional frames catch Euler flips that integer-frame SMD compilation misses.
max_interpolation_error=0.
for track in addon.tracks(scene):
    if 'slide' in track['key']:continue
    addon.select_track(scene,track['key'])
    keyframes=[]
    for frame in range(1,track['frames']+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        keyframes.append({pb.name:pb.rotation_euler.to_quaternion().copy() for pb in controls.pose.bones if pb.name.startswith(('G_','D_'))})
    for frame in range(1,track['frames']):
        scene.frame_set(frame,subframe=.5);bpy.context.view_layer.update()
        for name,q in keyframes[frame-1].items():
            actual=controls.pose.bones[name].rotation_euler.to_quaternion()
            angle=actual.rotation_difference(q.slerp(keyframes[frame][name],.5)).angle
            max_interpolation_error=max(max_interpolation_error,min(angle,abs(2*math.pi-angle)))
assert max_interpolation_error<.03,('finger rotation interpolation',max_interpolation_error)
report=dict(saved_scene_loads=True,reference_packed=True,baseline_preserved=True,
    maximum_finger_gap=maximum_gap,maximum_finger_penetration=maximum_penetration,
    maximum_thumb_front_gap=maximum_thumb_gap,minimum_dorsal_alignment=minimum_dorsal_alignment,
    minimum_inward_thumb_distance=minimum_inward_thumb_distance,
    maximum_half_frame_rotation_error=max_interpolation_error,game_files_deployed=False)
(out/'saved-scene-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS',json.dumps(report),flush=True)

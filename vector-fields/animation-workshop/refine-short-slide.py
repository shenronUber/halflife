"""Fold the right leg under the seat without changing the reviewed upper body."""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import globals_from
from studio_assets import Studio
from traversal_aim import slide_tucked_foot_rotation
scene=bpy.context.scene;source,controls,result=addon.objects(scene)
assert scene['vf_view']=='third-person'
baseline=Path(bpy.data.filepath);sha=hashlib.sha256(baseline.read_bytes()).hexdigest()
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
mapping=json.loads(controls['vf_mapping']);tracks=addon.tracks(scene)
ids=tuple(names.index(n)for n in('Bip01 R Leg','Bip01 R Leg1','Bip01 R Foot'))
persona=Studio(ROOT/'generated/personas/persona_scout.mdl')
bind={n:Matrix(m.tolist())for n,m in zip(persona.names,persona.bind)}
exports=baseline.parent.parent/'retouches/left-seat-slide/third-person';exports.mkdir(parents=True,exist_ok=True)
out=baseline.parent/'verification/left-seat-slide';out.mkdir(parents=True,exist_ok=True)
destination=baseline.with_name('Corps-R1-appuis-revus.blend')

def evaluate(f):
    scene.frame_set(f);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def solve(local,goal,pole):
    upper,fore,foot=ids;g=globals_from(local,parents)
    hip,knee,ankle=(g[i].translation for i in ids)
    a=(knee-hip).length;b=(ankle-knee).length;delta=goal.translation-hip;d=delta.length
    assert abs(a-b)+.0001<d<a+b-.0001,('right leg out of reach',d,a,b)
    direction=delta.normalized();bias=pole-hip;bias-=direction*bias.dot(direction)
    along=(a*a-b*b+d*d)/(2*d)
    next_knee=hip+direction*along+bias.normalized()*math.sqrt(max(0,a*a-along*along))
    turn=(knee-hip).rotation_difference(next_knee-hip).to_matrix()
    translation=local[upper].translation.copy()
    local[upper]=(g[parents[upper]].to_3x3().transposed()@turn@g[upper].to_3x3()).to_4x4();local[upper].translation=translation
    g=globals_from(local,parents)
    relative=bind[names[fore]].inverted()@bind[names[foot]]
    desired=goal.to_3x3()@relative.to_3x3().transposed()
    turn=(desired@relative.translation).rotation_difference(goal.translation-next_knee).to_matrix()
    translation=local[fore].translation.copy()
    local[fore]=(g[upper].to_3x3().transposed()@turn@desired).to_4x4();local[fore].translation=translation
    g=globals_from(local,parents);translation=local[foot].translation.copy()
    local[foot]=(g[fore].to_3x3().transposed()@goal.to_3x3()).to_4x4();local[foot].translation=translation

stats=[]
for track in tracks:
    name=track['key']
    if name not in ('vf_slide_start_0','vf_slide_loop_0','vf_slide_end_0'):continue
    addon.select_track(scene,name);frames=[]
    for f in range(1,track['frames']+1):
        evaluate(f);frames.append([m.copy()for m in addon.locals_from(result,names,parents)])
    action=controls.animation_data.action.copy();action.name='SHORT_SLIDE|'+name;action.use_fake_user=True
    controls.animation_data.action=action;previous={}
    for f,original in enumerate(frames,1):
        evaluate(f);t=(f-1)/(track['frames']-1)
        weight=smooth(t)if 'start' in name else 1-smooth(t)if 'end' in name else 1.
        local=[m.copy()for m in original];g=globals_from(local,parents)
        goal=g[ids[2]].copy()
        # World (+3,+6,-14): the right sole crosses underneath the LEFT
        # buttock. The knee remains ahead/right, outside the other shin.
        goal.translation=goal.translation.lerp(Vector((6,-3,-14)),weight)
        rotation=Matrix.Rotation(-math.pi/2,3,'Z')@Matrix(slide_tucked_foot_rotation())
        goal_rotation=goal.to_quaternion().slerp(rotation.to_quaternion(),weight).to_matrix()
        goal=goal_rotation.to_4x4();goal.translation=g[ids[2]].translation.lerp(Vector((6,-3,-14)),weight)
        # Preserve the original knee at the equipped endpoints.
        pole=g[ids[1]].translation.lerp(Vector((-9,-18,-11)),weight)
        if weight>1.e-8:solve(local,goal,pole)
        for i in ids:
            control=next(c for c,n in mapping.items()if n==names[i]);pb=controls.pose.bones[control]
            rest=pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local
            basis=rest.inverted()@local[i];pb.location=basis.translation
            pb.rotation_euler=basis.to_quaternion().to_euler('XYZ',previous.get(control,pb.rotation_euler))
            previous[control]=pb.rotation_euler.copy()
            for prop in('location','rotation_euler'):pb.keyframe_insert(prop,frame=f,group=control)
        bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
        if f in(1,round(track['frames']/2),track['frames']):
            actual=globals_from(addon.locals_from(result,names,parents),parents)
            stats.append(dict(track=name,frame=f,leg={names[i]:list(actual[i].translation)for i in ids}))
    for slot in action.slots:
        for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
            for point in curve.keyframe_points:point.interpolation='LINEAR'
    track['control_action']=action.name;scene['vf_tracks']=json.dumps(tracks)
    addon.select_track(scene,name);addon.export_smd(scene,exports/(name+'.smd'))
scene['vf_exports']='//../retouches/left-seat-slide/third-person'
scene['vf_pose_revision']='Glissade : pied droit sous la fesse gauche, genou droit devant et à droite.'
scene.vf_gesture='vf_slide_loop_0';addon.select_track(scene,'vf_slide_loop_0');evaluate(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==sha
(out/'third-person.json').write_text(json.dumps(dict(baseline=str(baseline),baseline_sha256=sha,revision=str(destination),exports=str(exports),stats=stats),indent=2))
print('SAVED SHORT SLIDE',destination,flush=True)

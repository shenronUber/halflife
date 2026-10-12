"""Author readable FP mantle and forward-looking TP slide in the Blender rigs."""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import globals_from

scene=bpy.context.scene;source,controls,result=addon.objects(scene)
view=scene['vf_view'];baseline=Path(bpy.data.filepath)
before=hashlib.sha256(baseline.read_bytes()).hexdigest()
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
mapping=json.loads(controls['vf_mapping']);tracks=addon.tracks(scene)
out=baseline.parent/'verification/climb-slide';out.mkdir(parents=True,exist_ok=True)
exports=baseline.parent.parent/'retouches/climb-slide'/view;exports.mkdir(parents=True,exist_ok=True)
destination=baseline.parent/('Mains-R1-climb-lisible.blend'if view=='first-person'else'Corps-R1-glissade-regard.blend')

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def blend(a,b,t):
    m=a.to_quaternion().slerp(b.to_quaternion(),t).to_matrix().to_4x4()
    m.translation=a.translation.lerp(b.translation,t);return m

def evaluate(f):
    scene.frame_set(f);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def key(pb,basis,f,previous):
    pb.location=basis.translation
    pb.rotation_euler=basis.to_quaternion().to_euler('XYZ',previous.get(pb.name,pb.rotation_euler))
    previous[pb.name]=pb.rotation_euler.copy()
    for prop in ('location','rotation_euler'):pb.keyframe_insert(prop,frame=f,group=pb.name)

def rest(pb):return pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local if pb.parent else pb.bone.matrix_local

addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
idle_control={pb.name:pb.matrix.copy()for pb in controls.pose.bones}
idle_local=addon.locals_from(result,names,parents)
normal_key='vf_climb_0';addon.select_track(scene,normal_key)
normal_track=next(t for t in tracks if t['key']==normal_key)
evaluate(normal_track['frames'])
normal_local=addon.locals_from(result,names,parents);normal_g=globals_from(normal_local,parents)
normal_control={pb.name:pb.matrix.copy()for pb in controls.pose.bones}
stats=[]
wanted=['vf_climb_0']if view=='first-person'else['vf_slide_start_0','vf_slide_loop_0','vf_slide_end_0']

for track in tracks:
    name=track['key']
    if name not in wanted:continue
    addon.select_track(scene,name)
    frames=[]
    for f in range(1,track['frames']+1):
        evaluate(f);frames.append([m.copy()for m in addon.locals_from(result,names,parents)])
    action=controls.animation_data.action.copy();action.name='CLIMB_SLIDE|'+name;action.use_fake_user=True
    controls.animation_data.action=action;previous={}
    for f,original in enumerate(frames,1):
        evaluate(f);t=(f-1)/(track['frames']-1)
        if view=='first-person':
            # SMD forward is -Y. The held pose is constrained by the renderer;
            # use that actual camera-space grip instead of rotating it sideways
            # towards an equipped stance while the hands are still visible.
            for side,sign in [('G',1),('D',-1)]:
                initial=Matrix.Rotation(-math.pi/2,4,'Z')@idle_control['Main_'+side]
                press=smooth(t/.42)
                hand=initial.copy();hand.translation+=Vector((sign*1.2*press,0,-25*press))
                withdraw=smooth((t-.42)/.24)
                low=initial.copy();low.translation=Vector((sign*8.5,-18.,-23.))
                hand=blend(hand,low,withdraw)
                recover=smooth((t-.68)/.32)
                hand=blend(hand,normal_control['Main_'+side],recover)
                pole=Matrix.Identity(4);pole.translation=Vector((sign*18.,-5.,-17.))
                # Start elbows below and outside the frame. Blend to the real
                # equipped poles only after both palms have left the image.
                pole=blend(pole,normal_control['Coude_'+side],recover)
                for control,goal in [('Main_'+side,hand),('Coude_'+side,pole)]:
                    pb=controls.pose.bones[control]
                    key(pb,pb.bone.matrix_local.inverted()@goal,f,previous)
            curl=smooth((t-.44)/.44)
            for control,bone in mapping.items():
                if not control.startswith(('G_','D_')):continue
                i=names.index(bone);pb=controls.pose.bones[control]
                key(pb,rest(pb).inverted()@blend(idle_local[i],normal_local[i],curl),f,previous)
        else:
            local=[m.copy()for m in original];g=globals_from(local,parents)
            amount=smooth(t)if name=='vf_slide_start_0'else 1-smooth(t)if name=='vf_slide_end_0'else 1.
            # Counter the torso's seated recline. A small downward gaze sees
            # the route ahead; distributing the compensation avoids a kink.
            for bone,down in [('Bip01 Neck',3.),('Bip01 Head',5.)]:
                i=names.index(bone);p=parents[i]
                target=Matrix.Rotation(math.radians(down),3,'X')@normal_g[i].to_3x3()
                rotation=g[i].to_quaternion().slerp(target.to_quaternion(),amount).to_matrix()
                translation=local[i].translation.copy()
                local[i]=(g[p].to_3x3().transposed()@rotation).to_4x4();local[i].translation=translation
                g=globals_from(local,parents)
                control=next(c for c,n in mapping.items()if n==bone);pb=controls.pose.bones[control]
                key(pb,rest(pb).inverted()@local[i],f,previous)
        bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
        assert not result.get('vf_reach_warning'),(name,f,result.get('vf_reach_warning'))
        if f in (1,round(track['frames']/2),track['frames']):
            stats.append(dict(track=name,frame=f,controls={n:list(controls.pose.bones[n].matrix.translation)for n in ('Main_G','Main_D','Coude_G','Coude_D')if n in controls.pose.bones}))
    for slot in action.slots:
        for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
            for point in curve.keyframe_points:point.interpolation='LINEAR'
    track['control_action']=action.name;scene['vf_tracks']=json.dumps(tracks)
    addon.select_track(scene,name);addon.export_smd(scene,exports/(name+'.smd'))
    print('REFINED CLIMB SLIDE',view,name,flush=True)
scene['vf_exports']='//../retouches/climb-slide/'+view
scene['vf_pose_revision']='Montée subjective : appui, poussée, retrait ; glissade : regard vers la trajectoire.'
scene.vf_gesture=wanted[0];addon.select_track(scene,wanted[0]);evaluate(1)
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==before
(out/(view+'.json')).write_text(json.dumps(dict(baseline=str(baseline),baseline_sha256=before,
    revision=str(destination),gestures=wanted,exports=str(exports),stats=stats),indent=2))
print('SAVED',destination)

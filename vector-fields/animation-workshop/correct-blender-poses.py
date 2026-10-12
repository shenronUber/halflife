"""Author a separate, editable hand-pose revision in the Blender workshop.

Use --preview for grasp studies, then run normally to save the revision.
Only animator control actions are changed; the source rig stays intact.
"""
import json
import math
import sys
import hashlib
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
import vf_workshop as addon

BASE = Path(bpy.data.filepath).parent
OUT = BASE / 'verification/postures'
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
source, controls, result = addon.objects(scene)
FINGERS = ('Index','Majeur','Annulaire','Auriculaire')


def rz(a):
    return Matrix.Rotation(a, 3, 'Z')


def rx(a):
    return Matrix.Rotation(a, 3, 'X')


def rest_local(bone):
    return bone.parent.matrix_local.inverted() @ bone.matrix_local


def grasp(side, angles=(30,75,92,96)):
    """Orient finger pads with a common palm plane, without axial twisting."""
    desired = {}
    hand = controls.pose.bones['Main_'+side].matrix.copy()
    for finger in FINGERS:
        chain = [controls.pose.bones[f'{side}_{finger}_{i}'] for i in range(1,5)]
        splay = {'Index': 1.5, 'Majeur': .5, 'Annulaire': -.5, 'Auriculaire': -2}[finger]
        splay *= 1 if side == 'G' else -1
        for i, pb in enumerate(chain):
            next_bone = chain[min(i+1,3)]
            offset = rest_local(next_bone.bone).translation
            # At the last phalanx keep the same anatomical roll as its parent.
            if i == 3:
                offset = rest_local(pb.bone).translation
            alignment = math.atan2(offset.x, offset.y)
            rotation = hand.to_3x3() @ rz(math.radians(splay)) @ rx(math.radians(angles[i])) @ rz(alignment)
            desired[pb.name] = rotation
    thumb = [controls.pose.bones[f'{side}_Pouce_{i}'] for i in range(1,4)]
    sign = 1 if side == 'G' else -1
    for i, pb in enumerate(thumb):
        offset = rest_local(thumb[min(i+1,2)].bone).translation
        if i == 2:
            offset = rest_local(pb.bone).translation
        alignment = math.atan2(offset.x, offset.y)
        # Bring the thumb alongside the index, with its pad over the edge.
        outward = (14,36,36)[i] * sign
        rotation = hand.to_3x3() @ rz(-math.radians(outward)) @ rx(math.radians((0,0,85)[i])) @ rz(alignment)
        desired[pb.name] = rotation
    values = {}
    for name, global_rotation in desired.items():
        pb = controls.pose.bones[name]
        parent_rotation = desired.get(pb.parent.name, hand.to_3x3())
        local = (parent_rotation.transposed() @ global_rotation).to_4x4()
        rest = rest_local(pb.bone)
        local.translation = rest.translation
        values[name] = rest.inverted() @ local
    return values


def apply_values(values, frame, weight=1., neutral=None):
    for name, target in values.items():
        pb = controls.pose.bones[name]
        initial = neutral[name] if neutral else pb.rotation_euler.to_quaternion()
        rotation = initial.slerp(target.to_quaternion(), weight)
        euler = rotation.to_euler('XYZ', pb.rotation_euler)
        pb.rotation_euler = euler
        pb.keyframe_insert('rotation_euler', frame=frame, group=name)


def setup_render():
    for obj in scene.objects:
        if obj.name.startswith('Repère'):
            obj.hide_render = True
    center = sum((controls.pose.bones['Main_'+s].matrix.translation for s in ('G','D')),Vector())*.5
    center += Vector((0,0,-2))
    data=bpy.data.cameras.new('Diagnostic posture'); camera=bpy.data.objects.new('Diagnostic posture',data)
    scene.collection.objects.link(camera); scene.camera=camera
    data.type='ORTHO'; data.ortho_scale=32
    for label, offset, power in [('Key',(-25,-25,35),18000),('Fill',(-15,25,20),12000)]:
        data=bpy.data.lights.new(label,'AREA');data.energy=power;data.size=25
        obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj)
        obj.location=center+Vector(offset)
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=32
    scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
    scene.view_settings.view_transform='Standard'
    return camera, center


def render(camera, center, label, offset):
    bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
    camera.location=center+Vector(offset)
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(label+'.png'))
    bpy.ops.render.render(write_still=True)


def main():
    addon.select_track(scene,'vf_hang_idle_0')
    camera, center = setup_render()
    if '--preview' in sys.argv:
        original = controls.animation_data.action
        for label,angles in [('study-A',(10,75,90,93)),('study-B',(30,75,92,96)),('study-C',(50,80,93,96))]:
            controls.animation_data.action = original.copy()
            scene.frame_set(1);bpy.context.view_layer.update()
            values = {**grasp('G',angles), **grasp('D',angles)}
            apply_values(values,1)
            render(camera,center,label+'-front',(-45,0,7))
            render(camera,center,label+'-oblique',(-30,-30,24))
        return
    destination = BASE/'Mains-R1-poses-corrigees.blend'
    if destination.exists():
        raise FileExistsError('Preserve the existing revision: '+str(destination))
    baseline = Path(bpy.data.filepath)
    baseline_hash = hashlib.sha256(baseline.read_bytes()).hexdigest()
    tracks = addon.tracks(scene)
    modified=[];max_wrist_error=0.;max_length_error=0.;max_weapon_error=0.
    # The release pose is the original weapon idle, shared by the transitions.
    addon.select_track(scene,'vf_hang_catch_0')
    scene.frame_set(1);bpy.context.view_layer.update()
    neutral = {pb.name:pb.rotation_euler.to_quaternion().copy() for pb in controls.pose.bones if pb.name.startswith(('G_','D_'))}
    exports=BASE.parent/'retouches/postures-corrigees/first-person'
    exports.mkdir(parents=True,exist_ok=True)
    for track in tracks:
        key=track['key']
        if 'slide' in key:
            continue
        addon.select_track(scene,key)
        original=bpy.data.actions[track['control_action']]
        revision=original.copy();revision.name='POSES|'+key;revision.use_fake_user=True
        controls.animation_data.action=revision
        for frame in range(1,track['frames']+1):
            scene.frame_set(frame);bpy.context.view_layer.update()
            before={n:result.pose.bones[n].matrix.copy() for n in ('Bone42','Bone07')}
            weapon_before={pb.name:pb.matrix_basis.copy() for pb in controls.pose.bones if pb.name.startswith('D_')}
            t=(frame-1)/(track['frames']-1)
            smooth=lambda x: (lambda u:u*u*(3-2*u))(max(0.,min(1.,x)))
            weight=1.
            if key=='vf_hang_catch_0':weight=smooth(t)
            elif key=='vf_drop_0':weight=1-smooth(t)
            elif key=='vf_climb_0':weight=1-smooth((t-.48)/.35)
            elif key=='vf_vault_0':weight=smooth(min(1.,t/.2)*min(1.,(1-t)/.28))
            left=grasp('G')
            apply_values(left,frame,weight,neutral if key in ('vf_hang_catch_0','vf_climb_0','vf_drop_0','vf_vault_0') else None)
            if 'aim_' not in key:
                right=grasp('D')
                right_weight=1-smooth(t) if key=='vf_hang_arm_0' else weight
                apply_values(right,frame,right_weight,neutral if key in ('vf_hang_catch_0','vf_climb_0','vf_drop_0','vf_vault_0','vf_hang_arm_0') else None)
            bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
            for name in before:
                max_wrist_error=max(max_wrist_error,max(abs(x-y) for ra,rb in zip(before[name],result.pose.bones[name].matrix) for x,y in zip(ra,rb)))
            if 'aim_' in key:
                max_weapon_error=max(max_weapon_error,max(abs(x-y) for n,m in weapon_before.items() for ra,rb in zip(m,controls.pose.bones[n].matrix_basis) for x,y in zip(ra,rb)))
            names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
            actual=addon.locals_from(result,names,parents);authored=addon.locals_from(source,names,parents)
            max_length_error=max(max_length_error,max(abs(a.translation.length-b.translation.length) for a,b in zip(actual[1:],authored[1:])))
        for slot in revision.slots:
            bag=revision.layers[0].strips[0].channelbag(slot)
            for curve in bag.fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
        track['control_action']=revision.name
        # Update the track list before export, so frame handlers use the revision.
        scene['vf_tracks']=json.dumps(tracks)
        addon.select_track(scene,key)
        addon.export_smd(scene,exports/(key+'.smd'))
        modified.append(key)
        print('Corrected',key,flush=True)
    assert max_wrist_error<.005,max_wrist_error
    assert max_length_error<.001,max_length_error
    assert max_weapon_error<.0001,max_weapon_error
    scene.vf_gesture='vf_hang_idle_0'
    addon.select_track(scene,'vf_hang_idle_0')
    bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
    # The old guide intersected the palm. Its edge now starts behind the palms.
    board=next(o for o in scene.objects if o.name.startswith('Repère'))
    board.location=(24.8,-.3,5.05);board.dimensions=(10,36,6)
    board.hide_render=False;board.display_type='WIRE'
    board['note']='Repère visuel de la prise de suspension ; ne fait pas partie de l’export SMD.'
    render(camera,center,'after-ledge',(-30,-30,24))
    board.hide_render=True
    render(camera,center,'after-front',(-45,0,7))
    render(camera,center,'after-oblique',(-30,-30,24))
    render(camera,center,'after-side',(-5,-45,6))
    board.hide_render=False
    scene['vf_exports']='//../retouches/postures-corrigees/first-person'
    scene['vf_pose_revision']='Courbure régulière des phalanges, suppression de la torsion des doigts, pouces rapprochés du rebord.'
    report=dict(baseline=str(baseline),baseline_sha256=baseline_hash,revision=str(destination),
        gestures=modified,export_directory=str(exports),frames=sum(t['frames'] for t in tracks if t['key'] in modified),
        max_wrist_matrix_change=max_wrist_error,max_bone_length_change=max_length_error,max_armed_right_hand_change=max_weapon_error)
    (OUT/'corrections.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    text=bpy.data.texts.new('A LIRE - poses corrigées')
    text.write('Révision séparée de Mains-R1.blend.\nLes animations SOURCE et les commandes RETouche initiales sont conservées.\nLes gestes POSES utilisent une courbure progressive et une orientation cohérente des doigts.\nLa main droite des poses de tir est conservée.\nLe rebord gris est un repère ajustable, affiché en fil de fer dans la vue.\nLes exports vont dans retouches/postures-corrigees/first-person.\nCette révision n’est pas encore installée dans le jeu.\n')
    # Keep render cameras/lights out of the animator's viewport.
    for obj in scene.objects:
        if obj.type in ('CAMERA','LIGHT'):obj.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=Vector((19,-.3,3))
                area.spaces.active.region_3d.view_distance=37
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
    print(json.dumps(report),flush=True)


main()

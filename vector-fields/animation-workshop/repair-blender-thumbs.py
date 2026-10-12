"""Study and repair thumb articulation without twisting the terminal bone.

Thumb bending uses the anatomical axis of the original thumb, not the X axis
of a long finger. Terminal-bone roll stays aligned with the preceding bone.
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
import vf_workshop as addon

scene=bpy.context.scene
source,controls,result=addon.objects(scene)
BASE=Path(bpy.data.filepath).parent
OUT=BASE/'verification/postures/pouces';OUT.mkdir(parents=True,exist_ok=True)


def local_rest(bone):
    return bone.parent.matrix_local.inverted()@bone.matrix_local


def thumb_pose(side,adduction=25,flexion=10,tip_flexion=5):
    chain=[controls.pose.bones[f'{side}_Pouce_{i}'] for i in range(1,4)]
    hand=controls.pose.bones['Main_'+side].matrix.to_3x3()
    sign=1 if side=='G' else -1
    root=Matrix.Rotation(math.radians(sign*adduction),3,'Z')
    # In the original hand the thumb points diagonally across local X/Y.
    # Flex perpendicular to that diagonal, so its pad does not roll sideways.
    direction=local_rest(chain[2].bone).translation.normalized()
    axis=direction.cross(Vector((0,0,1))).normalized()
    middle=root@Quaternion(axis,math.radians(flexion)).to_matrix()
    tip=middle@Quaternion(axis,math.radians(tip_flexion)).to_matrix()
    rotations=[hand@r for r in (root,middle,tip)]
    values={}
    for i,pb in enumerate(chain):
        parent=hand if i==0 else rotations[i-1]
        local=(parent.transposed()@rotations[i]).to_4x4()
        rest=local_rest(pb.bone);local.translation=rest.translation
        values[pb.name]=rest.inverted()@local
    return values


def apply(values,frame,weight=1.,neutral=None,previous=None):
    for name,matrix in values.items():
        pb=controls.pose.bones[name]
        q=(neutral[name] if neutral else pb.rotation_euler.to_quaternion()).slerp(matrix.to_quaternion(),weight)
        euler=q.to_euler('XYZ',previous.get(name,pb.rotation_euler) if previous is not None else pb.rotation_euler)
        pb.rotation_euler=euler
        if previous is not None:previous[name]=euler.copy()
        pb.keyframe_insert('rotation_euler',frame=frame,group=name)


def setup_render():
    for obj in scene.objects:
        if obj.name.startswith('Repère'):obj.hide_render=True
    center=Vector((19,-.3,5))
    data=bpy.data.cameras.new('Diagnostic pouces');camera=bpy.data.objects.new('Diagnostic pouces',data)
    scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.ortho_scale=26
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=32
    scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    return camera,center


def render(camera,center,label,offset):
    bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
    camera.location=center+Vector(offset)
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)


def main():
    addon.select_track(scene,'vf_hang_idle_0')
    camera,center=setup_render()
    original=controls.animation_data.action
    render(camera,center,'avant-face',(-45,0,4))
    if '--preview' in sys.argv:
        for label,parameters in [('A',(15,0,0)),('B',(25,10,5)),('C',(35,20,10))]:
            controls.animation_data.action=original.copy()
            scene.frame_set(1);bpy.context.view_layer.update()
            apply({**thumb_pose('G',*parameters),**thumb_pose('D',*parameters)},1)
            render(camera,center,label+'-face',(-45,0,4))
            render(camera,center,label+'-oblique',(-30,-30,24))
        return
    destination=BASE/'Mains-R1-pouces-corriges.blend'
    if destination.exists():raise FileExistsError(str(destination))
    tracks=addon.tracks(scene)
    addon.select_track(scene,'vf_hang_catch_0');scene.frame_set(1);bpy.context.view_layer.update()
    neutral={pb.name:pb.rotation_euler.to_quaternion().copy() for pb in controls.pose.bones if '_Pouce_' in pb.name}
    modified=[];max_other_bone_change=0.;max_tip_joint_angle=0.
    exports=BASE.parent/'retouches/postures-corrigees/first-person'
    for track in tracks:
        key=track['key']
        if 'slide' in key:continue
        addon.select_track(scene,key)
        revision=controls.animation_data.action.copy()
        revision.name='POUCES|'+key;revision.use_fake_user=True
        controls.animation_data.action=revision
        previous={}
        for frame in range(1,track['frames']+1):
            scene.frame_set(frame);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
            before={pb.name:pb.matrix.copy() for pb in result.pose.bones if pb.name not in ('Bone43','Bone44','Bone45','VFRight_Bone43','VFRight_Bone44','VFRight_Bone45')}
            t=(frame-1)/(track['frames']-1)
            smooth=lambda x:(lambda u:u*u*(3-2*u))(max(0.,min(1.,x)))
            weight=1.
            if key=='vf_hang_catch_0':weight=smooth(t)
            elif key=='vf_drop_0':weight=1-smooth(t)
            elif key=='vf_climb_0':weight=1-smooth((t-.48)/.35)
            elif key=='vf_vault_0':weight=smooth(min(1.,t/.2)*min(1.,(1-t)/.28))
            apply(thumb_pose('G'),frame,weight,neutral if key in ('vf_hang_catch_0','vf_climb_0','vf_drop_0','vf_vault_0') else None,previous)
            if 'aim_' not in key:
                right_weight=1-smooth(t) if key=='vf_hang_arm_0' else weight
                apply(thumb_pose('D'),frame,right_weight,neutral if key in ('vf_hang_catch_0','vf_climb_0','vf_drop_0','vf_vault_0','vf_hang_arm_0') else None,previous)
            bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
            for name,matrix in before.items():
                max_other_bone_change=max(max_other_bone_change,max(abs(x-y) for ra,rb in zip(matrix,result.pose.bones[name].matrix) for x,y in zip(ra,rb)))
            if key=='vf_hang_idle_0':
                for side in ('G','D'):
                    q=controls.pose.bones[side+'_Pouce_3'].rotation_euler.to_quaternion()
                    angle=q.angle;max_tip_joint_angle=max(max_tip_joint_angle,min(angle,abs(2*math.pi-angle)))
        for slot in revision.slots:
            for curve in revision.layers[0].strips[0].channelbag(slot).fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
        track['control_action']=revision.name;scene['vf_tracks']=json.dumps(tracks)
        addon.select_track(scene,key)
        addon.export_smd(scene,exports/(key+'.smd'))
        modified.append(key)
    assert max_other_bone_change<.001,max_other_bone_change
    assert max_tip_joint_angle<math.radians(6),max_tip_joint_angle
    scene.vf_gesture='vf_hang_idle_0';addon.select_track(scene,'vf_hang_idle_0')
    render(camera,center,'apres-face',(-45,0,4))
    render(camera,center,'apres-oblique',(-30,-30,24))
    render(camera,center,'apres-profil',(-5,-45,6))
    board=next(o for o in scene.objects if o.name.startswith('Repère'))
    board.hide_render=False
    render(camera,center,'apres-rebord',(-30,-30,24))
    for obj in scene.objects:
        if obj.type in ('CAMERA','LIGHT'):obj.hide_set(True)
    scene['vf_pose_revision']='Pouces : orientation neutre préservée, flexion anatomique limitée à 10° + 5°, sans torsion de la dernière phalange.'
    text=bpy.data.texts.new('A LIRE - correction des pouces')
    text.write('Cette version corrige les pouces de la première révision.\nLa flexion se fait perpendiculairement à l’axe diagonal du pouce d’origine.\nL’articulation intermédiaire fléchit de 10 degrés et la pointe de 5 degrés.\nLes autres doigts, les poignets, les bras et la pose de tir sont conservés.\nLes actions actives portent le préfixe POUCES|.\nLe jeu n’est pas modifié.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    report_path=BASE/'verification/postures/corrections.json'
    report=json.loads(report_path.read_text(encoding='utf-8'))
    report['revision']=str(destination)
    report['thumb_revision']=dict(adduction_degrees=25,middle_flexion_degrees=10,tip_flexion_degrees=5,
        max_tip_joint_degrees=math.degrees(max_tip_joint_angle),max_other_bone_matrix_change=max_other_bone_change,
        axial_twist_applied=False,visual_checks=['front','oblique','side'])
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('THUMBS',json.dumps(report['thumb_revision']),flush=True)


main()

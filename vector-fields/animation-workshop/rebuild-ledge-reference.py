"""Reconstruct a dorsal ledge grip from the user's image and source hand motion.

The rest anatomy, bone names and lengths remain those of the R1 hands. The
previous palm-facing grip is replaced, not used as an artistic starting pose.
"""
import json
import math
import sys
import hashlib
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector
import vf_workshop as addon

scene=bpy.context.scene
source,controls,result=addon.objects(scene)
BASE=Path(bpy.data.filepath).parent
OUT=BASE/'verification/reference-rebord';OUT.mkdir(exist_ok=True,parents=True)
DONOR=json.loads((OUT/'donor-fingers.json').read_text())
PALM=Vector((.3,3,-1))
PAD=Vector((.3,3,-1.45))
FINGERS={'Index':'Index','Majeur':'Middle','Annulaire':'Ring','Auriculaire':'Pinky'}
FRONT=18.;TOP=9.
mesh=bpy.data.objects[scene['vf_mesh']]
SKIN={}
for vertex in mesh.data.vertices:
    group=next(g for g in vertex.groups if g.weight>.99)
    name=mesh.vertex_groups[group.group].name
    bone=result.data.bones[name]
    SKIN.setdefault(name,[]).append(bone.matrix_local.inverted()@vertex.co)
MAPPING=json.loads(controls['vf_mapping'])


def local_rest(bone):
    return bone.parent.matrix_local.inverted()@bone.matrix_local


def pad(side):
    return Vector((PAD.x if side=='G' else -PAD.x,PAD.y,PAD.z))


def wrist_target(matrix,tilt=20,weight=1.,side='G'):
    # Turn the back of the hand toward the eye, then lean the fingers over the
    # edge. Keep the authored palm contact, including in the camera sectors.
    rotation=matrix.to_3x3()@Matrix.Rotation(math.pi*weight,3,'Y')@Matrix.Rotation(math.radians(-tilt*weight),3,'X')
    target=rotation.to_4x4()
    target.translation=matrix@PALM-rotation@PALM.lerp(pad(side),weight)
    return target


def finger_targets(side,hand,root_curl=12,extra_curl=0,fitted=None,thumb_flex=8):
    rotations={};values={}
    for finger,donor_name in FINGERS.items():
        curls=[sum(DONOR['hands'][s][donor_name]['curl_degrees'][i]for s in ('Left','Right'))*.5 for i in range(3)]
        angles=[root_curl,curls[0]+extra_curl,curls[1]+extra_curl,curls[2]+extra_curl]
        if fitted and finger in fitted:angles=fitted[finger]
        # A small independent gap is preserved between each finger.
        splay={'Index':1.5,'Majeur':.5,'Annulaire':-.5,'Auriculaire':-2}[finger]*(1 if side=='G' else -1)
        chain=[controls.pose.bones[f'{side}_{finger}_{i}']for i in range(1,5)]
        for i,pb in enumerate(chain):
            offset=local_rest(chain[min(i+1,3)].bone).translation if i<3 else local_rest(pb.bone).translation
            alignment=math.atan2(offset.x,offset.y)
            rotations[pb.name]=hand.to_3x3()@Matrix.Rotation(math.radians(splay),3,'Z')@Matrix.Rotation(math.radians(-angles[i]),3,'X')@Matrix.Rotation(alignment,3,'Z')
    # A relaxed thumb spread toward the middle of the screen. Small bends use
    # the diagonal anatomical axis; the terminal phalanx has no axial twist.
    chain=[controls.pose.bones[f'{side}_Pouce_{i}']for i in range(1,4)]
    sign=1 if side=='G' else -1
    root=Matrix.Rotation(math.radians(sign*0),3,'Z')
    direction=local_rest(chain[2].bone).translation.normalized()
    axis=direction.cross(Vector((0,0,1))).normalized()
    middle=root@Quaternion(axis,math.radians(thumb_flex)).to_matrix()
    tip=middle@Quaternion(axis,math.radians(5)).to_matrix()
    for pb,rotation in zip(chain,(root,middle,tip)):
        rotations[pb.name]=hand.to_3x3()@rotation
    for name,rotation in rotations.items():
        pb=controls.pose.bones[name]
        parent=rotations.get(pb.parent.name,hand.to_3x3())
        local=(parent.transposed()@rotation).to_4x4();rest=local_rest(pb.bone)
        local.translation=rest.translation
        values[name]=rest.inverted()@local
    return values


def predicted_fingers(side,hand,values):
    globals_={'Main_'+side:hand};points={}
    for name,value in values.items():
        pb=controls.pose.bones[name]
        globals_[name]=globals_[pb.parent.name]@local_rest(pb.bone)@value
        points[name]=[globals_[name]@p for p in SKIN.get(MAPPING[name],[])]
    return globals_,points


def fit_contacts(side,hand):
    fitted={};report={}
    for finger,donor in FINGERS.items():
        curls=[sum(DONOR['hands'][s][donor]['curl_degrees'][i]for s in ('Left','Right'))*.5 for i in range(3)]
        pip=min(35.,max(18.,curls[1]-curls[0]));dip=min(8.,max(2.,curls[2]-curls[1]))
        best=None
        for step in range(221):
            proximal=25+step*.25
            angles=[12,proximal,proximal+pip,proximal+pip+dip]
            values=finger_targets(side,hand,fitted={**fitted,finger:angles})
            _,points=predicted_fingers(side,hand,values)
            tip=[p for p in points[f'{side}_{finger}_4']if p.x>FRONT+.12]
            if not tip:continue
            gap=min(p.z for p in tip)-TOP
            all_points=[p for segment in range(2,5)for p in points[f'{side}_{finger}_{segment}']if p.x>FRONT+.12]
            penetration=max(0.,TOP-min(p.z for p in all_points))
            cost=abs(gap-.035)+20*max(0.,penetration-.08)**2
            if best is None or cost<best[0]:best=(cost,angles,gap,penetration)
        if best is None:raise ValueError('Finger does not reach the ledge: '+finger)
        fitted[finger]=best[1]
        report[finger]=dict(angles_degrees=best[1],tip_gap=best[2],max_penetration=best[3])
    best=None
    for step in range(41):
        flexion=step*.5
        values=finger_targets(side,hand,fitted=fitted,thumb_flex=flexion)
        _,points=predicted_fingers(side,hand,values)
        contact=[p for p in points[f'{side}_Pouce_3']if p.z<TOP-.2]
        if not contact:continue
        gap=FRONT-max(p.x for p in contact)
        cost=abs(gap-.025)+25*max(0.,-gap-.05)**2
        if best is None or cost<best[0]:best=(cost,flexion,gap)
    report['Pouce']=dict(middle_flexion_degrees=best[1],tip_flexion_degrees=5,front_gap=best[2])
    return fitted,best[1],report


def apply_hand(side,hand,frame,previous=None):
    pb=controls.pose.bones['Main_'+side]
    basis=pb.bone.matrix_local.inverted()@hand
    pb.location=basis.translation
    pb.rotation_euler=basis.to_quaternion().to_euler('XYZ',previous.get(pb.name,pb.rotation_euler) if previous is not None else pb.rotation_euler)
    if previous is not None:previous[pb.name]=pb.rotation_euler.copy()
    for prop in ('location','rotation_euler'):pb.keyframe_insert(prop,frame=frame,group=pb.name)


def apply_fingers(values,frame,weight=1.,neutral=None,previous=None):
    for name,matrix in values.items():
        pb=controls.pose.bones[name]
        quaternion=(neutral[name] if neutral else pb.rotation_euler.to_quaternion()).slerp(matrix.to_quaternion(),weight)
        pb.rotation_euler=quaternion.to_euler('XYZ',previous.get(name,pb.rotation_euler) if previous is not None else pb.rotation_euler)
        if previous is not None:previous[name]=pb.rotation_euler.copy()
        pb.keyframe_insert('rotation_euler',frame=frame,group=name)


def setup_render():
    board=next(o for o in scene.objects if o.name.startswith('Repère'))
    board.location=(28,0,-11);board.dimensions=(20,65,40)
    bpy.context.view_layer.update()
    # Apply the guide's scale before adding a bevel: its width is in SMD units.
    board.data.transform(Matrix.Diagonal((*board.scale,1)));board.scale=(1,1,1)
    board.hide_render=False;board.display_type='SOLID'
    material=bpy.data.materials.new('Rebord - béton neutre');material.diffuse_color=(.26,.28,.29,1)
    board.data.materials.clear();board.data.materials.append(material)
    bevel=board.modifiers.new('Angle du rebord','BEVEL');bevel.width=.14;bevel.segments=3
    camera_data=bpy.data.cameras.new('Vue FPS - référence');camera=bpy.data.objects.new('Vue FPS - référence',camera_data)
    scene.collection.objects.link(camera);scene.camera=camera
    camera.location=(0,0,1.5);camera.rotation_euler=Vector((1,0,0)).to_track_quat('-Z','Y').to_euler()
    camera_data.type='PERSP';camera_data.angle=math.radians(75);camera_data.clip_start=.1;camera_data.clip_end=2000
    for label,position,power,size in [('Lumière supérieure',(-5,-15,30),6000,25),('Lumière douce',(-10,25,18),4000,20)]:
        data=bpy.data.lights.new(label,'AREA');data.energy=power;data.size=size
        obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj);obj.location=position
        obj.rotation_euler=(Vector((18,0,7))-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.37,.52,.66,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64
    scene.render.resolution_x=1448;scene.render.resolution_y=1086;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    return camera,board


def render(label):
    bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
    scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)


def main():
    addon.select_track(scene,'vf_hang_idle_0')
    original=controls.animation_data.action
    camera,board=setup_render()
    if '--contact-study' in sys.argv:
        targets={side:wrist_target(controls.pose.bones['Main_'+side].matrix.copy(),20,side=side)for side in ('G','D')}
        report={}
        for side,hand in targets.items():
            fitted,thumb_flex,report[side]=fit_contacts(side,hand)
            apply_fingers(finger_targets(side,hand,fitted=fitted,thumb_flex=thumb_flex),1)
            apply_hand(side,hand,1)
        (OUT/'contact-study.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        render('prise-contact-FPS')
        camera.data.type='ORTHO';camera.data.ortho_scale=29
        camera.location=(8,-35,16)
        camera.rotation_euler=(Vector((18,0,6))-camera.location).to_track_quat('-Z','Y').to_euler()
        render('prise-contact-oblique')
        board.hide_render=True;render('prise-contact-sans-mur')
        print(json.dumps(report),flush=True)
        return
    if '--preview' in sys.argv:
        for label,tilt,root,extra in [('A',15,5,0),('B',20,12,0),('C',25,15,6)]:
            controls.animation_data.action=original.copy();scene.frame_set(1);bpy.context.view_layer.update()
            targets={side:wrist_target(controls.pose.bones['Main_'+side].matrix.copy(),tilt,side=side)for side in ('G','D')}
            for side,hand in targets.items():
                apply_fingers(finger_targets(side,hand,root,extra),1)
                apply_hand(side,hand,1)
            render('etude-'+label)
            board.hide_render=True;render('etude-'+label+'-sans-mur');board.hide_render=False
        return
    destination=BASE/'Mains-R1-prise-reference.blend'
    if destination.exists():raise FileExistsError(str(destination))
    baseline=Path(bpy.data.filepath);baseline_hash=hashlib.sha256(baseline.read_bytes()).hexdigest()
    fitted={};thumbs={};contacts={}
    for side in ('G','D'):
        hand=wrist_target(controls.pose.bones['Main_'+side].matrix.copy(),side=side)
        fitted[side],thumbs[side],contacts[side]=fit_contacts(side,hand)
    for values in contacts.values():
        for finger in FINGERS:
            assert abs(values[finger]['tip_gap'])<.06
            assert values[finger]['max_penetration']<.05
        assert abs(values['Pouce']['front_gap'])<.04
    tracks=addon.tracks(scene)
    addon.select_track(scene,'vf_hang_catch_0');scene.frame_set(1);bpy.context.view_layer.update()
    neutral={pb.name:pb.rotation_euler.to_quaternion().copy() for pb in controls.pose.bones if pb.name.startswith(('G_','D_'))}
    exports=BASE.parent/'retouches/reference-rebord/first-person'
    modified=[];max_contact_error=0.;max_weapon_error=0.;max_length_error=0.;warnings=[]
    names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
    for track in tracks:
        key=track['key']
        if 'slide' in key:continue
        addon.select_track(scene,key)
        revision=controls.animation_data.action.copy();revision.name='REFERENCE|'+key;revision.use_fake_user=True
        controls.animation_data.action=revision;previous={}
        for frame in range(1,track['frames']+1):
            scene.frame_set(frame);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
            old={side:controls.pose.bones['Main_'+side].matrix.copy()for side in ('G','D')}
            weapon_before={pb.name:pb.matrix.copy()for pb in result.pose.bones if pb.name in ('Bone05','Bone06','Bone07','Bone75','Bone76','Bone71','R01_Bolt') or pb.name.startswith('VFRight_')}
            t=(frame-1)/(track['frames']-1)
            smooth=lambda x:(lambda u:u*u*(3-2*u))(max(0.,min(1.,x)))
            weight=1.
            if key=='vf_hang_catch_0':weight=smooth(t)
            elif key=='vf_drop_0':weight=1-smooth(t)
            elif key=='vf_climb_0':weight=1-smooth((t-.48)/.35)
            elif key=='vf_vault_0':weight=smooth(min(1.,t/.2)*min(1.,(1-t)/.28))
            active={'G':weight}
            if 'aim_' not in key:active['D']=1-smooth(t) if key=='vf_hang_arm_0' else weight
            for side,amount in active.items():
                target=wrist_target(old[side],weight=amount,side=side)
                values=finger_targets(side,target,fitted=fitted[side],thumb_flex=thumbs[side])
                apply_fingers(values,frame,amount,neutral if key in ('vf_hang_catch_0','vf_drop_0','vf_climb_0','vf_vault_0','vf_hang_arm_0') else None,previous)
                apply_hand(side,target,frame,previous)
            bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
            for side,amount in active.items():
                wrist=result.pose.bones['Bone42' if side=='G' else 'Bone07'].matrix
                error=(wrist@PALM.lerp(pad(side),amount)-old[side]@PALM).length
                max_contact_error=max(max_contact_error,error)
            if result.get('vf_reach_warning'):warnings.append([key,frame])
            if 'aim_' in key:
                max_weapon_error=max(max_weapon_error,max(abs(x-y)for n,m in weapon_before.items()for ra,rb in zip(m,result.pose.bones[n].matrix)for x,y in zip(ra,rb)))
            actual=addon.locals_from(result,names,parents);authored=addon.locals_from(source,names,parents)
            max_length_error=max(max_length_error,max(abs(a.translation.length-b.translation.length)for a,b in zip(actual[1:],authored[1:])))
        for slot in revision.slots:
            for curve in revision.layers[0].strips[0].channelbag(slot).fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
        track['control_action']=revision.name;scene['vf_tracks']=json.dumps(tracks)
        addon.select_track(scene,key);addon.export_smd(scene,exports/(key+'.smd'))
        modified.append(key);print('REFERENCE',key,flush=True)
    assert max_contact_error<.01,max_contact_error
    assert max_weapon_error<.001,max_weapon_error
    assert max_length_error<.001,max_length_error
    assert not warnings,warnings
    scene.vf_gesture='vf_hang_idle_0';addon.select_track(scene,'vf_hang_idle_0')
    render('prise-reference-FPS')
    camera.data.type='ORTHO';camera.data.ortho_scale=29;camera.location=(8,-35,16)
    camera.rotation_euler=(Vector((18,0,6))-camera.location).to_track_quat('-Z','Y').to_euler()
    render('prise-reference-oblique')
    board.hide_render=True;render('prise-reference-sans-mur');board.hide_render=False
    camera.data.type='PERSP';camera.data.angle=math.radians(75);camera.location=(0,0,1.5)
    camera.rotation_euler=Vector((1,0,0)).to_track_quat('-Z','Y').to_euler()
    # Pack the supplied image so it remains available beside the editable rig.
    reference_path='C:/Users/Mathieu/AppData/Local/Temp/codex-clipboard-886b0897-69ce-4667-96cc-15d7bd023332.png'
    reference=bpy.data.images.load(reference_path,check_existing=True);reference.name='REFERENCE UTILISATEUR - prise du rebord';reference.pack()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if screen.name=='Layout' and area.type=='DOPESHEET_EDITOR' and area.width<500 and area.height>300:
                # Background Blender defers creation of a new editor space until UI load.
                area.type='IMAGE_EDITOR'
            for editor in area.spaces:
                if editor.type=='IMAGE_EDITOR':editor.image=reference
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_perspective='CAMERA'
                space.overlay.show_relationship_lines=False
    board.display_type='WIRE'
    for obj in scene.objects:
        if obj.type in ('CAMERA','LIGHT'):obj.hide_set(True)
    scene['vf_exports']='//../retouches/reference-rebord/first-person'
    scene['vf_pose_revision']='Prise reconstruite d’après l’image : dos des mains visibles, pouces vers le centre, doigts posés sur le dessus du rebord.'
    scene['vf_grip_pad_G']=list(pad('G'));scene['vf_grip_pad_D']=list(pad('D'))
    note=bpy.data.texts.new('A LIRE - prise de référence')
    note.write('La prise est reconstruite depuis le squelette R1 et l’image fournie.\nHanging_Idle.glb fournit les rapports de courbure PIP/DIP, ajustés au contact du mesh R1.\nLes paumes regardent le mur et les pouces pointent vers le centre.\nLes actions actives portent le préfixe REFERENCE|. Les actions sources sont conservées.\nLe repère de mur est visible en fil de fer dans l’atelier et n’est pas exporté.\nLa référence utilisateur est intégrée au fichier et affichée à droite.\nLes exports sont séparés dans retouches/reference-rebord/first-person. Le jeu n’est pas modifié.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
    report=dict(baseline=str(baseline),baseline_sha256=baseline_hash,revision=str(destination),gestures=modified,
        frames=sum(t['frames']for t in tracks if t['key']in modified),export_directory=str(exports),
        donor='Hanging_Idle.glb',reference_image_packed=True,contacts=contacts,
        max_anchor_error=max_contact_error,max_right_weapon_matrix_change=max_weapon_error,max_bone_length_change=max_length_error,
        reach_warnings=warnings,game_files_deployed=False)
    (OUT/'corrections.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('REFERENCE REPORT',json.dumps(report),flush=True)


if __name__=='__main__':main()

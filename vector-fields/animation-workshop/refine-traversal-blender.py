"""Refine traversal transitions and fit the body grip in editable Blender rigs."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import read_smd,globals_from
from studio_assets import Studio
from traversal_aim import body_turn,head_turn,slide_foot_rotation,slide_tucked_foot_rotation,firing_arm,aim_deploy,weapon_pitch
persona=Studio(ROOT/'generated/personas/persona_scout.mdl')
persona_bind={n:Matrix(m.tolist()) for n,m in zip(persona.names,persona.bind)}
scene=bpy.context.scene;source,controls,result=addon.objects(scene)
view=scene['vf_view'];base=Path(bpy.data.filepath).parent
out=base/'verification/audit-traversal/after';out.mkdir(parents=True,exist_ok=True)
normal_names,normal_parents,normal_frames,_=read_smd(base/'verification/audit-traversal'/(view+'-normal.smd'))
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
assert set(normal_names)==set(names)
for i,name in enumerate(names):
    j=normal_names.index(name);p=normal_parents[j]
    assert (normal_names[p] if p>=0 else None)==(names[parents[i]] if parents[i]>=0 else None)
normal=[normal_frames[0][normal_names.index(name)] for name in names];normal_g=globals_from(normal,parents)
mapping=json.loads(controls['vf_mapping']);inverse_mapping={bone:control for control,bone in mapping.items()}
right_hand=names.index('Bone07') if view=='first-person' else names.index('Bip01 R Hand')
gun=names.index('Bone76') if view=='first-person' else names.index('VF_Weapon')
tracks=addon.tracks(scene)
destination=base/('Mains-R1-revue-complete.blend' if view=='first-person' else 'Corps-R1-revue-complete.blend')
if destination.exists():raise FileExistsError(str(destination))
baseline=Path(bpy.data.filepath);baseline_hash=hashlib.sha256(baseline.read_bytes()).hexdigest()
exports=base.parent/'retouches/revue-complete'/view;exports.mkdir(parents=True,exist_ok=True)

def smooth(t):
    u=max(0.,min(1.,t));return u*u*(3-2*u)

def blend(a,b,t):
    m=a.to_quaternion().slerp(b.to_quaternion(),t).to_matrix().to_4x4()
    m.translation=a.translation.lerp(b.translation,t);return m

def rest(pb):
    return pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local if pb.parent else pb.bone.matrix_local

def key(pb,basis,frame,previous):
    pb.location=basis.translation
    pb.rotation_euler=basis.to_quaternion().to_euler('XYZ',previous.get(pb.name,pb.rotation_euler))
    previous[pb.name]=pb.rotation_euler.copy()
    for prop in ('location','rotation_euler'):pb.keyframe_insert(prop,frame=frame,group=pb.name)

def evaluate(frame):
    scene.frame_set(frame);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def solve(local,ids,goal,pole):
    upper,fore,hand=ids;g=globals_from(local,parents)
    shoulder=g[upper].translation;elbow=g[fore].translation;wrist=g[hand].translation
    a=(elbow-shoulder).length;b=(wrist-elbow).length;delta=goal.translation-shoulder;distance=delta.length
    assert abs(a-b)+.0001<distance<a+b-.0001,('body hand out of reach',ids,distance,a+b)
    direction=delta.normalized();bias=pole-shoulder;bias-=direction*bias.dot(direction)
    if bias.length<.00001:bias=direction.cross(Vector((0,0,1)))
    along=(a*a-b*b+distance*distance)/(2*distance)
    next_elbow=shoulder+direction*along+bias.normalized()*math.sqrt(max(0,a*a-along*along))
    turn=(elbow-shoulder).rotation_difference(next_elbow-shoulder).to_matrix()
    local[upper]=(g[parents[upper]].to_3x3().transposed()@turn@g[upper].to_3x3()).to_4x4();local[upper].translation=(g[parents[upper]].inverted()@g[upper]).translation
    g=globals_from(local,parents)
    relative=persona_bind[names[fore]].inverted()@persona_bind[names[hand]]
    desired=goal.to_3x3()@relative.to_3x3().transposed()
    turn=(desired@relative.translation).rotation_difference(goal.translation-next_elbow).to_matrix()
    translation=local[fore].translation.copy()
    local[fore]=(g[upper].to_3x3().transposed()@turn@desired).to_4x4();local[fore].translation=translation
    g=globals_from(local,parents);translation=local[hand].translation.copy()
    local[hand]=(g[fore].to_3x3().transposed()@goal.to_3x3()).to_4x4();local[hand].translation=translation

addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
idle_poles={side:controls.pose.bones['Coude_'+side].matrix.copy() for side in ('G','D')} if view=='first-person' else None
skin={}
mesh=bpy.data.objects[scene['vf_mesh']]
for vertex in mesh.data.vertices:
    name=mesh.vertex_groups[vertex.groups[0].group].name
    skin.setdefault(name,[]).append(result.data.bones[name].matrix_local.inverted()@vertex.co)

def body_hand(old,amount):
    # Body fingers curl towards local +Y: dorsal is -Y, unlike the FPS rig.
    palm=Vector((1.8,-.2,-.4));rotation=old.to_3x3()@Matrix.Rotation(math.radians(20*amount),3,'Z')
    target=rotation.to_4x4();target.translation=old@palm-rotation@palm;return target

def body_digits(local,side,hand,angles,thumb_angle=0):
    prefix='Bip01 '+side+' ';wanted={}
    hand_rest=persona_bind[prefix+'Hand']
    for suffix,angle in [('Finger1',angles[0]),('Finger11',angles[1]),('Finger0',thumb_angle)]:
        name=prefix+suffix;bind=hand_rest.to_3x3().transposed()@persona_bind[name].to_3x3()
        wanted[name]=hand.to_3x3()@Matrix.Rotation(math.radians(angle),3,'Z')@bind
    g=globals_from(local,parents)
    for suffix in ('Finger1','Finger11','Finger0'):
        name=prefix+suffix;i=names.index(name);p=parents[i]
        rotation=wanted.get(names[p],hand.to_3x3())
        target=(rotation.transposed()@wanted[name]).to_4x4();target.translation=local[i].translation
        local[i]=target
    return local

fitted={};thumbs={};contacts={}
if view=='third-person':
    idle=addon.locals_from(result,names,parents);ig=globals_from(idle,parents)
    for side,hand_index in [('L',17),('R',24)]:
        hand=body_hand(ig[hand_index],1);best=None
        for proximal in range(-90,136,5):
            for pip in range(-75,101,5):
                local=[m.copy() for m in idle];local[hand_index]=(ig[parents[hand_index]].inverted()@hand)
                body_digits(local,side,hand,(proximal,proximal+pip));g=globals_from(local,parents)
                tip=[g[names.index('Bip01 '+side+' Finger11')]@p for p in skin['Bip01 '+side+' Finger11']]
                tip=[p for p in tip if p.y < -18.1]
                if not tip:continue
                all_points=[g[names.index('Bip01 '+side+' '+suffix)]@p for suffix in ('Finger1','Finger11') for p in skin['Bip01 '+side+' '+suffix]]
                all_points=[p for p in all_points if p.y < -18.1]
                gap=min(p.z for p in tip)-40;penetration=max(0.,40-min(p.z for p in all_points))
                cost=abs(gap-.04)+20*max(0.,penetration-.08)**2
                if best is None or cost<best[0]:best=(cost,(proximal,proximal+pip),gap,penetration)
        assert best is not None,side
        fitted[side]=best[1];contacts[side]=dict(angles=list(best[1]),tip_gap=best[2],penetration=best[3]);thumbs[side]=0

def body_pose(original,key_name,t):
    local=[m.copy()for m in original];g=globals_from(local,parents)
    hang=key_name.startswith('vf_hang');armed='aim_' in key_name
    amount=1.
    if key_name=='vf_hang_catch_0':amount=smooth(t)
    elif key_name=='vf_drop_0':amount=1-smooth(t)
    elif key_name=='vf_climb_0':amount=1-smooth((t-.06)/.24)
    elif key_name=='vf_vault_0':amount=smooth(min(1,t/.2)*min(1,(1-t)/.3))
    root_weight=1 if hang else 0.
    if key_name=='vf_hang_catch_0':root_weight=smooth(t)
    elif key_name=='vf_hang_arm_0':root_weight=1.
    elif key_name in ('vf_climb_0','vf_drop_0'):root_weight=1-smooth(t)
    offset=Vector((0,0,-6*root_weight));local[0].translation+=offset
    aim_targets={};aim_poles={}
    if hang and (armed or key_name=='vf_hang_arm_0'):
        alpha=1 if armed else smooth(t)
        yaw,pitch=0.,0.
        if armed:
            _,_,_,sector,corner=key_name.split('_')
            yaw=(int(sector)*45+(-22.5 if int(corner)%2==0 else 22.5)+180)%360-180
            pitch=-70 if int(corner)<2 else 70
        # Preserve the planted waist and both bent legs in WORLD coordinates.
        # The gameplay origin rises 22 units while drawing; compensate it in
        # the model root instead of raising the knees with the camera.
        for i in (*range(8),8,9,10,11):local[i]=corrected_idle[i].copy()
        local[0].translation.z-=22*alpha
        hips,spine,lean=body_turn(yaw,pitch)
        for i,angle,axis in [(i,spine/4,'Z')for i in (8,9,10,11)]+[(i,lean/4,'X')for i in (8,9,10,11)]:
            current=globals_from(local,parents);translation=local[i].translation.copy()
            turn=Matrix.Rotation(math.radians(angle*alpha),3,axis)
            if axis=='X':
                heading=Matrix.Rotation(math.radians(yaw*alpha),3,'Z');turn=heading@turn@heading.transposed()
            local[i]=(current[parents[i]].to_3x3().transposed()@turn@current[i].to_3x3()).to_4x4();local[i].translation=translation
        turn=Matrix.Rotation(math.radians(yaw),3,'Z')@Matrix.Rotation(math.radians(weapon_pitch(yaw,pitch)),3,'X')
        head_yaw,head_pitch=head_turn(yaw,pitch)
        head=Matrix.Rotation(math.radians(head_yaw),3,'Z')@Matrix.Rotation(math.radians(head_pitch),3,'X')
        current=globals_from(local,parents);translation=local[13].translation.copy()
        wanted=current[13].to_quaternion().slerp((head@normal_g[13].to_3x3()).to_quaternion(),alpha).to_matrix()
        local[13]=(current[parents[13]].to_3x3().transposed()@wanted).to_4x4();local[13].translation=translation
        idle_g=globals_from(corrected_idle,parents)
        support=idle_g[17].copy();support.translation.z-=22*alpha
        # Armed player origin rises by 22. Lower the model-space hand by
        # the same amount, leaving its WORLD contact on the same ledge.
        # The firing wrist travels with its shoulder. The support arm uses
        # its anatomical reach; fitting it may not displace the lower body.
        current=globals_from(local,parents)
        reach=(current[23].translation-current[22].translation).length+(current[24].translation-current[23].translation).length
        wrist,pole,crossing=firing_arm(yaw,pitch,reach)
        smd=lambda v:Vector((v[1],-v[0],v[2]))
        right=(turn@normal_g[24].to_3x3()).to_4x4()
        right.translation=current[22].translation+smd(wrist)
        start=idle_g[24].copy();start.translation.z-=22*alpha
        aim_targets={'L':support,'R':blend(start,right,alpha)}
        original_left=idle_g[16].translation.copy();original_left.z-=22*alpha
        low_left=current[15].translation+smd((-4,4,-16))
        aim_poles={'L':original_left.lerp(low_left,min(1.,2*crossing)*alpha),
                   'R':current[22].translation+smd(pole)}
    if 'slide' in key_name:
        weight=smooth(t) if 'start' in key_name else 1-smooth(t) if 'end' in key_name else 1.
        local[0].translation.z-=12*weight
        gslide=globals_from(local,parents);spine=names.index('Bip01 Spine');parent=parents[spine]
        desired=Matrix.Rotation(math.radians(-35),3,'X')@normal_g[spine].to_3x3()
        rotation=gslide[spine].to_quaternion().slerp(desired.to_quaternion(),weight).to_matrix()
        translation=local[spine].translation.copy();local[spine]=(gslide[parent].to_3x3().transposed()@rotation).to_4x4();local[spine].translation=translation
        current=globals_from(local,parents)
        for ids,position,pole in [((2,3,4),(8,-28,-14),(8,-12,0)),((5,6,7),(-3,0,-14),(-4,-18,-11))]:
            orientation=slide_foot_rotation()if ids[0]==2 else slide_tucked_foot_rotation()
            foot=(Matrix.Rotation(math.radians(-90),3,'Z')@Matrix(orientation)).to_4x4()
            target=blend(current[ids[2]],foot,weight);target.translation=current[ids[2]].translation.lerp(Vector(position),weight)
            solve(local,ids,target,Vector(pole))
    if hang or key_name in ('vf_climb_0','vf_drop_0','vf_vault_0'):
        for side,ids in [('L',(15,16,17)),('R',(22,23,24))]:
            weight=amount if side=='L' else 0 if armed else 1-smooth(t) if key_name=='vf_hang_arm_0' else amount
            target=body_hand(g[ids[2]],weight);target.translation+=offset*(1-weight)
            if aim_targets:target=aim_targets[side].copy()
            solve(local,ids,target,aim_poles.get(side,g[ids[1]].translation+offset))
            desired=[m.copy()for m in local];body_digits(desired,side,target,fitted[side],thumbs[side])
            for suffix in ('Finger0','Finger1','Finger11'):
                i=names.index('Bip01 '+side+' '+suffix)
                local[i]=blend(normal[i],desired[i],weight)
        if aim_targets:local[gun]=normal[gun].copy()
    return local

corrected_idle=None
if view=='third-person':
    addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
    corrected_idle=body_pose(addon.locals_from(result,names,parents),'vf_hang_idle_0',0)
modified=[]
for track in tracks:
    key_name=track['key'];addon.select_track(scene,key_name)
    revision=controls.animation_data.action.copy();revision.name='REVUE|'+key_name;revision.use_fake_user=True
    controls.animation_data.action=revision;previous={}
    for frame in range(1,track['frames']+1):
        evaluate(frame);t=(frame-1)/(track['frames']-1)
        if view=='first-person':
            if key_name=='vf_hang_arm_0':
                pb=controls.pose.bones['Coude_D'];wanted=blend(idle_poles['D'],pb.matrix.copy(),smooth(t))
                key(pb,pb.bone.matrix_local.inverted()@wanted,frame,previous)
            if key_name=='vf_hang_arm_0' or 'vf_hang_aim_' in key_name:
                yaw=0.
                if 'aim_' in key_name:
                    _,_,_,sector,corner=key_name.split('_')
                    yaw=(int(sector)*45+(-22.5 if int(corner)%2==0 else 22.5)+180)%360-180
                guard=(1-aim_deploy(yaw))*(smooth(t) if key_name=='vf_hang_arm_0' else 1.)
                pb=controls.pose.bones['Main_D'];wanted=pb.matrix.copy()
                # The equipped R1 points along compiler +X, i.e. SMD -Y.
                # Rotate -Y into +Z without rolling the thumb sideways.
                wanted_rotation=Matrix.Rotation(math.radians(-90*guard),3,'X')@wanted.to_3x3()
                wanted= wanted_rotation.to_4x4();wanted.translation=pb.matrix.translation
                key(pb,pb.bone.matrix_local.inverted()@wanted,frame,previous)
            edge=smooth(min(1,t/.15)) if key_name in ('vf_hang_catch_0','vf_vault_0') else 1.
            if key_name in ('vf_climb_0','vf_drop_0','vf_vault_0'):edge*=1-smooth((t-.8)/.2)
            if edge<1:
                for side,wrist,elbow in [('G',12,10),('D',6,4)]:
                    for control,neutral_matrix in [('Main_'+side,normal_g[wrist]),('Coude_'+side,normal_g[elbow])]:
                        pb=controls.pose.bones[control];wanted=blend(neutral_matrix,pb.matrix.copy(),edge)
                        key(pb,pb.bone.matrix_local.inverted()@wanted,frame,previous)
                for control,bone in mapping.items():
                    if control.startswith(('G_','D_')):
                        pb=controls.pose.bones[control];wanted=blend(normal[names.index(bone)],rest(pb)@pb.matrix_basis,edge)
                        key(pb,rest(pb).inverted()@wanted,frame,previous)
            bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
        else:
            original=addon.locals_from(source,names,parents)
            local=body_pose(original,key_name,t)
            if key_name=='vf_hang_arm_0':
                local=[blend(a,b,smooth(t/.25))for a,b in zip(corrected_idle,local)]
                # The gun stays at a constant socket in the drawing hand.
                local[gun]=normal[gun].copy()
            elif key_name=='vf_hang_catch_0':
                local=[blend(a,b,smooth(t/.25))for a,b in zip(normal,local)]
            elif key_name in ('vf_climb_0','vf_drop_0','vf_vault_0','vf_slide_end_0'):
                local=[blend(a,b,smooth((t-.65)/.35))for a,b in zip(local,normal)]
                if key_name=='vf_vault_0':local=[blend(a,b,smooth(t/.15))for a,b in zip(normal,local)]
            # Body segment offsets come from the original anatomical rig.
            # Only root motion and weapon sockets may translate independently.
            for i,name in enumerate(names):
                if i and name not in {'VF_Weapon','VF_Magazine','VF_Bolt'}:local[i].translation=original[i].translation
            for control,bone in mapping.items():
                pb=controls.pose.bones[control];key(pb,rest(pb).inverted()@local[names.index(bone)],frame,previous)
        bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
    for slot in revision.slots:
        for curve in revision.layers[0].strips[0].channelbag(slot).fcurves:
            for point in curve.keyframe_points:point.interpolation='LINEAR'
    track['control_action']=revision.name;scene['vf_tracks']=json.dumps(tracks)
    addon.select_track(scene,key_name);addon.export_smd(scene,exports/(key_name+'.smd'))
    modified.append(key_name);print('REFINED',view,key_name,flush=True)
scene['vf_exports']='//../retouches/revue-complete/'+view
scene.vf_gesture='vf_hang_idle_0';addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
for obj in scene.objects:
    if obj.type=='MESH' and obj!=mesh and obj.name.startswith('R1 -'):obj.hide_set(True);obj.hide_render=True
scene['vf_pose_revision']='Revue complète : prise dorsale, raccords aux poses R1, corps suspendu et sortie des gestes.'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
report=dict(baseline=str(baseline),baseline_sha256=baseline_hash,revision=str(destination),view=view,
    gestures=modified,frames=sum(t['frames']for t in tracks),export_directory=str(exports),body_grip_contacts=contacts)
(out/('corrections-'+view+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SAVED REVIEW',str(destination),json.dumps(contacts),flush=True)

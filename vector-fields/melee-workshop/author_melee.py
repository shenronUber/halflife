"""Run in Blender. Right-handed overhead barrel strike and released support hand."""
import json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[1];WORK=Path(__file__).resolve().parent;REVIEW=ROOT/'build/fist-refinement/authoring'
REVIEW.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import make_armature
payload=json.loads((WORK/'input.json').read_text())
FISTS=json.loads((WORK/'fist-poses.json').read_text())

def globals_of(local,parents):
    result=[]
    for i,m in enumerate(local):result.append(result[parents[i]]@m if parents[i]>=0 else m.copy())
    return result

def turn(a,b):return a.normalized().rotation_difference(b.normalized()).to_matrix()

def orient(m,r):
    p=m.translation.copy();out=r.to_4x4();out.translation=p;return out

def fist(local,idle,control,fp):
    # Each articulation has an explicit Blender pose. FP fingers curl into
    # -Z; TP fingers curl into +Y (the palm), never backwards through the back.
    for finger,pose in FISTS['fp'if fp else'tp'].items():
        weight=float(control['Fermeture_'+finger])
        for bone,angles in pose.items():
            bone=int(bone);closed=Euler(tuple(math.radians(a)for a in angles),'XYZ').to_quaternion()
            local[bone]=orient(local[bone],idle[bone].to_quaternion().slerp(closed,weight).to_matrix())
    for bone,offset in FISTS.get('offsets',{}).get('fp'if fp else'tp',{}).items():
        bone=int(bone);local[bone].translation=idle[bone].translation+Vector(offset)*float(control['Fermeture_thumb'])

def neutral_wrist(local,parents,fp,release):
    g=globals_of(local,parents);wrist,fore=(12,10)if fp else(17,16)
    forward=(g[wrist].translation-g[fore].translation).normalized()
    up=Vector((0,0,1));up=(up-forward*up.dot(forward)).normalized()
    if fp:x,y=up,forward;z=x.cross(y)
    else:x,z=forward,-up;y=z.cross(x)
    neutral=Matrix((x,y,z)).transposed().to_quaternion()
    rotation=g[wrist].to_quaternion().slerp(neutral,release).to_matrix()
    local[wrist]=orient(local[wrist],g[parents[wrist]].to_3x3().transposed()@rotation)

def left_keys(obj,fp,crouch):
    keys=[(1,(19,7,-10)if fp else(17,10,21)),(5,(19,8,-10)if fp else(17,10,21)),
          (10,(19,8.5,-9)if fp else(17,11,22)),(14,(19,7.5,-10)if fp else(17.5,10,21)),
          (17,(19,7,-10.5)if fp else(17,10,20)),(23,(19,7.5,-10)if fp else(16.5,10,20)),
          (28,(19,7,-10)if fp else(16,9,19)),(34,(19,7,-10)if fp else(17,10,21))]
    for frame,point in keys:
        obj.location=Vector(point)+Vector((0,0,-4 if crouch else 0));obj.keyframe_insert('location',frame=frame)
    for finger,closed_at in [('pinky',7),('ring',8),('middle',9),('index',9),('thumb',11)]:
        prop='Fermeture_'+finger
        for frame,value in [(1,0),(3,0),(5,.12),(closed_at,1),(23,1),(28,1),(31,.25),(34,0)]:
            obj[prop]=value;obj.keyframe_insert('["'+prop+'"]',frame=frame)
    for frame,value in [(1,0),(3,.05),(5,.45),(8,.95),(10,1),(24,1),(28,1),(31,.35),(34,0)]:
        obj['Poignet_neutre']=value;obj.keyframe_insert('["Poignet_neutre"]',frame=frame)
    action=obj.animation_data.action;action.name='Garde gauche / poses manuelles / '+obj.name;action.use_fake_user=True
    for slot in action.slots:
        for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
            for k in curve.keyframe_points:k.interpolation='BEZIER';k.handle_left_type=k.handle_right_type='AUTO_CLAMPED'

def solve(local,parents,goal,fp,right,pole):
    g=globals_of(local,parents)
    shoulder,elbow,wrist=(3,4,6) if fp and right else (3,10,12) if fp else (22,23,24) if right else (15,16,17)
    s,e,w=[g[i].translation.copy() for i in (shoulder,elbow,wrist)]
    a,b=(e-s).length,(w-e).length;d=(goal.translation-s).length
    if not abs(a-b)+.0001<d<a+b-.0001:raise ValueError(('unreachable',item['key'],frame,fp,right,d,a,b))
    direction=(goal.translation-s).normalized();p=pole-s;p-=direction*p.dot(direction);p.normalize()
    along=(a*a-b*b+d*d)/(2*d);new=s+direction*along+p*math.sqrt(max(0,a*a-along*along))
    if fp:
        relative=g[elbow].inverted()@g[wrist];desired=goal.to_3x3()@relative.to_3x3().transposed()
        target=orient(g[elbow],turn(desired@relative.translation,goal.translation-new)@desired);target.translation=new
        local[elbow]=g[parents[elbow]].inverted()@target
    else:
        target=orient(g[shoulder],turn(e-s,new-s)@g[shoulder].to_3x3())
        local[shoulder]=g[parents[shoulder]].inverted()@target
        g=globals_of(local,parents)
        target=orient(g[elbow],turn(g[wrist].translation-g[elbow].translation,goal.translation-g[elbow].translation)@g[elbow].to_3x3())
        local[elbow]=g[parents[elbow]].inverted()@target
    g=globals_of(local,parents);local[wrist]=orient(local[wrist],g[parents[wrist]].to_3x3().transposed()@goal.to_3x3())
    error=(globals_of(local,parents)[wrist].translation-goal.translation).length
    assert error<.0001,error

def mesh(item,rig,names,bind):
    materials=[]
    for path in item['materials']:
        mat=bpy.data.materials.new(Path(path).stem);mat.use_nodes=True
        texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(path,check_existing=True)
        texture.image.pack();shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.65
        mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);materials.append(mat)
    verts=[];faces=[];bones=[];uvs=[];indices=[];normals=[]
    for tex,triangle in item['triangles']:
        start=len(verts);indices.append(tex)
        for v in triangle:
            bone=v['bone'];rebinding=rig.data.bones[names[bone]].matrix_local@bind[bone].inverted()
            verts.append(rebinding@Vector(v['p']));bones.append(bone);uvs.append(v['uv']);normals.append((rebinding.to_3x3()@Vector(v['n'])).normalized())
        faces.append((start,start+1,start+2))
    data=bpy.data.meshes.new(item['name']);data.from_pydata(verts,[],faces);data.update()
    layer=data.uv_layers.new()
    for loop in data.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    for p,index in zip(data.polygons,indices):p.material_index=index;p.use_smooth=True
    data.normals_split_custom_set([normals[loop.vertex_index] for loop in data.loops])
    for material in materials:data.materials.append(material)
    obj=bpy.data.objects.new(item['name'],data);bpy.context.collection.objects.link(obj)
    groups=[obj.vertex_groups.new(name=n) for n in names]
    for i,b in enumerate(bones):groups[b].add([i],1,'REPLACE')
    modifier=obj.modifiers.new('Squelette','ARMATURE');modifier.object=rig

def control_keys(obj,fp):
    # Frames: prise, lâcher, armement, impact, suivi, reprise, retour.
    # Positive pitch lifts the muzzle. It crosses the forward aim at frame 13,
    # then continues below it; the stock stays behind the firing hand.
    keys=[(0,(0,0,0),(0,0,0),0,0),(4,(3,-1,4) if fp else (1,-1,3),(0,25,4),1,-3),
          (9,(13,-2,13) if fp else (1,-1,15),(-8,80,12) if fp else (-8,80,8),1,-8),
          (13,(14,0,10) if fp else (8,3,6),(6,-4,22) if fp else (6,2,0),1,6),
          (16,(13,0,3) if fp else (8,3,-1),(8,-30,20) if fp else (8,-30,-6),1,10),
          (21,(8,0,1) if fp else (4,1,0),(3,-10,10) if fp else (3,-10,-3),1,5),
          (27,(3,0,0) if fp else (1,0,0),(0,4,0),1,1),
          (33,(0,0,0),(0,0,0),0,0)]
    for frame,position,angles,release,torso in keys:
        obj.location=position;obj.rotation_euler=Euler(tuple(math.radians(v) for v in (angles[0],-angles[1],angles[2])),'XYZ')
        obj['Main_libre']=release;obj['Torse']=torso
        for prop in ('location','rotation_euler','["Main_libre"]','["Torse"]'):obj.keyframe_insert(prop,frame=frame+1)
    action=obj.animation_data.action;action.name='Frappe au canon / poses manuelles / '+obj.name;action.use_fake_user=True
    for slot in action.slots:
        for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
            for key in curve.keyframe_points:key.interpolation='BEZIER';key.handle_left_type=key.handle_right_type='AUTO_CLAMPED'

scenes={}
for view in ('fp','tp'):
    scene=bpy.data.scenes.new('Première personne' if view=='fp' else 'Troisième personne');bpy.context.window.scene=scene
    scene.render.fps=30;scene.frame_start=1;scene.frame_end=34;scenes[view]=scene
    for frame,name in ((1,'Prise'),(5,'Lâcher'),(10,'Armement'),(14,'Impact'),(17,'Suivi'),(28,'Reprise'),(34,'Retour')):scene.timeline_markers.new(name,frame=frame)
    for item in [r for r in payload['rigs'] if r['kind']==view]:
        names=item['names'];parents=item['parents'];bind=[Matrix(m) for m in item['bind']];idle=[Matrix(m) for m in item['idle']]
        rig=make_armature(item['key'],names,parents,bind);rig['source']=item['source']
        control=bpy.data.objects.new('Gestuelle / '+item['key'],None);scene.collection.objects.link(control);control.empty_display_type='ARROWS';control.empty_display_size=3
        control.rotation_mode='XYZ';control_keys(control,view=='fp')
        left_control=bpy.data.objects.new('Garde gauche / '+item['key'],None);scene.collection.objects.link(left_control)
        left_control.empty_display_type='SPHERE';left_control.empty_display_size=1;left_keys(left_control,view=='fp',item['crouch'])
        for part in item['meshes']:mesh(part,rig,names,bind)
        rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new('Frappe au canon / '+item['key']);rig.animation_data.action.use_fake_user=True
        g0=globals_of(idle,parents);fp=view=='fp';right=6 if fp else 24;left=12 if fp else 17;gun=40 if fp else 28
        previous={};frames=[]
        for frame in range(1,35):
            scene.frame_set(frame);bpy.context.view_layer.update();local=[m.copy() for m in idle]
            rotation=control.rotation_euler.to_matrix();release=float(control['Main_libre'])
            if item['crouch']:
                # The crouch gait tilts the pelvis (and resting aim) down.
                # Correct it only while the hand is free, so the strike
                # shares the standing world-space arc and still rejoins idle.
                level=turn(g0[gun].to_3x3().col[1],Vector((1,0,0))).to_quaternion()
                rotation=rotation@Matrix.Identity(3).to_quaternion().slerp(level,release).to_matrix()
            if not fp:
                torso=Euler((0,0,math.radians(float(control['Torse']))),'XYZ').to_matrix()
                target=orient(g0[8],torso@g0[8].to_3x3());local[8]=g0[parents[8]].inverted()@target
            target=orient(g0[right],rotation@g0[right].to_3x3());target.translation=g0[right].translation+control.location
            weapon=target@g0[right].inverted()@g0[gun]
            # A compact fighting guard, away from the magazine. Keep the
            # wrist straight instead of rolling an open palm off the grip.
            resting=left_control.location.copy()
            guard=Matrix(((0,1,0),(0,0,1),(1,0,0))) if fp else Matrix(((1,0,0),(0,-1,0),(0,0,-1)))
            relaxed=orient(g0[left],g0[left].to_3x3());relaxed.translation=resting
            support=weapon@g0[gun].inverted()@g0[left]
            support.translation=support.translation.lerp(resting,release)
            support.translation+=rotation@g0[left].to_3x3().col[2]*(math.sin(math.pi*release)*(5 if fp else 3))
            q=support.to_quaternion().slerp(relaxed.to_quaternion(),release);support=orient(support,q.to_matrix())
            weight=math.sin(math.pi*(frame-1)/33)
            solve(local,parents,target,fp,True,g0[4 if fp else 23].translation+Vector((3,-4,-3))*weight)
            solve(local,parents,support,fp,False,g0[10 if fp else 16].translation+Vector((0,4,-3))*weight)
            neutral_wrist(local,parents,fp,float(left_control['Poignet_neutre']))
            fist(local,idle,left_control,fp)
            now=globals_of(local,parents);local[gun]=now[parents[gun]].inverted()@weapon
            for i,name in enumerate(names):
                pb=rig.pose.bones[name];rest=rig.data.bones[name].matrix_local
                if parents[i]>=0:rest=rig.data.bones[names[parents[i]]].matrix_local.inverted()@rest
                pb.matrix_basis=rest.inverted()@local[i]
                if name in previous and pb.rotation_quaternion.dot(previous[name])<0:pb.rotation_quaternion.negate()
                previous[name]=pb.rotation_quaternion.copy()
                for prop in ('location','rotation_quaternion'):pb.keyframe_insert(prop,frame=frame,group=name)
            bpy.context.view_layer.update()
            posed=[rig.pose.bones[name].matrix.copy() for name in names]
            evaluated=[posed[parents[i]].inverted()@m if parents[i]>=0 else m for i,m in enumerate(posed)]
            frames.append(np.array(evaluated))
        assert np.abs(np.array(frames)[[0,-1]]-np.array(idle)).max()<.0001,item['key']
        np.save(WORK/(item['key']+'.npy'),np.array(frames))
        action=rig.animation_data.action
        for slot in action.slots:
            for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
        # Only the primary carrier is visible; all alternatives remain editable.
        primary=item['key']==('r01_rig' if fp else 'r01_tp')
        for obj in list(scene.objects):
            if obj.type=='MESH' and obj.modifiers and obj.modifiers[0].object==rig:obj.hide_render=not primary;obj.hide_set(not primary)
        rig.hide_set(not primary);control.hide_set(not primary)
    camera=bpy.data.objects.new('Camera / '+view,bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera);scene.camera=camera
    if view=='fp':camera.location=(0,0,0);direction=Vector((1,0,0));camera.data.lens=18
    else:camera.location=(80,-80,43);direction=Vector((5,0,-1))-camera.location;camera.data.type='ORTHO';camera.data.ortho_scale=144
    camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();camera.data.clip_start=.05
    scene.world=bpy.data.worlds.new('Fond / '+view);scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.19,.24,1)
    if view=='tp':
        bpy.ops.mesh.primitive_plane_add(size=600,location=(0,0,-36))
        ground=bpy.context.object;ground.name='Sol / appuis fixes';mat=bpy.data.materials.new('Sol');mat.diffuse_color=(.12,.15,.18,1);ground.data.materials.append(mat)
    for name,position,power,size in [('Principale',(20,-40,80),18000,45),('Remplissage',(-20,30,45),12000,35)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position
        obj.rotation_euler=(Vector((10,0,0))-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16
    scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    scene.frame_set(14)
bpy.context.window.scene=scenes['tp'];bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'Frappe-au-canon-R1-poing.blend'))
for view,scene in scenes.items():
    bpy.context.window.scene=scene
    for frame in (1,5,10,14,17,25,34):
        scene.frame_set(frame);scene.render.filepath=str(REVIEW/(view+'_'+str(frame).zfill(2)+'.png'));bpy.ops.render.render(write_still=True)
print('PASS Blender: twelve editable rig actions, eight authored control poses each, grounded third-person torso and attached firing hand')
(WORK/'blender-export.json').write_text(json.dumps(dict(passed=True,rigs=[r['key'] for r in payload['rigs']],frames=34)))

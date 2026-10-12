"""Blender close-up turntables, using the actual animated game geometry."""
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--frames',default='14');parser.add_argument('--colors',action='store_true');parser.add_argument('--views',default='fp,tp');a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
out=ROOT/'build/fist-refinement/review'/a.tag;out.mkdir(parents=True,exist_ok=True)
for view,title,key,wrist in [('fp','Première personne','r01_rig','Bone42'),('tp','Troisième personne','r01_tp','Bip01 L Hand')]:
    if view not in a.views.split(','):continue
    scene=bpy.data.scenes[title];bpy.context.window.scene=scene;rig=scene.objects[key]
    for obj in scene.objects:
        if obj.type=='MESH':obj.hide_render=not(any(m.type=='ARMATURE'and m.object==rig for m in obj.modifiers)and obj.name.startswith('inspect_gloves'if view=='fp'else'persona_scout'))
    # The opposite hand must not obscure the palm-side review.
    order=json.loads(rig['vf_order']);allowed=set(order[10:32]if view=='fp'else order[16:21]+['VF_LThumbTip'])
    for obj in list(scene.objects):
        if obj.type!='MESH'or obj.hide_render:continue
        isolated=obj.copy();isolated.data=obj.data.copy();scene.collection.objects.link(isolated);obj.hide_render=True;isolated.hide_render=False
        drop=[v.index for v in isolated.data.vertices if not any(isolated.vertex_groups[g.group].name in allowed for g in v.groups)]
        bm=bmesh.new();bm.from_mesh(isolated.data);bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.verts[i]for i in drop],context='VERTS');bm.to_mesh(isolated.data);bm.free()
        if a.colors:
            isolated.data.materials.clear()
            colors=[(.55,.55,.55,1),(1,.3,.03,1),(.85,.03,.03,1),(1,.85,.03,1),(.08,.7,.15,1),(.05,.3,1,1)]
            for index,color in enumerate(colors):
                material=bpy.data.materials.new('Anatomie '+str(index));material.diffuse_color=color;material.use_nodes=True
                material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=color
                isolated.data.materials.append(material)
            for face in isolated.data.polygons:
                ids=[order.index(isolated.vertex_groups[g.group].name)for vi in face.vertices for g in isolated.data.vertices[vi].groups]
                bone=max(ids)
                family=1 if 13<=bone<=15 else 2+(bone-16)//4 if 16<=bone<=31 else 0
                if view=='tp':family=1 if bone==18 else 2 if bone in(19,20)else 0
                face.material_index=family
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=32
    scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=13
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.25,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    for obj in scene.objects:
        if obj.type=='LIGHT':obj.hide_render=True
    views={'dos':(4,5,20),'paume':(4,5,-20),'pouce':(20,4,3),'jointures':(4,22,2)}if view=='fp'else{'dos':(4,-20,-3),'paume':(4,20,-3),'pouce':(4,3,-20),'jointures':(22,3,-3)}
    for frame in map(int,a.frames.split(',')):
        scene.frame_set(frame);bpy.context.view_layer.update();hand=rig.matrix_world@rig.pose.bones[wrist].matrix
        target=hand@Vector((0,3,-1)if view=='fp'else(2,0,0))
        for angle,offset in views.items():
            camera=scene.camera;camera.location=hand@Vector(offset)
            z=(camera.location-target).normalized();up=hand.to_3x3()@Vector((1,0,0)if view=='fp'else(0,0,-1))
            if abs(up.dot(z))>.94:up=hand.to_3x3()@Vector((0,1,0)if view=='fp'else(1,0,0))
            x=up.cross(z).normalized();y=z.cross(x);camera.rotation_euler=Matrix((x,y,z)).transposed().to_euler()
            lights=[]
            for label,offset,power in [('Key',(10,-12,12),700),('Fill',(-8,8,9),450)]:
                data=bpy.data.lights.new(label,'AREA');data.energy=power;data.size=8
                obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj);obj.location=target+Vector(offset)
                obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler();lights.append(obj)
            scene.render.filepath=str(out/f'{view}_{frame:02}_{angle}.png');bpy.ops.render.render(write_still=True)
            for obj in lights:bpy.data.objects.remove(obj,do_unlink=True)
print('PASS Blender close-up review',a.tag,flush=True)

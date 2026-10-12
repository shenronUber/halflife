import bpy,json,math
from pathlib import Path
from mathutils import Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
scene=bpy.context.scene;source,controls,result=addon.objects(scene);view=scene['vf_view'];mesh=bpy.data.objects[scene['vf_mesh']]
out=Path(bpy.data.filepath).parent/'verification/audit-traversal/after'/view;report={}
def evaluate(f):
 scene.frame_set(f);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
for obj in scene.objects:
 if obj.type=='MESH' and obj!=mesh:obj.hide_render=True
 if obj.name.startswith('Repère'):obj.hide_render=True
data=bpy.data.cameras.new('Contact');camera=bpy.data.objects.new('Contact',data);scene.collection.objects.link(camera);scene.camera=camera
for position in [(-20,20,65),(30,10,50)]:
 ld=bpy.data.lights.new('Softbox','AREA');ld.energy=18000;ld.size=30;lo=bpy.data.objects.new('Softbox',ld);scene.collection.objects.link(lo);lo.location=position;lo.rotation_euler=(Vector((0,-18,38))-lo.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[1].default_value=.85
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=32
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
# Inspect the actual low-poly fingers against a solid ledge, close enough
# to see thumb direction and interpenetration in both rigs.
addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
bpy.ops.mesh.primitive_cube_add()
ledge=bpy.context.object;ledge.name='Rebord de contrÃ´le'
if view=='first-person':ledge.location=(34,0,-16);ledge.scale=(16,35,25)
else:ledge.location=(0,-34,0);ledge.scale=(35,16,40)
material=bpy.data.materials.new('Pierre de contrÃ´le');material.diffuse_color=(.24,.27,.3,1);ledge.data.materials.append(material)
target=Vector((18,0,7)) if view=='first-person' else Vector((0,-18,38))
positions=[(-12,0,24),(13,-38,19)] if view=='first-person' else [(0,14,58),(35,-10,48)]
data.type='ORTHO';data.ortho_scale=45;scene.render.resolution_x=960;scene.render.resolution_y=720

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prepare_blender_workshop import read_smd
from studio_assets import Studio
persona=Studio(Path(__file__).resolve().parents[1]/'generated/personas/persona_scout.mdl')
from mathutils import Matrix
nn,np,nf,_=read_smd(out.parents[1]/'third-person-normal.smd')
mapping=json.loads(controls['vf_mapping']);inverse={n:c for c,n in mapping.items()}
controls.animation_data_clear()
for style in ['persona','rest','normal','source']:
 evaluate(1)
 for side in ['L','R']:
  for suffix in ['Finger0','Finger1','Finger11']:
   name='Bip01 '+side+' '+suffix;pb=controls.pose.bones[inverse[name]]
   rest=pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local
   if style=='persona':
    i=persona.names.index(name);local=Matrix((__import__('numpy').linalg.inv(persona.bind[persona.parents[i]])@persona.bind[i]).tolist())
   elif style=='rest':local=rest.copy()
   elif style=='normal':local=nf[0][nn.index(name)]
   else:
    sb=source.pose.bones[name];local=sb.parent.matrix.inverted()@sb.matrix
   pb.matrix_basis=rest.inverted()@local
 bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
 print('PROBE',style,'control',controls.pose.bones[inverse['Bip01 L Finger1']].matrix_basis,'result',result.pose.bones['Bip01 L Finger1'].matrix,flush=True)
 camera.location=positions[0];camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(out/('probe-'+style+'.png'));bpy.ops.render.render(write_still=True)
 print('AFTER',style,result.pose.bones['Bip01 L Finger1'].matrix,flush=True)

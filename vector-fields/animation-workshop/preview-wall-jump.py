"""Render the new actions from their saved editable scenes for visual review."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blender_workshop_addon as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
scene=bpy.context.scene;view=scene['vf_view']
out=ROOT/'docs/validation/traversal/wall-jump/blender-preview';out.mkdir(parents=True,exist_ok=True)
source,controls,result=addon.objects(scene)
mesh=scene.objects[scene['vf_mesh']]
for obj in scene.objects:
    if obj.type=='MESH' and obj!=mesh:obj.hide_render=True
center=Vector((0,-8,7))if view=='first-person'else Vector((0,0,2))
position=Vector((0,6,7))if view=='first-person'else Vector((-110,-120,40))
data=bpy.data.cameras.new('Wall jump preview');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
camera.location=position;camera.rotation_euler=(center-position).to_track_quat('-Z','Y').to_euler()
data.type='PERSP'if view=='first-person'else'ORTHO';data.lens=18;data.ortho_scale=100
data.clip_start=.1;data.clip_end=1000;scene.camera=camera
for label,position,power,size in [('Key',(-45,-60,95),90000,65),('Fill',(45,35,65),60000,50)]:
    data=bpy.data.lights.new(label,'AREA');data.energy=power;data.size=size
    lamp=bpy.data.objects.new(label,data);scene.collection.objects.link(lamp);lamp.location=position
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=24
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.10,.14,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
for gesture in ('vf_wall_jump_0','vf_wall_jump_turn_0'):
    addon.select_track(scene,gesture)
    for f in (1,7,13,19):
        scene.frame_set(f);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()
        scene.render.filepath=str(out/(view+'-'+gesture+'-'+str(f)+'.png'))
        bpy.ops.render.render(write_still=True)
        print('PREVIEW',view,gesture,f,flush=True)

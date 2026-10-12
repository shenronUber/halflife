"""Render the actual textured workshop mesh for visual verification."""
from pathlib import Path
import bpy
from mathutils import Vector
import vf_workshop as addon

scene = bpy.context.scene
addon.select_track(scene,'vf_hang_idle_0')
bpy.context.view_layer.update()
addon.update(scene,force=True)
bpy.context.view_layer.update()
_, controls, _ = addon.objects(scene)
center = sum((controls.pose.bones['Main_'+side].matrix.translation for side in ('G','D')),Vector())*.5
center += Vector((0,0,-3))
camera_data=bpy.data.cameras.new('Aperçu');camera=bpy.data.objects.new('Aperçu',camera_data)
scene.collection.objects.link(camera)
camera.location=center+Vector((-45,-9,17))
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=41
scene.camera=camera
for label,position,power,size in [('Principale',center+Vector((-25,-25,35)),18000,25),
                                  ('Remplissage',center+Vector((-15,25,20)),12000,20)]:
 data=bpy.data.lights.new(label,'AREA');data.energy=power;data.shape='DISK';data.size=size
 obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj);obj.location=position
 obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples=32
scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(Path(bpy.data.filepath).parent/'verification/atelier-mains.png')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
scene.view_settings.view_transform='Standard'
scene.render.use_lock_interface=True
bpy.ops.render.render(write_still=True)

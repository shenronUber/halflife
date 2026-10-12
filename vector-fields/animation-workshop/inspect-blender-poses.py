"""Inspect the hand workshop through Blender's own renderer and pose API."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
import vf_workshop as addon

scene = bpy.context.scene
addon.select_track(scene, 'vf_hang_idle_0')
bpy.context.view_layer.update()
addon.update(scene, force=True)
bpy.context.view_layer.update()
source, controls, result = addon.objects(scene)
out = Path(bpy.data.filepath).parent / 'verification/postures'
out.mkdir(parents=True, exist_ok=True)
info = {'scene': {k: scene[k] for k in ('vf_tracks','vf_current','vf_mapping') if k in scene}, 'controls': {}, 'bones': {}}
for bone in controls.pose.bones:
    info['controls'][bone.name] = {'head': list(bone.matrix.translation),
        'matrix': [list(row) for row in bone.matrix], 'rotation': list(bone.rotation_euler)}
for bone in result.pose.bones:
    info['bones'][bone.name] = {'head': list(bone.matrix.translation),
        'matrix': [list(row) for row in bone.matrix]}
(out / 'before.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
for obj in scene.objects:
    if obj.name.startswith('Repère'):
        obj.hide_render = True
center = sum((controls.pose.bones['Main_'+s].matrix.translation for s in ('G','D')), Vector())*.5
center += Vector((0,0,-2))
data = bpy.data.cameras.new('Diagnostic'); camera = bpy.data.objects.new('Diagnostic', data)
scene.collection.objects.link(camera); scene.camera = camera
data.type = 'ORTHO'; data.ortho_scale = 32
for label, offset, power in [('Key', (-25,-25,35), 18000), ('Fill', (-15,25,20),12000)]:
    light_data = bpy.data.lights.new(label, 'AREA'); light_data.energy=power; light_data.size=25
    obj=bpy.data.objects.new(label,light_data); scene.collection.objects.link(obj)
    obj.location=center+Vector(offset)
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE_NEXT'; scene.eevee.taa_render_samples=32
scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
scene.view_settings.view_transform='Standard'
for name, offset in [('before-front',(-45,0,7)),('before-oblique',(-30,-30,24))]:
    camera.location=center+Vector(offset)
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)

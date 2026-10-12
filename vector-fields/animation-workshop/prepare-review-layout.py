"""Save inspection views and a correct visual ledge in the generated review only."""
import argparse,sys
import bpy
from pathlib import Path
from mathutils import Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
scene=bpy.context.scene;fp=scene['vf_view']=='first-person'
parser=argparse.ArgumentParser();parser.add_argument('--focused-traversal',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[])
source,controls,result=addon.objects(scene)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
for obj in list(scene.objects):
    if obj.name.startswith('Repère'):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.mesh.primitive_cube_add()
board=bpy.context.object;board.name='Repère - rebord / dos vers visage'
board.location=(34,0,-16) if fp else (0,-34,0)
board.scale=(16,35,25) if fp else (35,16,40)
board.hide_select=True
mat=bpy.data.materials.new('Rebord - prise par-dessus');mat.diffuse_color=(.22,.26,.3,1);board.data.materials.append(mat)
reference=Path('C:/Users/Mathieu/AppData/Local/Temp/codex-clipboard-886b0897-69ce-4667-96cc-15d7bd023332.png')
if reference.exists():
    img=bpy.data.images.load(str(reference),check_existing=True);img.name='REFERENCE UTILISATEUR - prise par-dessus';img.pack()
gesture=('vf_climb_0'if fp else'vf_slide_loop_0')if args.focused_traversal else'vf_hang_idle_0'
scene.vf_gesture=gesture;addon.select_track(scene,gesture)
for obj in scene.objects:obj.select_set(False)
controls.select_set(True);bpy.context.view_layer.objects.active=controls;bpy.ops.object.mode_set(mode='POSE')
target=Vector((18,0,7)) if fp else Vector((0,-6,12))
eye=Vector((0,0,1.5)) if fp else Vector((65,85,55))
if args.focused_traversal:
    target=Vector((0,-18,0))if fp else Vector((0,-6,-8))
    eye=Vector((0,0,1.5))if fp else Vector((65,85,30))
    board.hide_set(True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.region_3d.view_location=target;space.region_3d.view_distance=(eye-target).length
            space.region_3d.view_rotation=(eye-target).to_track_quat('Z','Y');space.region_3d.view_perspective='PERSP'
            space.lens=28;space.shading.type='MATERIAL';space.overlay.show_bones=True;space.show_region_ui=True
scene['vf_review_instruction']='Dos vers le visage ; doigts par-dessus. Le repère suit la remontée du corps pendant le tir. Visage / Profil / Corps : panneau Vector Fields.'
if args.focused_traversal:bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('REVIEW LAYOUT SAVED',bpy.data.filepath,flush=True)

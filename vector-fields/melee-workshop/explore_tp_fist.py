"""A Blender pose study: compare thumb opposition and both finger flexion planes."""
import bpy,json,math,runpy,sys
from pathlib import Path
from mathutils import Matrix,Euler
WORK=Path(__file__).resolve().parent;scene=bpy.data.scenes['Troisième personne'];bpy.context.window.scene=scene;scene.frame_set(14);bpy.context.view_layer.update()
rig=scene.objects['r01_tp'];names=json.loads(rig['vf_order']);parents=[names.index(b.parent.name)if b.parent else-1 for b in rig.data.bones]
g=[rig.pose.bones[n].matrix.copy()for n in names];base=[g[p].inverted()@m if p>=0 else m.copy()for p,m in zip(parents,g)]
variants=[('A',[-65,-42,42],[-20,0,105],[0,0,105]),('B',[-150,-42,42],[-20,0,105],[0,0,105]),
 ('C',[63,-42,42],[-20,0,105],[0,0,105]),('D',[63,42,-42],[-20,0,-105],[0,0,-105]),
 ('E',[-60,42,-42],[-20,0,-110],[0,0,-110]),('F',[80,25,-25],[-20,0,-110],[0,0,-110]),
 ('G',[0,-50,35],[-20,0,105],[0,0,105]),('H',[0,50,-35],[-20,0,-95],[0,0,-100])]
variants.append(('I',[-105,-68,45],[-20,0,105],[0,0,105]))
rig.animation_data.action=bpy.data.actions.new('Étude manuelle / poing gauche / huit poses');rig.animation_data.action.use_fake_user=True
for frame,(label,thumb,mcp,pip)in enumerate(variants,1):
    local=[m.copy()for m in base]
    for index,angles in [(18,thumb),(19,mcp),(20,pip)]:
        rotation=Euler(tuple(math.radians(v)for v in angles),'XYZ').to_matrix().to_4x4();rotation.translation=local[index].translation;local[index]=rotation
    if label=='I':local[18].translation+=__import__('mathutils').Vector((0,0,-.8))
    for i,name in enumerate(names):
        rest=rig.data.bones[name].matrix_local
        if parents[i]>=0:rest=rig.data.bones[names[parents[i]]].matrix_local.inverted()@rest
        pb=rig.pose.bones[name];pb.matrix_basis=rest.inverted()@local[i]
        pb.keyframe_insert('location',frame=frame);pb.keyframe_insert('rotation_quaternion',frame=frame)
    scene.timeline_markers.new('Pose '+label,frame=frame)
scene['finger_study']=json.dumps(variants);bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'Etude-poing-gauche.blend'))
sys.argv=['review','--','--tag','tp-study-2','--frames','9','--views','tp']
runpy.run_path(str(WORK/'review_fist.py'),run_name='__main__')

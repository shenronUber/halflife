import bpy,json,sys
from pathlib import Path
import vf_workshop as a
from mathutils import Vector,Matrix
s=bpy.context.scene;src,c,r=a.objects(s);a.select_track(s,'vf_hang_idle_0');s.frame_set(1);bpy.context.view_layer.update();a.update(s,force=True)
for n in ['Bip01','Bip01 L Hand','Bip01 L Finger1','Bip01 L Finger11','Bip01 R Hand']:
 print('JOINT',n,tuple(r.pose.bones[n].matrix.translation),list(r.pose.bones[n].matrix.to_3x3()))
m=bpy.data.objects[s['vf_mesh']];posed=m.evaluated_get(bpy.context.evaluated_depsgraph_get())
for n in ['Bip01 L Finger1','Bip01 L Finger11']:
 pts=[v.co for v,orig in zip(posed.data.vertices,m.data.vertices) if m.vertex_groups[orig.groups[0].group].name==n]
 print('SKIN',n,'count',len(pts),'bounds',[(min(p[i] for p in pts),max(p[i] for p in pts))for i in range(3)])
print('RESULT',r.matrix_world,'MESH',m.matrix_world)

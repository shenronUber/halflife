"""Inspect every traversal track through Blender's evaluated rig and renderer.

All integer and half frames are checked. Contact sheets include both the
player view and an anatomical inspection view; native tests cover assembly.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()

parser=argparse.ArgumentParser()
parser.add_argument('--phase',default='before')
parser.add_argument('--no-render',action='store_true')
parser.add_argument('--render-left-only',action='store_true')
parser.add_argument('--track',action='append',default=[])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
scene=bpy.context.scene
source,controls,result=addon.objects(scene)
view=scene['vf_view']
out=Path(bpy.data.filepath).parent/'verification/audit-traversal'/args.phase/view
out.mkdir(parents=True,exist_ok=True)
mesh=bpy.data.objects[scene['vf_mesh']]
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
report=dict(file=bpy.data.filepath,view=view,tracks={},transitions={},renders=[],sampled_frames=0)
if args.render_left_only:
    assert view=='third-person'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from traversal_aim import left_lean,left_route
    def changed_left(key):
        if not key.startswith('vf_hang_aim_'):return False
        sector,corner=map(int,key.split('_')[-2:])
        yaw=sector*45+(-22.5 if corner%2==0 else 22.5)
        return left_lean(yaw)>1.e-8 or left_route(yaw)>1.e-8
    prior=json.loads((out/'rig-audit.json').read_text())
    report['renders']=[r for r in prior['renders'] if not changed_left(r['track'])]

def evaluate(frame,subframe=0):
    scene.frame_set(frame,subframe=subframe)
    bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def difference(a,b):
    return max(abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))

endpoints={}
for track in addon.tracks(scene):
    if args.track and track['key']not in args.track:continue
    addon.select_track(scene,track['key'])
    stats=dict(frames=track['frames'],max_length_change=0.,max_skinning_error=0.,max_rotation_step=0.,reach_warnings=[])
    last=None
    for frame in range(1,track['frames']+1):
        for sub in (0.,.5) if frame<track['frames'] else (0.,):
            evaluate(frame,sub)
            if result.get('vf_reach_warning'):stats['reach_warnings'].append([frame,sub])
            authored=addon.locals_from(source,names,parents)
            actual=addon.locals_from(result,names,parents)
            stats['max_length_change']=max(stats['max_length_change'],max(abs(a.translation.length-b.translation.length) for n,a,b in zip(names[1:],actual[1:],authored[1:]) if n not in {'VF_Weapon','VF_Magazine','VF_Bolt'}))
            posed=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
            for vertex,point in zip(mesh.data.vertices,posed.data.vertices):
                assert all(math.isfinite(v) for v in point.co),(track['key'],frame,sub)
                group=mesh.vertex_groups[vertex.groups[0].group].name
                expected=result.pose.bones[group].matrix@result.data.bones[group].matrix_local.inverted()@vertex.co
                stats['max_skinning_error']=max(stats['max_skinning_error'],(point.co-expected).length)
            now=[matrix.to_quaternion() for matrix in actual]
            if last:
                for a,b in zip(last,now):
                    angle=a.rotation_difference(b).angle
                    stats['max_rotation_step']=max(stats['max_rotation_step'],min(angle,abs(2*math.pi-angle)))
            last=now
            report['sampled_frames']+=1
    evaluate(1);first=[result.pose.bones[n].matrix.copy() for n in names]
    evaluate(track['frames']);end=[result.pose.bones[n].matrix.copy() for n in names]
    endpoints[track['key']]=(first,end)
    loop=track['key'].startswith(('vf_hang_both_','vf_hang_aim_','vf_hang_idle_','vf_slide_loop_'))
    stats['loop_error']=max(difference(a,b) for a,b in zip(first,end)) if loop else None
    assert stats['max_length_change']<.003,(track['key'],stats)
    assert stats['max_skinning_error']<.001,(track['key'],stats)
    assert not stats['reach_warnings'],(track['key'],stats)
    if loop:assert stats['loop_error']<.006,(track['key'],stats)
    report['tracks'][track['key']]=stats
    print('AUDIT',view,track['key'],flush=True)

for a,b in [('vf_hang_catch_0','vf_hang_idle_0'),('vf_hang_idle_0','vf_hang_arm_0'),
            ('vf_hang_idle_0','vf_climb_0'),('vf_hang_idle_0','vf_drop_0'),
            ('vf_slide_start_0','vf_slide_loop_0'),('vf_slide_loop_0','vf_slide_end_0')]:
    if a not in endpoints or b not in endpoints:continue
    first=endpoints[a][1];second=endpoints[b][0]
    deltas={n:dict(position=(x.translation-y.translation).length,
                    rotation_degrees=math.degrees(min(x.to_quaternion().rotation_difference(y.to_quaternion()).angle,abs(2*math.pi-x.to_quaternion().rotation_difference(y.to_quaternion()).angle))))
            for n,x,y in zip(names,first,second)}
    report['transitions'][a+' -> '+b]=deltas
(out/'rig-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if not args.no_render:
    for obj in scene.objects:
        if obj.name.startswith('Repère'):obj.hide_render=True
        if obj.type=='MESH' and obj!=mesh:obj.hide_render=True
    data=bpy.data.cameras.new('Caméra audit');camera=bpy.data.objects.new('Caméra audit',data)
    scene.collection.objects.link(camera);scene.camera=camera
    for label,position,power in [('Principale',(-25,-30,70),18000),('Douce',(-25,35,45),14000)]:
        light_data=bpy.data.lights.new(label,'AREA');light_data.energy=power;light_data.size=30
        light=bpy.data.objects.new(label,light_data);scene.collection.objects.link(light);light.location=position
        light.rotation_euler=(Vector((15,0,20))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.18,.23,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.85
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=24
    scene.render.resolution_x=480;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    for track in addon.tracks(scene):
        if args.track and track['key']not in args.track:continue
        if args.render_left_only and not changed_left(track['key']):continue
        addon.select_track(scene,track['key'])
        fractions=(0.,) if track['frames']==3 else (0.,.25,.5,.75,1.)
        evaluate(1)
        center=(controls.pose.bones['Main_G'].matrix.translation+controls.pose.bones['Main_D'].matrix.translation)*.5 if view=='first-person' else Vector((6,0,8))
        normal=result.pose.bones['Bone42'].matrix.to_3x3()@Vector((0,0,1)) if view=='first-person' else Vector((1,-.3,.15))
        for row in ('jeu','controle'):
            if view=='first-person' and row=='jeu':
                data.type='PERSP';data.angle=math.radians(75);camera.location=(0,0,1.5)
                direction=(0,-1,0)if args.track and track['key']=='vf_climb_0'else(1,0,0)
                camera.rotation_euler=Vector(direction).to_track_quat('-Z','Y').to_euler()
            else:
                data.type='ORTHO';data.ortho_scale=52 if view=='first-person' else 115
                offset=normal*48+Vector((0,-16,9)) if view=='first-person' else (Vector((90,-30,20)) if row=='jeu' else Vector((-15,-90,25)))
                camera.location=center+offset;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            for index,fraction in enumerate(fractions):
                f=1+fraction*(track['frames']-1);evaluate(int(f),f-int(f))
                path=out/f"{track['key']}-{row}-{index}.png"
                scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
                report['renders'].append(dict(track=track['key'],view=row,index=index,fraction=fraction,path=str(path)))
        print('RENDERED',view,track['key'],flush=True)
    # Inspect the actual low-poly fingers against a solid ledge, close enough
    # to see thumb direction and interpenetration in both rigs.
    addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
    bpy.ops.mesh.primitive_cube_add()
    ledge=bpy.context.object;ledge.name='Rebord de contrôle'
    if view=='first-person':ledge.location=(34,0,-16);ledge.scale=(16,35,25)
    else:ledge.location=(0,-34,0);ledge.scale=(35,16,40)
    material=bpy.data.materials.new('Pierre de contrôle');material.diffuse_color=(.24,.27,.3,1);ledge.data.materials.append(material)
    target=Vector((18,0,7)) if view=='first-person' else Vector((0,-18,38))
    positions=[(-12,0,24),(13,-38,19)] if view=='first-person' else [(0,14,58),(35,-10,48)]
    data.type='ORTHO';data.ortho_scale=45;scene.render.resolution_x=960;scene.render.resolution_y=720
    for index,position in enumerate(positions):
        camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        path=out/f'contact-rebord-{index}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        report.setdefault('contact_renders',[]).append(str(path))
(out/'rig-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS AUDIT',view,len(report['tracks']),report['sampled_frames'],len(report['renders']),flush=True)

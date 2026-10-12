"""Extend the planted left arm and lean back in the existing reviewed body."""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import globals_from
from studio_assets import Studio
from traversal_aim import left_lean,support_retreat,firing_arm,left_cross_arm,left_route

scene=bpy.context.scene;source,controls,result=addon.objects(scene)
assert scene['vf_view']=='third-person'
baseline=Path(bpy.data.filepath);before=hashlib.sha256(baseline.read_bytes()).hexdigest()
destination=baseline.parent/'Corps-R1-appui-gauche.blend'
assert not destination.exists(),destination
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
mapping=json.loads(controls['vf_mapping'])
persona=Studio(ROOT/'generated/personas/persona_scout.mdl')
bind={n:Matrix(m.tolist()) for n,m in zip(persona.names,persona.bind)}
exports=baseline.parent.parent/'retouches/appui-gauche/third-person';exports.mkdir(parents=True,exist_ok=True)
out=baseline.parent/'verification/audit-traversal/after'
prior=json.loads((out/'corrections-third-person.json').read_text())
tracks=addon.tracks(scene);stats=[]
smd=lambda v:Vector((v[1],-v[0],v[2]))
compiler=lambda v:(-v.y,v.x,v.z)

def evaluate(frame):
    scene.frame_set(frame);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def solve(local,ids,goal,pole):
    upper,fore,hand=ids;g=globals_from(local,parents)
    shoulder,elbow,wrist=(g[i].translation for i in ids)
    a=(elbow-shoulder).length;b=(wrist-elbow).length;delta=goal.translation-shoulder;d=delta.length
    assert abs(a-b)+.0001<d<a+b-.0001,(ids,d,a+b)
    direction=delta.normalized();bias=pole-shoulder;bias-=direction*bias.dot(direction)
    if bias.length<.00001:bias=direction.cross(Vector((0,0,1)))
    along=(a*a-b*b+d*d)/(2*d)
    e=shoulder+direction*along+bias.normalized()*math.sqrt(max(0,a*a-along*along))
    turn=(elbow-shoulder).rotation_difference(e-shoulder).to_matrix()
    translation=local[upper].translation.copy()
    local[upper]=(g[parents[upper]].to_3x3().transposed()@turn@g[upper].to_3x3()).to_4x4();local[upper].translation=translation
    g=globals_from(local,parents);relative=bind[names[fore]].inverted()@bind[names[hand]]
    desired=goal.to_3x3()@relative.to_3x3().transposed()
    turn=(desired@relative.translation).rotation_difference(goal.translation-e).to_matrix()
    translation=local[fore].translation.copy()
    local[fore]=(g[upper].to_3x3().transposed()@turn@desired).to_4x4();local[fore].translation=translation
    g=globals_from(local,parents);translation=local[hand].translation.copy()
    local[hand]=(g[fore].to_3x3().transposed()@goal.to_3x3()).to_4x4();local[hand].translation=translation

for track in tracks:
    key=track['key'];addon.select_track(scene,key)
    weight=0.;yaw=pitch=0.
    if key.startswith('vf_hang_aim_'):
        sector,corner=map(int,key.split('_')[-2:])
        yaw=(sector*45+(-22.5 if corner%2==0 else 22.5)+180)%360-180
        pitch=-70 if corner<2 else 70;weight=left_lean(yaw)
    if weight>1.e-8 or (key.startswith('vf_hang_aim_') and left_route(yaw)>1.e-8):
        frames=[]
        for f in range(1,track['frames']+1):
            evaluate(f);frames.append([m.copy()for m in addon.locals_from(result,names,parents)])
        action=controls.animation_data.action.copy();action.name='APPUI_GAUCHE|'+key;action.use_fake_user=True
        controls.animation_data.action=action;previous={}
        for f,original in enumerate(frames,1):
            local=[m.copy()for m in original];old=globals_from(local,parents)
            local[0].translation.z+=3*weight
            for i in (8,9,10,11):
                g=globals_from(local,parents);translation=local[i].translation.copy()
                rotation=Matrix.Rotation(math.radians(-12*weight/4),3,'X')
                local[i]=(g[parents[i]].to_3x3().transposed()@rotation@g[i].to_3x3()).to_4x4();local[i].translation=translation
            g=globals_from(local,parents)
            reach=(old[16].translation-old[15].translation).length+(old[17].translation-old[16].translation).length
            retreat=support_retreat(compiler(old[17].translation-g[15].translation),reach,weight)
            local[0].translation+=smd((-retreat,0,0));g=globals_from(local,parents)
            translation=local[13].translation.copy()
            local[13]=(g[parents[13]].to_3x3().transposed()@old[13].to_3x3()).to_4x4();local[13].translation=translation
            right=old[24].copy();offset=old[24].translation-old[22].translation
            a=(old[23].translation-old[22].translation).length;b=(old[24].translation-old[23].translation).length
            _,pole,_=firing_arm(yaw,pitch,a+b)
            span=compiler(g[15].translation-g[22].translation);chest=math.atan2(-span[0],span[1])
            route_wrist,route_elbow,route=left_cross_arm(yaw,a,b,chest)
            offset=(1-route)*offset+route*smd(route_wrist)
            pole=tuple((1-route)*v+route*r for v,r in zip(pole,route_elbow))
            rise=offset.z;right.translation=g[22].translation+offset
            solve(local,(15,16,17),old[17],g[15].translation+smd((-4,4,-16)))
            solve(local,(22,23,24),right,g[22].translation+smd(pole))
            actual=globals_from(local,parents)
            assert (actual[17].translation-old[17].translation).length<.001
            for control,bone in mapping.items():
                pb=controls.pose.bones[control]
                rest=pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local if pb.parent else pb.bone.matrix_local
                basis=rest.inverted()@local[names.index(bone)]
                pb.location=basis.translation
                pb.rotation_euler=basis.to_quaternion().to_euler('XYZ',previous.get(control,pb.rotation_euler));previous[control]=pb.rotation_euler.copy()
                for prop in ('location','rotation_euler'):pb.keyframe_insert(prop,frame=f,group=control)
            if f==1:stats.append(dict(track=key,yaw=yaw,pitch=pitch,weight=weight,retreat=retreat,lift=3*weight,right_wrist_rise=rise,support_extension=(actual[17].translation-actual[15].translation).length/reach))
        for slot in action.slots:
            for curve in action.layers[0].strips[0].channelbag(slot).fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
        track['control_action']=action.name;scene['vf_tracks']=json.dumps(tracks)
        addon.select_track(scene,key)
    addon.export_smd(scene,exports/(key+'.smd'));print('EXPORTED LEFT LEAN',key,round(weight,4),flush=True)
scene.vf_gesture='vf_hang_idle_0';addon.select_track(scene,'vf_hang_idle_0');evaluate(1)
scene['vf_exports']='//../retouches/appui-gauche/third-person'
scene['vf_pose_revision']='Appui gauche tendu : recul doux, torse en arrière, jambes relevées de trois unités au maximum.'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==before
prior.update(baseline=str(baseline),baseline_sha256=before,revision=str(destination),export_directory=str(exports),left_lean=stats)
(out/'corrections-third-person.json').write_text(json.dumps(prior,indent=2),encoding='utf-8')
print('PASS LEFT LEAN BLENDER',json.dumps(stats),flush=True)

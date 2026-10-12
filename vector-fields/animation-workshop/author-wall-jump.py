"""Add two editable push-off actions to copies of the reviewed Blender scenes.

Run with Blender --background <reviewed scene> --python this script.
The masters and all their previous actions remain untouched.
"""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blender_workshop_addon as addon
from prepare_blender_workshop import animate,globals_from,control_frames
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
scene=bpy.context.scene;source,controls,result=addon.objects(scene)
view=scene['vf_view'];baseline=Path(bpy.data.filepath)
out=ROOT/'docs/validation/traversal/wall-jump';out.mkdir(parents=True,exist_ok=True)
exports=ROOT/'assets/animations/traversal-edits'/view;exports.mkdir(parents=True,exist_ok=True)
destination=baseline.parent/('Mains-R1-saut-mural.blend'if view=='first-person'else'Corps-R1-rebond-dynamique.blend')
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents'])
mapping=json.loads(controls['vf_mapping']);tracks=addon.tracks(scene)
original_actions={a.name:len(a.fcurves)if hasattr(a,'fcurves')else len(a.slots)for a in bpy.data.actions}
before=hashlib.sha256(baseline.read_bytes()).hexdigest()

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def blend(a,b,t):
    m=a.to_quaternion().slerp(b.to_quaternion(),t).to_matrix().to_4x4()
    m.translation=a.translation.lerp(b.translation,t);return m

def local_blend(a,b,t):
    m=blend(a,b,t);length=m.translation.length
    if length>1e-8:m.translation*=a.translation.length/length
    return m

def solve_limb(local,ids,goal,pole):
    upper,fore,hand=ids;g=globals_from(local,parents)
    shoulder=g[upper].translation;elbow=g[fore].translation;wrist=g[hand].translation
    a=(elbow-shoulder).length;b=(wrist-elbow).length
    delta=goal.translation-shoulder;distance=max(abs(a-b)+.001,min(a+b-.001,delta.length))
    direction=delta.normalized();goal=goal.copy();goal.translation=shoulder+direction*distance
    bias=pole-shoulder;bias-=direction*bias.dot(direction)
    if bias.length<.00001:bias=direction.cross(Vector((0,0,1)))
    along=(a*a-b*b+distance*distance)/(2*distance)
    next_elbow=shoulder+direction*along+bias.normalized()*math.sqrt(max(0,a*a-along*along))
    turn=(elbow-shoulder).rotation_difference(next_elbow-shoulder).to_matrix()
    translation=local[upper].translation.copy()
    local[upper]=(g[parents[upper]].to_3x3().transposed()@turn@g[upper].to_3x3()).to_4x4();local[upper].translation=translation
    g=globals_from(local,parents);desired=g[fore].to_3x3()
    turn=(g[hand].translation-g[fore].translation).rotation_difference(goal.translation-next_elbow).to_matrix()
    translation=local[fore].translation.copy()
    local[fore]=(g[upper].to_3x3().transposed()@turn@desired).to_4x4();local[fore].translation=translation
    g=globals_from(local,parents);translation=local[hand].translation.copy()
    local[hand]=(g[fore].to_3x3().transposed()@goal.to_3x3()).to_4x4();local[hand].translation=translation

def evaluate(f):
    scene.frame_set(f);bpy.context.view_layer.update();addon.update(scene,force=True);bpy.context.view_layer.update()

def local_rest(rig,order):
    return [rig.data.bones[n].parent.matrix_local.inverted()@rig.data.bones[n].matrix_local
            if rig.data.bones[n].parent else rig.data.bones[n].matrix_local.copy()for n in order]

def pose(key,f=1):
    addon.select_track(scene,key);evaluate(f)
    return ([m.copy()for m in addon.locals_from(result,names,parents)],
            {pb.name:pb.matrix.copy()for pb in controls.pose.bones})

idle,idle_c=pose('vf_hang_idle_0')
idle_g=globals_from(idle,parents)
normal,normal_c=pose('vf_climb_0',next(t['frames']for t in tracks if t['key']=='vf_climb_0'))
source_rest=local_rest(source,names);cnames=json.loads(controls['vf_order'])
cp=[cnames.index(controls.data.bones[n].parent.name)if controls.data.bones[n].parent else -1 for n in cnames]
crest=local_rest(controls,cnames)
audits=[]
for turned in (False,True):
    gesture='vf_wall_jump_turn'if turned else'vf_wall_jump';key=gesture+'_0';count=21
    if any(t['key']==key for t in tracks):raise RuntimeError('Action already exists: '+key)
    frames=[]
    for f in range(count):
        t=f/(count-1);release=smooth(t/(.12 if view=='third-person'else .28));recover=smooth((t-.80)/.20) if view=='third-person'else smooth((t-.72)/.28)
        local=[m.copy()for m in idle]
        if view=='third-person':
            # At release, the legs extend from the wall, then tuck for flight.
            # The root keeps the same position: physics alone moves the body.
            angles={
                'Bip01 Spine':(0,-16*math.sin(math.pi*t),0),
                'Bip01 Spine1':(0,6*math.sin(math.pi*t),0),
            }
            for n,xyz in angles.items():
                if n not in names:continue
                i=names.index(n)
                for axis,angle in zip('XYZ',xyz):local[i]=local[i]@Matrix.Rotation(math.radians(angle),4,axis)
            for sign,ids in [(1,(15,16,17)),(-1,(22,23,24))]:
                start=idle_g[ids[2]].copy();tuck=start.copy();tuck.translation=Vector((sign*11,-10,22))
                goal=blend(start,tuck,release)
                ready=tuck.copy();ready.translation=Vector((sign*10,-22,32))
                goal=blend(goal,ready,smooth((t-.16)/.25))
                solve_limb(local,ids,goal,Vector((sign*18,-3,15)))
            for sign,ids in [(1,(2,3,4)),(-1,(5,6,7))]:
                start=idle_g[ids[2]].copy();press=start.copy();press.translation=Vector((sign*4,6,-23))
                goal=blend(start,press,smooth(t/.16))
                tuck=press.copy();tuck.translation=Vector((sign*5,7,-12 if sign==1 else -16))
                goal=blend(goal,tuck,smooth((t-.14)/.25))
                solve_limb(local,ids,goal,Vector((sign*6,-12,-3)))
            local=[local_blend(a,b,recover)if i else blend(a,b,recover)for i,(a,b)in enumerate(zip(local,normal))]
            if turned:
                # Entity yaw follows the player's actual look, including a
                # turn made after S+jump. Do not bake a second 180-degree turn.
                turn=smooth(t/.4)
                for n,weight in [('Bip01 Neck',.30),('Bip01 Head',.70)]:
                    i=names.index(n);g=globals_from(local,parents);translation=local[i].translation.copy()
                    rotation=Matrix.Rotation(math.radians(35)*weight*smooth(t/.1)*(1-turn),3,'Z')@g[i].to_3x3()
                    local[i]=(g[parents[i]].to_3x3().transposed()@rotation).to_4x4();local[i].translation=translation
        frames.append(local)
    sa=animate(source,'WALL_JUMP_SOURCE|'+key,frames,source_rest)
    if view=='third-person':
        cf=control_frames(view,names,parents,frames,cnames,cp,mapping)
    else:
        cf=[]
        # Corrected hang keys are expressed in the editor's wall frame. Match
        # the in-game camera frame, just as the reviewed mantle does.
        initial={n:Matrix.Rotation(-math.pi/2,4,'Z')@m for n,m in idle_c.items()if n.startswith(('Main_','Coude_'))}
        if turned:
            # Rear view sees the wall hands behind the eye until release.
            for n in initial:initial[n]=Matrix.Rotation(math.pi,4,'Z')@initial[n]
        for f in range(count):
            t=f/(count-1);release=smooth(t/.28);reach=smooth((t-.34)/.30);recover=smooth((t-.72)/.28)
            values=[]
            for n in cnames:
                if n.startswith(('Main_','Coude_')):
                    sign=1 if n.endswith('G')else -1
                    if n.startswith('Main_'):
                        tuck=initial[n].copy();tuck.translation=Vector((sign*9,-9,-14))
                        goal=blend(initial[n],tuck,release)
                        ready=tuck.copy();ready.translation=Vector((sign*12,-15,-5))
                        goal=blend(goal,ready,reach);goal=blend(goal,normal_c[n],recover)
                        elbow=names.index('Bone40'if sign==1 else'Bone05')
                        wrist=names.index('Bone42'if sign==1 else'Bone07')
                        shoulder=idle_g[parents[elbow]].translation
                        a=(idle_g[elbow].translation-shoulder).length
                        b=(idle_g[wrist].translation-idle_g[elbow].translation).length
                        delta=goal.translation-shoulder
                        distance=max(abs(a-b)+.05,min(a+b-.05,delta.length))
                        if delta.length>1e-8:goal.translation=shoulder+delta.normalized()*distance
                    else:
                        tuck=initial[n].copy();tuck.translation=Vector((sign*17,-3,-15))
                        goal=blend(initial[n],tuck,release);goal=blend(goal,normal_c[n],recover)
                    values.append(goal)
                else:
                    i=names.index(mapping[n]);values.append(local_blend(idle[i],normal[i],release*recover))
            cf.append(values)
    ca=animate(controls,'SAUT_MURAL|'+key,cf,crest)
    track=dict(key=key,label='Saut du mur / '+('regard derrière'if turned else'face au mur'),
               frames=count,fps=(count-1)/.65,source_action=sa.name,control_action=ca.name,original=str(baseline))
    tracks.append(track);scene['vf_tracks']=json.dumps(tracks,ensure_ascii=False)
    addon.select_track(scene,key)
    warnings=[];samples=[]
    for f in range(1,count+1):
        evaluate(f)
        if result.get('vf_reach_warning'):warnings.append(f)
        if f in (1,6,11,16,21):samples.append(dict(frame=f,root=list(result.pose.bones[names[0]].matrix.translation)))
    if warnings:raise RuntimeError((view,key,'IK reach',warnings))
    addon.export_smd(scene,exports/(key+'.smd'))
    audits.append(dict(gesture=gesture,frames=count,samples=samples))
    print('AUTHORED',view,key,flush=True)
scene['vf_exports']=str(exports)
scene['vf_pose_revision']='Saut mural : relâcher, repousser, ramener les mains ; nouvelle prise possible en vol.'
addon.select_track(scene,'vf_wall_jump_0');scene.vf_gesture='vf_wall_jump_0';evaluate(1)
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==before,'Master changed'
assert all(n in bpy.data.actions for n in original_actions),'Previous action removed'
(out/(view+'-blender.json')).write_text(json.dumps(dict(baseline=str(baseline),baseline_sha256=before,
    revision=str(destination),preserved_actions=len(original_actions),gestures=audits),indent=2))
print('SAVED',destination,flush=True)

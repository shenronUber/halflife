"""Update reviewed actions in the new Blender files without rebuilding meshes."""
import json,sys
from pathlib import Path
import bpy
import vf_workshop as addon
if not hasattr(bpy.types.Scene,'vf_gesture'):addon.register()
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare_blender_workshop import read_smd,animate,control_frames
scene=bpy.context.scene;source,controls,result=addon.objects(scene);view=scene['vf_view']
names=json.loads(result['vf_names']);parents=json.loads(result['vf_parents']);mapping=json.loads(controls['vf_mapping'])
cnames=json.loads(controls['vf_order']);cparents=[cnames.index(controls.data.bones[n].parent.name)if controls.data.bones[n].parent else-1 for n in cnames]
def rest(rig,order,relations):
 matrices=[rig.data.bones[n].matrix_local.copy()for n in order]
 return [matrices[p].inverted()@matrices[i]if p>=0 else matrices[i]for i,p in enumerate(relations)]
srest=rest(source,names,parents);crest=rest(controls,cnames,cparents);tracks=addon.tracks(scene)
for track in tracks:
 if track['key']not in ('vf_vault_0','vf_stepup_0'):continue
 path=ROOT/'animation-workshop/traversal'/view/(track['key']+'.smd');frame_names,frame_parents,frames,_=read_smd(path)
 assert frame_names==names and frame_parents==parents
 source_action=animate(source,'SOURCE|REVUE|'+track['key'],frames,srest)
 cf=control_frames(view,names,parents,frames,cnames,cparents,mapping)
 control_action=animate(controls,'RETOUCHE|REVUE|'+track['key'],cf,crest)
 track.update(source_action=source_action.name,control_action=control_action.name,frames=len(frames),original=str(path))
scene['vf_tracks']=json.dumps(tracks,ensure_ascii=False);scene['vf_pose_revision']='Appui gauche, rotation stable du poignet, muret et plateforme distincts.'
addon.select_track(scene,'vf_vault_0');scene.frame_set(1);addon.update(scene,force=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Updated vault and platform actions in',bpy.data.filepath)

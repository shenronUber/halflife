"""Run with the project's Blender: verify import, controls, skinning and SMD export."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_blender_workshop import read_smd, globals_from
import vf_workshop as addon


def difference(a, b):
    return max(abs(x-y) for ra, rb in zip(a,b) for x,y in zip(ra,rb))


def evaluate(scene):
    bpy.context.view_layer.update()
    addon.update(scene, force=True)
    bpy.context.view_layer.update()
    source, controls, result = addon.objects(scene)
    dg = bpy.context.evaluated_depsgraph_get()
    return source.evaluated_get(dg), controls.evaluated_get(dg), result.evaluated_get(dg)


def verify():
    report = {}; verification = ROOT/'animation-workshop/traversal/blender/verification'
    verification.mkdir(parents=True, exist_ok=True)
    for view, filename in [('first-person','Mains-R1.blend'), ('third-person','Corps-R1.blend')]:
        path = verification.parent/filename
        new_base = path.with_name(path.stem+'-nouvelle-base.blend')
        bpy.ops.wm.open_mainfile(filepath=str(new_base if new_base.exists() else path))
        scene = bpy.context.scene
        source, controls, result = addon.objects(scene)
        names = json.loads(result['vf_names']); parents = json.loads(result['vf_parents'])
        errors = []; source_errors = []; sample_count = 0
        for track in addon.tracks(scene):
            addon.select_track(scene, track['key'])
            _, _, frames, _ = read_smd(Path(track['original']))
            for frame in sorted({1,(track['frames']+1)//2,track['frames']}):
                scene.frame_set(frame)
                se, ce, re = evaluate(scene)
                expected = globals_from(frames[frame-1], parents)
                source_errors.extend(difference(se.pose.bones[n].matrix,m) for n,m in zip(names,expected))
                errors.extend(difference(re.pose.bones[n].matrix,m) for n,m in zip(names,expected))
                sample_count += 1
        assert max(source_errors) < .0003, (view,'source import',max(source_errors))
        # Euler controls can lose a few float bits close to a gimbal singularity.
        # Bound the resulting displacement to < .003 GoldSrc units.
        assert max(errors) < .003, (view,'control rig changes the baseline',max(errors))
        addon.select_track(scene, 'vf_hang_idle_0')
        se, ce, re = evaluate(scene)
        # The weighted mesh must agree with the original SMD bind-pose skinning.
        mesh = bpy.data.objects[scene['vf_mesh']]
        evaluated_mesh = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        skin_error = 0.
        for vertex, actual in zip(mesh.data.vertices,evaluated_mesh.data.vertices):
            group = mesh.vertex_groups[vertex.groups[0].group].name
            expected = re.pose.bones[group].matrix @ result.data.bones[group].matrix_local.inverted() @ vertex.co
            skin_error = max(skin_error,(actual.co-expected).length)
        assert skin_error < .0005, (view,'mesh mismatch',skin_error)
        addon.export_smd(scene, verification/(view+'-baseline.smd'))
        if view == 'first-person':
            wrist = 'Bone42'; finger = 'Bone49'; control = 'G_Index_2'
            before_tip = re.pose.bones[finger].matrix.translation.copy()
            pb = controls.pose.bones[control]
            pb.rotation_euler = (pb.rotation_euler.to_matrix() @ Quaternion(Vector((1,0,0)),math.radians(20)).to_matrix()).to_euler('XYZ',pb.rotation_euler)
            # Test the automatic dependency-graph handler used by native drags.
            bpy.context.view_layer.update(); bpy.context.view_layer.update()
            auto_result=result.evaluated_get(bpy.context.evaluated_depsgraph_get())
            assert (auto_result.pose.bones[finger].matrix.translation-before_tip).length>.1
            se, ce, re = evaluate(scene)
            finger_motion = (re.pose.bones[finger].matrix.translation-before_tip).length
            assert finger_motion > .1, ('finger control inactive',finger_motion)
            hand = controls.pose.bones['Main_G']
            before_hand = re.pose.bones[wrist].matrix.translation.copy()
            wanted = hand.matrix.copy(); wanted.translation += Vector((.4,.2,.1))
            hand.matrix = wanted
            bpy.context.view_layer.update(); bpy.context.view_layer.update()
            auto_result=result.evaluated_get(bpy.context.evaluated_depsgraph_get())
            assert (auto_result.pose.bones[wrist].matrix.translation-wanted.translation).length<.001
            se, ce, re = evaluate(scene)
            hand_motion_error = (re.pose.bones[wrist].matrix.translation-wanted.translation).length
            assert hand_motion_error < .001, ('hand IK mismatch',hand_motion_error)
            assert (re.pose.bones[wrist].matrix.translation-before_hand).length > .3
            # Commit the test edits as the user would; export changes frames.
            for pb in (controls.pose.bones[control],hand):
                for prop in ('location','rotation_euler','scale'):
                    pb.keyframe_insert(prop,frame=scene.frame_current,group=pb.name)
            addon.export_smd(scene,verification/'first-person-edited.smd')
            report['manual_controls'] = dict(finger_tip_motion=finger_motion,hand_target_error=hand_motion_error)
        report[view] = dict(tracks=len(addon.tracks(scene)),sampled_frames=sample_count,
                            source_matrix_error=max(source_errors),result_matrix_error=max(errors),
                            mesh_skinning_error=skin_error,bones=len(names),skins=len(json.loads(scene['vf_skins'])))
    (verification/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS',json.dumps(report),flush=True)


if __name__ == '__main__':
    verify()

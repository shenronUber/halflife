"""Animator controls and full-skeleton SMD export for the Vector Fields workshop.

The hidden source rig preserves the imported animation. The visible control rig
is editable, and the result rig carries only the original game bones. No code
has to be embedded or trusted in the .blend file.
"""
bl_info = {'name': 'Vector Fields - Atelier', 'author': 'Vector Fields',
           'version': (1, 0, 0), 'blender': (4, 5, 0), 'category': 'Animation'}

import json
import math
import shutil
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix, Vector

_busy = False
_signature = None
_enum_cache = {}


def objects(scene):
    return tuple(bpy.data.objects.get(scene.get(key, '')) for key in
                 ('vf_source', 'vf_controls', 'vf_result'))


def globals_from(locals_, parents):
    out = []
    for i, matrix in enumerate(locals_):
        out.append(out[parents[i]] @ matrix if parents[i] >= 0 else matrix.copy())
    return out


def locals_from(rig, names, parents):
    poses = [rig.pose.bones[n].matrix.copy() for n in names]
    return [poses[p].inverted() @ poses[i] if p >= 0 else poses[i]
            for i, p in enumerate(parents)]


def arm(locals_, parents, elbow, middle, wrist, target, pole, bind_relative=None):
    """Two-link solve preserving the authored intermediate joint and lengths."""
    g = globals_from(locals_, parents)
    shoulder = g[parents[elbow]].translation
    old_elbow = g[elbow].translation
    old_wrist = g[wrist].translation
    a = (old_elbow - shoulder).length
    b = (old_wrist - old_elbow).length
    delta = target.translation - shoulder
    distance = delta.length
    if distance < 1e-8:
        delta = old_wrist - shoulder
        distance = delta.length
    direction = delta.normalized()
    reach = min(max(distance, abs(a - b) + .0001), a + b - .0001)
    actual = shoulder + direction * reach
    pole_direction = pole - shoulder
    pole_direction -= direction * pole_direction.dot(direction)
    if pole_direction.length < 1e-5:
        pole_direction = old_elbow - shoulder
        pole_direction -= direction * pole_direction.dot(direction)
    if pole_direction.length < 1e-5:
        pole_direction = direction.cross(Vector((0, 0, 1)))
    if pole_direction.length < 1e-5:
        pole_direction = direction.cross(Vector((0, 1, 0)))
    along = (a*a - b*b + reach*reach) / (2*reach)
    height = math.sqrt(max(0., a*a - along*along))
    new_elbow = shoulder + along * direction + height * pole_direction.normalized()
    relative = g[elbow].inverted() @ g[wrist]
    if bind_relative is not None:
        translation=relative.translation.copy()
        relative=bind_relative.copy();relative.translation=translation
    desired = target.to_3x3() @ relative.to_3x3().transposed()
    old_direction = desired @ relative.translation
    new_direction = actual - new_elbow
    rotation = old_direction.rotation_difference(new_direction).to_matrix() @ desired
    forearm = rotation.to_4x4()
    forearm.translation = new_elbow
    locals_[elbow] = g[parents[elbow]].inverted() @ forearm
    g = globals_from(locals_, parents)
    rotation = g[middle].to_3x3().transposed() @ target.to_3x3()
    position = locals_[wrist].translation.copy()
    locals_[wrist] = rotation.to_4x4()
    locals_[wrist].translation = position
    return abs(reach - distance)


def update(scene, depsgraph=None, force=False):
    global _busy, _signature
    if _busy:
        return
    source, controls, result = objects(scene)
    if not all((source, controls, result)):
        return
    _busy = True
    try:
        depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
        source_eval = source.evaluated_get(depsgraph)
        controls_eval = controls.evaluated_get(depsgraph)
        names = json.loads(result['vf_names'])
        parents = json.loads(result['vf_parents'])
        mapping = json.loads(controls['vf_mapping'])
        locals_ = locals_from(source_eval, names, parents)
        signature = (scene.as_pointer(), scene.frame_current,
                     source.animation_data.action.name if source.animation_data.action else '',
                     tuple(round(x, 5) for pb in controls_eval.pose.bones
                           for row in pb.matrix for x in row),
                     tuple(round(x, 5) for m in locals_ for row in m for x in row))
        if not force and signature == _signature:
            return
        _signature = signature
        marker=scene.objects.get('Repère - rebord / dos vers visage')
        if marker:
            gesture=scene.get('vf_current','vf_hang_idle_0')
            marker.hide_set(not gesture.startswith('vf_hang'))
            if scene.get('vf_view')=='third-person':
                top=40.
                if gesture.startswith('vf_hang_aim_'):top=18.
                elif gesture=='vf_hang_arm_0':
                    t=max(0.,min(1.,(scene.frame_current_final-1)/max(1,scene.frame_end-1)))
                    top-=22*t*t*(3-2*t)
                marker.location.z=top-marker.scale.z
        if scene.get('vf_view') == 'first-person':
            error = 0.
            for side, elbow, middle, wrist in [('G', 'Bone40', 'Bone41', 'Bone42'),
                                               ('D', 'Bone05', 'Bone06', 'Bone07')]:
                target = controls_eval.pose.bones['Main_'+side].matrix.copy()
                pole = controls_eval.pose.bones['Coude_'+side].matrix.translation
                bind_relative=source.data.bones[elbow].matrix_local.inverted()@source.data.bones[wrist].matrix_local
                error = max(error, arm(locals_, parents, names.index(elbow),
                                       names.index(middle), names.index(wrist), target, pole,bind_relative))
            # Finger controls have the exact rest basis of the original bones.
            for control, bone in mapping.items():
                if not control.startswith(('G_', 'D_')):
                    continue
                cb = controls_eval.data.bones[control]
                rest = cb.parent.matrix_local.inverted() @ cb.matrix_local
                locals_[names.index(bone)] = rest @ controls_eval.pose.bones[control].matrix_basis
            result['vf_reach_warning'] = 'Main hors de portée : rapprocher la poignée.' if error > .02 else ''
        else:
            # The body workshop uses ordinary FK, with readable names.
            for control, bone in mapping.items():
                cb = controls_eval.data.bones[control]
                rest = cb.parent.matrix_local.inverted() @ cb.matrix_local if cb.parent else cb.matrix_local
                locals_[names.index(bone)] = rest @ controls_eval.pose.bones[control].matrix_basis
        for i, name in enumerate(names):
            bone = result.data.bones[name]
            rest = bone.parent.matrix_local.inverted() @ bone.matrix_local if bone.parent else bone.matrix_local
            result.pose.bones[name].matrix_basis = rest.inverted() @ locals_[i]
    finally:
        _busy = False


@persistent
def on_frame(scene, depsgraph=None):
    update(scene, depsgraph, True)


@persistent
def on_update(scene, depsgraph):
    update(scene, depsgraph)


@persistent
def on_load(_):
    global _signature
    _signature = None
    for scene in bpy.data.scenes:
        if scene.get('vf_source'):
            update(scene, force=True)


def tracks(scene):
    return json.loads(scene.get('vf_tracks', '[]'))


def items(self, context):
    if not context:
        return []
    data = context.scene.get('vf_tracks', '[]')
    if data not in _enum_cache:
        _enum_cache[data] = [(t['key'], t['label'], t['key']) for t in json.loads(data)]
    return _enum_cache[data]


def select_track(scene, key):
    global _signature
    source, controls, result = objects(scene)
    if not all((source, controls, result)):
        return
    track = next(t for t in tracks(scene) if t['key'] == key)
    source.animation_data.action = bpy.data.actions[track['source_action']]
    controls.animation_data.action = bpy.data.actions[track['control_action']]
    scene.frame_start = 1
    scene.frame_end = track['frames']
    scene.render.fps = round(track['fps'])
    scene.render.fps_base = scene.render.fps / track['fps']
    scene['vf_current'] = key
    _signature = None
    scene.frame_set(1)
    bpy.context.view_layer.update()
    update(scene, force=True)


def changed(self, context):
    if context.scene.get('vf_tracks'):
        select_track(context.scene, context.scene.vf_gesture)


def skin_items(self, context):
    if not context:
        return []
    data = context.scene.get('vf_skins', '[]')
    cache_key = 'skin:'+data
    if cache_key not in _enum_cache:
        _enum_cache[cache_key] = [(str(s['skin']), s['title'], s['title']) for s in json.loads(data)]
    return _enum_cache[cache_key]


def skin_changed(self, context):
    obj = bpy.data.objects.get(context.scene.get('vf_mesh',''))
    if not obj:
        return
    banks = json.loads(obj['vf_material_banks'])
    for i, name in enumerate(banks[int(context.scene.vf_skin)]):
        obj.data.materials[i] = bpy.data.materials[name]


def export_smd(scene, destination=None):
    source, controls, result = objects(scene)
    names = json.loads(result['vf_names'])
    parents = json.loads(result['vf_parents'])
    key = scene['vf_current']
    track = next(t for t in tracks(scene) if t['key'] == key)
    path = Path(destination) if destination else Path(bpy.path.abspath(scene['vf_exports'])) / (key+'.smd')
    lines = ['version 1', 'nodes'] + [f'{i} "{n}" {parents[i]}' for i, n in enumerate(names)] + ['end', 'skeleton']
    old_frame = scene.frame_current
    try:
        for f in range(1, track['frames']+1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            update(scene, force=True)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            actual = locals_from(result.evaluated_get(dg), names, parents)
            original = locals_from(source.evaluated_get(dg), names, parents)
            lines.append('time '+str(f-1))
            for i, (m, base) in enumerate(zip(actual, original)):
                # Weapon sockets may move during a draw; anatomical joints may
                # rotate but must retain their segment length.
                if i and names[i] not in {'VF_Weapon','VF_Magazine','VF_Bolt'} and abs(m.translation.length-base.translation.length) > .15:
                    raise ValueError('Longueur modifiée : '+names[i])
                if max(abs(s-1) for s in m.to_scale()) > .001:
                    raise ValueError('Échelle modifiée : '+names[i])
                values = [*m.translation, *m.to_euler('XYZ')]
                if not all(math.isfinite(v) for v in values):
                    raise ValueError('Transformation invalide : '+names[i])
                lines.append(str(i)+' '+' '.join(f'{v:.8f}' for v in values))
        lines.append('end')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, path.with_suffix('.smd.previous'))
        temporary = path.with_suffix('.smd.tmp')
        temporary.write_text('\n'.join(lines)+'\n', encoding='ascii')
        temporary.replace(path)
    finally:
        scene.frame_set(old_frame)
        bpy.context.view_layer.update()
        update(scene, force=True)
    return path


class VF_OT_Export(bpy.types.Operator):
    bl_idname = 'vf.export_gesture'
    bl_label = 'Exporter ce geste pour le jeu'
    bl_description = 'Écrit le SMD dans retouches, sans appliquer de changement au jeu'
    def execute(self, context):
        try:
            path = export_smd(context.scene)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Exporté : '+str(path))
        return {'FINISHED'}


class VF_OT_Select(bpy.types.Operator):
    bl_idname = 'vf.select_control'
    bl_label = 'Sélectionner une commande'
    control: bpy.props.StringProperty()
    def execute(self, context):
        _, controls, _ = objects(context.scene)
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        controls.select_set(True)
        context.view_layer.objects.active = controls
        bpy.ops.object.mode_set(mode='POSE')
        for b in controls.data.bones:
            b.select = b.name == self.control
        controls.data.bones.active = controls.data.bones.get(self.control)
        return {'FINISHED'}


class VF_OT_Key(bpy.types.Operator):
    bl_idname = 'vf.key_controls'
    bl_label = 'Enregistrer la pose sélectionnée'
    def execute(self, context):
        _, rig, _ = objects(context.scene)
        selected = [p for p in rig.pose.bones if p.bone.select]
        if not selected:
            self.report({'WARNING'}, 'Sélectionner une main ou un doigt.')
            return {'CANCELLED'}
        for p in selected:
            rotation = 'rotation_euler' if p.rotation_mode == 'XYZ' else 'rotation_quaternion'
            for property_ in ('location', rotation, 'scale'):
                p.keyframe_insert(property_, frame=context.scene.frame_current, group=p.name)
        return {'FINISHED'}


class VF_OT_View(bpy.types.Operator):
    bl_idname='vf.inspect_grip'
    bl_label='Contrôler la prise'
    angle:bpy.props.StringProperty(default='face')
    def execute(self,context):
        fp=context.scene.get('vf_view')=='first-person'
        target=Vector((18,0,7)) if fp else Vector((0,-18,38))
        eye=Vector((0,0,1.5)) if fp else Vector((0,28,54))
        if self.angle=='profil':eye=Vector((12,-40,18)) if fp else Vector((55,-5,46))
        if self.angle=='corps':target=Vector((0,-6,12));eye=Vector((65,85,55))
        for area in context.screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_location=target
                space.region_3d.view_distance=(eye-target).length
                space.region_3d.view_rotation=(eye-target).to_track_quat('Z','Y')
                space.region_3d.view_perspective='PERSP';space.lens=28
        return {'FINISHED'}


class VF_PT_Workshop(bpy.types.Panel):
    bl_label = 'Vector Fields - Animations'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Vector Fields'
    @classmethod
    def poll(cls, context):
        return bool(context.scene.get('vf_controls'))
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.prop(scene, 'vf_gesture', text='Geste')
        layout.prop(scene, 'vf_skin', text='Skin')
        row=layout.row(align=True)
        for label,angle in [('Visage','face'),('Profil','profil')]+([] if scene.get('vf_view')=='first-person' else [('Corps','corps')]):
            row.operator('vf.inspect_grip',text=label).angle=angle
        layout.label(text='G : déplacer | R : tourner | I : clé')
        layout.label(text='Ctrl+S : enregistrer le projet')
        if scene.get('vf_view') == 'first-person':
            for side, word in [('G', 'gauche'), ('D', 'droite')]:
                box = layout.box()
                row = box.row(align=True)
                for label, control in [('Main '+word, 'Main_'+side), ('Coude', 'Coude_'+side)]:
                    op = row.operator('vf.select_control', text=label)
                    op.control = control
                for finger in ('Pouce', 'Index', 'Majeur', 'Annulaire', 'Auriculaire'):
                    row = box.row(align=True)
                    row.label(text=finger)
                    for segment in range(1, 4 if finger == 'Pouce' else 5):
                        op = row.operator('vf.select_control', text=str(segment))
                        op.control = f'{side}_{finger}_{segment}'
        _, controls, result = objects(scene)
        if controls and context.object == controls and controls.data.bones.active:
            pb = controls.pose.bones[controls.data.bones.active.name]
            layout.label(text='Sélection : '+pb.name)
            if not all(pb.lock_location):
                layout.prop(pb, 'location', text='Position')
            layout.prop(pb, 'rotation_euler' if pb.rotation_mode == 'XYZ' else 'rotation_quaternion', text='Rotation')
        if result and result.get('vf_reach_warning'):
            layout.label(text=result['vf_reach_warning'], icon='ERROR')
        layout.operator('vf.key_controls', icon='KEY_HLT')
        layout.operator('vf.export_gesture', icon='EXPORT')


CLASSES = (VF_OT_Export, VF_OT_Select, VF_OT_Key, VF_OT_View, VF_PT_Workshop)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.vf_gesture = bpy.props.EnumProperty(name='Geste', items=items, update=changed)
    bpy.types.Scene.vf_skin = bpy.props.EnumProperty(name='Skin', items=skin_items, update=skin_changed)
    for collection, fn in ((bpy.app.handlers.frame_change_post, on_frame),
                           (bpy.app.handlers.depsgraph_update_post, on_update),
                           (bpy.app.handlers.load_post, on_load)):
        if fn not in collection:
            collection.append(fn)


def unregister():
    for collection, fn in ((bpy.app.handlers.frame_change_post, on_frame),
                           (bpy.app.handlers.depsgraph_update_post, on_update),
                           (bpy.app.handlers.load_post, on_load)):
        if fn in collection:
            collection.remove(fn)
    del bpy.types.Scene.vf_gesture
    del bpy.types.Scene.vf_skin
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)

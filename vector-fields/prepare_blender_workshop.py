"""Run inside Blender: prepare editable R1 hand/body scenes from workshop SMDs."""
import argparse
import json
import math
import re
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
WORKSHOP = ROOT/'animation-workshop/traversal'
OUT = WORKSHOP/'blender'
FINGERS = [('Pouce', [43,44,45], (1,.55,.1)),
           ('Index', [47,48,49,50], (.15,.45,1)),
           ('Majeur', [51,52,53,54], (.1,.85,.4)),
           ('Annulaire', [55,56,57,58], (.85,.25,.8)),
           ('Auriculaire', [59,60,61,62], (.15,.85,.9))]
LABELS = {'vf_hang_idle': 'Suspension à deux mains', 'vf_hang_catch': 'Saisie du rebord',
          'vf_climb': 'Remontée', 'vf_drop': 'Lâcher', 'vf_vault': 'Passage du muret', 'vf_stepup': 'Montée sur la plateforme',
          'vf_hang_arm': 'Passage au tir', 'vf_slide_start': 'Début de glissade',
          'vf_slide_loop': 'Glissade', 'vf_slide_end': 'Fin de glissade'}


def read_smd(path):
    nodes = {}; frames = {}; triangles = []; section = None; time = None
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip(); index += 1
        if line in ('nodes', 'skeleton', 'triangles'):
            section = line; continue
        if line == 'end':
            section = None; continue
        if not line or line.startswith('version'):
            continue
        if section == 'nodes':
            match = re.fullmatch(r'(\d+)\s+"([^"]+)"\s+(-?\d+)', line)
            i, name, parent = match.groups(); nodes[int(i)] = (name, int(parent))
        elif section == 'skeleton':
            if line.startswith('time '):
                time = int(line[5:]); frames[time] = {}
            else:
                row = line.split(); m = Euler(tuple(map(float, row[4:7])), 'XYZ').to_matrix().to_4x4()
                m.translation = Vector(tuple(map(float, row[1:4])))
                frames[time][int(row[0])] = m
        elif section == 'triangles':
            vertices = []
            for _ in range(3):
                row = lines[index].split(); index += 1
                vertices.append((int(row[0]), tuple(map(float,row[1:4])),
                                 tuple(map(float,row[4:7])), tuple(map(float,row[7:9]))))
            triangles.append((line, vertices))
    names = [nodes[i][0] for i in range(len(nodes))]
    parents = [nodes[i][1] for i in range(len(nodes))]
    return names, parents, [[frames[t][i] for i in range(len(nodes))] for t in sorted(frames)], triangles


def globals_from(locals_, parents):
    out = []
    for i, m in enumerate(locals_):
        out.append(out[parents[i]] @ m if parents[i] >= 0 else m.copy())
    return out


def make_armature(name, names, parents, matrices, lengths=None):
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for i, bone_name in enumerate(names):
        bone = data.edit_bones.new(bone_name)
        length = lengths[i] if lengths else 1.
        bone.head = matrices[i].translation
        bone.tail = matrices[i] @ Vector((0, length, 0))
        bone.align_roll(matrices[i].to_3x3() @ Vector((0, 0, 1)))
    for i, p in enumerate(parents):
        if p >= 0:
            data.edit_bones[names[i]].parent = data.edit_bones[names[p]]
    bpy.ops.object.mode_set(mode='OBJECT')
    for name, wanted in zip(names, matrices):
        actual = data.bones[name].matrix_local
        error = max(abs(x-y) for ra,rb in zip(actual,wanted) for x,y in zip(ra,rb))
        # Blender snaps orientations very close to its cardinal axes. The
        # importer compensates with the actual rest basis and rebinds vertices.
        assert error < .001, (name,error,str(actual),str(wanted))
    obj.select_set(False)
    for pb in obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.lock_scale = (True, True, True)
    obj.show_in_front = True
    obj['vf_order'] = json.dumps(names)
    data.display_type = 'STICK'
    return obj


def animate(rig, label, frames, matrices):
    action = bpy.data.actions.new(label)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    previous = {}
    for t, locals_ in enumerate(frames, 1):
        for i, name in enumerate(json.loads(rig['vf_order'])):
            pb = rig.pose.bones[name]
            rest = matrices[i]
            pb.matrix_basis = rest.inverted() @ locals_[i]
            rotation_property = 'rotation_euler' if pb.rotation_mode == 'XYZ' else 'rotation_quaternion'
            if name in previous:
                if rotation_property == 'rotation_euler':
                    pb.rotation_euler.make_compatible(previous[name])
                elif pb.rotation_quaternion.dot(previous[name]) < 0:
                    pb.rotation_quaternion.negate()
            previous[name] = getattr(pb, rotation_property).copy()
            for prop in ('location', rotation_property, 'scale'):
                pb.keyframe_insert(prop, frame=t, group=pb.name)
    # Blender 4.5 actions use slots; animation_data retains its matching slot.
    for slot in action.slots:
        channelbag = action.layers[0].strips[0].channelbag(slot)
        for fc in channelbag.fcurves:
            for key in fc.keyframe_points:
                key.interpolation = 'LINEAR'
    return action


def shape(name, rings):
    vertices = []; edges = []
    for plane in rings:
        offset = len(vertices)
        for i in range(24):
            a = i*2*math.pi/24; v = [0.,0.,0.]
            v[plane[0]], v[plane[1]] = math.cos(a), math.sin(a)
            vertices.append(v); edges.append((offset+i, offset+(i+1)%24))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.hide_render = True; obj.hide_set(True)
    return obj


def decorate(pb, widget, scale, color):
    pb.custom_shape = widget
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = (scale,)*3
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = color
    pb.color.custom.select = (1., .8, .3)
    pb.color.custom.active = (1., 1., 1.)


def materials(folder):
    banks = []
    skins = json.loads((folder/'skins.json').read_text(encoding='utf-8'))
    for skin in skins:
        bank = []
        for name in skin['textures']:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
            node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(str(folder/name), check_existing=True)
            node.image.pack()
            node.interpolation = 'Closest'
            shader = mat.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Roughness'].default_value = .8
            mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
            mat.node_tree.nodes.active = node
            bank.append(mat)
        banks.append(bank)
    return banks, skins


def mesh(triangles, names, rig, banks, skins, original_bind):
    vertices = []; faces = []; uv = []; normals = []; bones = []; material_indices = []
    material_names = skins[0]['textures']
    for mat, triangle in triangles:
        start = len(vertices)
        for bone, position, normal, texcoord in triangle:
            rebinding = rig.data.bones[names[bone]].matrix_local @ original_bind[bone].inverted()
            vertices.append(rebinding @ Vector(position)); bones.append(bone)
            normals.append(rebinding.to_3x3() @ Vector(normal)); uv.append(texcoord)
        faces.append((start,start+1,start+2)); material_indices.append(material_names.index(mat))
    data = bpy.data.meshes.new('R1 - géométrie originale')
    data.from_pydata(vertices, [], faces); data.update()
    layer = data.uv_layers.new(name='UVMap')
    for loop in data.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    for p, mat in zip(data.polygons, material_indices):
        p.material_index = mat; p.use_smooth = True
    data.normals_split_custom_set([normals[l.vertex_index] for l in data.loops])
    obj = bpy.data.objects.new('R1 - mains et manches' if bpy.context.scene['vf_view']=='first-person' else 'R1 - personnage',data)
    bpy.context.collection.objects.link(obj)
    for mat in banks[0]:
        data.materials.append(mat)
    obj['vf_material_banks'] = json.dumps([[m.name for m in bank] for bank in banks])
    groups = [obj.vertex_groups.new(name=n) for n in names]
    for i, b in enumerate(bones):
        groups[b].add([i], 1., 'REPLACE')
    modifier = obj.modifiers.new('Squelette du jeu', 'ARMATURE'); modifier.object = rig
    obj.hide_select = True
    return obj


def controls_fp(names, parents, bind):
    cnames = []; cparents = []; cbind = []; mapping = {}
    for side, wrist, elbow, prefix in [('G','Bone42','Bone40',''), ('D','Bone07','Bone05','VFRight_')]:
        hand_index = len(cnames)
        cnames.append('Main_'+side); cparents.append(-1); cbind.append(bind[names.index(wrist)].copy())
        cnames.append('Coude_'+side); cparents.append(-1); cbind.append(bind[names.index(elbow)].copy())
        for finger, ids, color in FINGERS:
            previous = hand_index
            for segment, num in enumerate(ids, 1):
                name = f'{side}_{finger}_{segment}'; original = prefix+'Bone'+str(num)
                cnames.append(name); cparents.append(previous); previous = len(cnames)-1
                cbind.append(bind[names.index(original)].copy()); mapping[name] = original
    controls = make_armature('VF_Commandes', cnames, cparents, cbind)
    ball = shape('Poignée - sphère', [(0,1),(1,2),(0,2)])
    ring = shape('Poignée - anneau', [(0,1),(1,2)])
    for pb in controls.pose.bones:
        pb.rotation_mode = 'XYZ'
        if pb.name.startswith('Main_'):
            decorate(pb, ring, 1.7, (.3,.6,1) if pb.name.endswith('G') else (1,.35,.2))
            pb.lock_location = (False,)*3
        elif pb.name.startswith('Coude_'):
            decorate(pb, ball, 1.2, (.8,.8,.3))
            pb.lock_rotation = (True,)*3
        else:
            finger = pb.name.split('_')[1]
            color = next(c for f,_,c in FINGERS if f == finger)
            decorate(pb, ball, .36 if pb.name.endswith('_1') else .27, color)
            pb.lock_location = (True,)*3
    controls['vf_mapping'] = json.dumps(mapping)
    return controls, cnames, cparents, cbind, mapping


def controls_body(folder, names, parents, bind):
    rows = json.loads((folder/'bones.json').read_text(encoding='utf-8'))
    cnames = [r['role']+' ['+r['bone']+']' for r in rows]
    # Labels must fit Blender's bone-name length limit.
    cnames = [n[:60] for n in cnames]
    rig = make_armature('VF_Commandes', cnames, parents, bind)
    widget = shape('Poignée - corps', [(0,1),(1,2),(0,2)])
    for pb, row in zip(rig.pose.bones, rows):
        pb.rotation_mode = 'XYZ'
        pb.lock_location = (True,)*3
        if row['usage'] == 'Aucun mesh visible':
            pb.bone.hide = True
        else:
            decorate(pb, widget, 1.3 if 'main' in row['role'] else .65, (.25,.7,1))
    mapping = dict(zip(cnames, names)); rig['vf_mapping'] = json.dumps(mapping)
    return rig, cnames, parents, bind, mapping


def control_frames(view, names, parents, frames, cnames, cparents, mapping):
    out = []
    for frame in frames:
        g = globals_from(frame, parents)
        if view == 'third-person':
            out.append(frame); continue
        values = []
        for name in cnames:
            if name.startswith('Main_'):
                values.append(g[names.index('Bone42' if name.endswith('G') else 'Bone07')].copy())
            elif name.startswith('Coude_'):
                values.append(g[names.index('Bone40' if name.endswith('G') else 'Bone05')].copy())
            else:
                values.append(frame[names.index(mapping[name])].copy())
        out.append(values)
    return out


def setup_view(scene, controls, center, distance):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.type = 'MATERIAL'
                space.show_region_ui = True
                space.overlay.show_floor = False
                space.overlay.show_axis_x = False; space.overlay.show_axis_y = False
                space.region_3d.view_location = center
                space.region_3d.view_distance = distance
                view = Vector((-1.,-.18,.35)) if scene['vf_view']=='first-person' else Vector((1.,-.5,.2))
                space.region_3d.view_rotation = view.to_track_quat('Z','Y')
                space.region_3d.view_perspective = 'PERSP'
                space.clip_start = .05; space.clip_end = 2000
            elif area.type == 'PROPERTIES' and screen.name == 'Layout':
                area.type = 'DOPESHEET_EDITOR'
                area.spaces.active.mode = 'ACTION'
    bpy.context.view_layer.objects.active = controls
    controls.hide_set(False); controls.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    if scene['vf_view'] == 'first-person':
        for bone in controls.data.bones:
            bone.select = bone.name == 'Main_G'
        controls.data.bones.active = controls.data.bones['Main_G']
    scene.tool_settings.use_keyframe_insert_auto = True
    scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
    scene.transform_orientation_slots[0].type = 'LOCAL'


def reference(scene, controls, view):
    if view != 'first-person':
        return Vector((0,0,30)), 100
    left = controls.pose.bones['Main_G'].matrix.translation
    right = controls.pose.bones['Main_D'].matrix.translation
    center = (left+right)*.5 + Vector((0,0,1))
    # A purely visual board for judging the grip; exported SMD contains no props.
    contact = []
    for side in ('G','D'):
        contact.append(controls.pose.bones['Main_'+side].matrix @ Vector((0,4.,-1.)))
    top = (contact[0]+contact[1])*.5
    bpy.ops.mesh.primitive_cube_add(size=1, location=top+Vector((3.,0,-3.)))
    board = bpy.context.object; board.name = 'Repère - rebord (ajustable)'
    board.dimensions = (6,max(35,abs(left.y-right.y)+15),6)
    material = bpy.data.materials.new('Rebord de référence'); material.diffuse_color = (.18,.24,.3,1)
    board.data.materials.append(material); board.hide_select = True
    board['note'] = 'Repère visuel de prise, à ajuster au besoin. Jamais exporté dans le jeu.'
    return center, 45


def build(view, addon, suffix=''):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # Hidden and unselectable rigs/meshes from the preceding view must also go.
    # Operators skip those objects, leaving FPS arms in the body workshop.
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    # Each workshop is an independent .blend with its own action library.
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    scene = bpy.context.scene; scene['vf_view'] = view
    folder = WORKSHOP/view
    names, parents, reference_frames, triangles = read_smd(folder/'reference.smd')
    bind = globals_from(reference_frames[0], parents)
    source = make_armature('VF_Source', names, parents, bind)
    result = make_armature('VF_Jeu', names, parents, bind)
    result['vf_names'] = json.dumps(names); result['vf_parents'] = json.dumps(parents)
    controls, cnames, cparents, cbind, mapping = (controls_fp(names,parents,bind)
        if view == 'first-person' else controls_body(folder,names,parents,bind))
    actual_cbind = [controls.data.bones[n].matrix_local.copy() for n in cnames]
    crest = [actual_cbind[p].inverted() @ actual_cbind[i] if p >= 0 else actual_cbind[i] for i,p in enumerate(cparents)]
    actual_source_bind = [source.data.bones[n].matrix_local.copy() for n in names]
    source_rest = [actual_source_bind[p].inverted() @ actual_source_bind[i] if p >= 0 else actual_source_bind[i] for i,p in enumerate(parents)]
    banks, skins = materials(folder)
    mesh_object = mesh(triangles,names,result,banks,skins,bind)
    scene['vf_mesh'] = mesh_object.name
    scene['vf_skins'] = json.dumps(skins, ensure_ascii=False)
    records = [r for r in json.loads((WORKSHOP/'gestures.json').read_text()) if r['view'] == view]
    records.sort(key=lambda r: (r['gesture'] != 'vf_hang_idle', r['gesture'], r['corner']))
    tracks = []
    for record in records:
        key = record['gesture']+'_'+str(record['corner'])
        accepted = ROOT/'assets/animations/traversal-edits'/view/(key+'.smd')
        path = accepted if accepted.exists() and record['gesture'] not in ('vf_vault','vf_stepup') else folder/(key+'.smd')
        frame_names, frame_parents, frames, _ = read_smd(path)
        assert frame_names == names and frame_parents == parents, 'Mismatched source skeleton'
        source_action = animate(source, 'SOURCE|'+key, frames, source_rest)
        cf = control_frames(view,names,parents,frames,cnames,cparents,mapping)
        control_action = animate(controls, 'RETouche|'+key, cf, crest)
        label = LABELS.get(record['gesture'], record['gesture'])
        if 'both_' in record['gesture'] or 'aim_' in record['gesture']:
            label += ' / secteur '+str(record['corner'])
        tracks.append(dict(key=key,label=label,frames=len(frames),fps=record['fps'],
                           source_action=source_action.name,control_action=control_action.name,
                           original=str(path)))
        print('Imported', view, key, len(frames), flush=True)
    source.hide_set(True); result.hide_set(True)
    source.hide_render = True; result.hide_render = True
    source.hide_select = True; result.hide_select = True
    scene['vf_source'] = source.name; scene['vf_controls'] = controls.name; scene['vf_result'] = result.name
    scene['vf_tracks'] = json.dumps(tracks, ensure_ascii=False)
    scene['vf_exports'] = '//../retouches/'+view
    # Assign a valid enum after tracks exist; callback connects both action slots.
    scene.vf_gesture = 'vf_hang_idle_0'
    addon.select_track(scene, 'vf_hang_idle_0')
    center, distance = reference(scene,controls,view)
    setup_view(scene,controls,center,distance)
    scene.world.color = (.15,.15,.15)
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    for text in list(bpy.data.texts):
        if text.name.startswith('LIRE-MOI'):
            bpy.data.texts.remove(text)
    guide = bpy.data.texts.new('LIRE-MOI - Atelier')
    guide.write((OUT/'LIRE-MOI.md').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True,exist_ok=True)
    destination = OUT/(('Mains-R1' if view=='first-person' else 'Corps-R1')+suffix+'.blend')
    if destination.exists():
        if suffix:raise FileExistsError(str(destination))
        # Rebuilding creates a new base; never overwrite the animator's project.
        destination = destination.with_name(destination.stem+'-nouvelle-base.blend')
        if destination.exists():
            raise RuntimeError('A new base already exists; preserve manual projects before rebuilding.')
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    print('SAVED', destination, flush=True)
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--view', choices=['first-person','third-person','both'],default='both')
    parser.add_argument('--suffix',default='')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    import addon_utils
    addon_utils.enable('io_scene_valvesource', default_set=True, persistent=True)
    addon = addon_utils.enable('vf_workshop', default_set=True, persistent=True)
    if addon is None:
        raise RuntimeError('Workshop addon failed to load')
    bpy.context.preferences.view.show_splash = False
    bpy.ops.wm.save_userpref()
    views = ('first-person','third-person') if args.view == 'both' else (args.view,)
    for view in views:
        build(view,addon,args.suffix)


if __name__ == '__main__':
    main()

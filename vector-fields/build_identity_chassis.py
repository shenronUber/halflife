"""Install reviewed chassis modules without rebuilding animated carriers.

Organic receivers have one intrinsic atlas. Metallic receivers may carry the
subsequent reviewed two-atlas revision; that revision is recognized by hash.
The first trigger revision retains legacy texture/skin/animation blocks.
"""
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSHOP = ROOT/'chassis-workshop/identity-2026-10-11'
SPECS = {
    'm40': dict(name='R-01 / Fonderie', family='Baseline', collection='chassis-fonderie',
                title='Fonderie', description='Recepteur tubulaire bleui, bakelite et marquage de fonderie.'),
    'a47': dict(name='R-01 / Vieux arsenal', family='Engine', collection='chassis-arsenal',
                title='Vieux arsenal', description='Capot embouti, nervures, rivets et garde-main sombre nervure.'),
    'ossuary': dict(name='R-01 / Ossuaire', family='Rogue', collection='chassis-ossuaire',
                    title='Ossuaire', description='Os de cervide et tendons autour d une armature mecanique visible.'),
    'bramble': dict(name='R-01 / Roncier', family='Fortress', collection='chassis-roncier',
                    title='Roncier', description='Branches irregulieres et ligatures autour d une armature mecanique.'),
}
INTRINSIC = {'r01_receiver_'+key: spec for key, spec in SPECS.items()}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs():
    paths = [Path(__file__), WORKSHOP/'manifest.json', WORKSHOP/'legacy-trigger-review/manifest.json']
    paths += [WORKSHOP/(name+'.py') for name in
              ('stage_legacy_triggers', 'trigger_geometry', 'coaxial_geometry', 'legacy_alignment', 'axis_export')]
    paths += [WORKSHOP/key/'export'/('r01_receiver_'+key+'.mdl') for key in SPECS]
    report = json.loads((WORKSHOP/'legacy-trigger-review/manifest.json').read_text(encoding='utf-8'))
    paths += [WORKSHOP/'legacy-trigger-review'/r['key']/('r01_receiver_'+r['key']+'.mdl') for r in report['assets']]
    return paths


def base_rows():
    return ['|'.join(['receiver', ident, '1', spec['name'], spec['family'], spec['title'],
                     '4', '4', '4', '4', '0', '0', spec['description']+
                     ' Texture propre au chassis. Alimentation dessous.', '0'])
            for ident, spec in INTRINSIC.items()]


def inventory_row(base,style='original'):
    fields = base.split('|') if isinstance(base, str) else list(base)
    ident = fields[1]
    fields = fields[:14]+['', ident, style.replace('-','_')]
    fields[1] = ident+'__'+style
    if style!='original':
        assert style=='medieval-forge'
        fields[3]=fields[3].removeprefix('R-01 / ')+' Forge medievale'
        fields[5]='Forge medievale'
    return fields


def append_catalog(data):
    """Only append missing objects; keep every existing byte and object index."""
    rows = {r.split('|')[1]: r for r in data.decode('ascii').splitlines()
            if r and not r.startswith(('#', 'limits|'))}
    additions = []
    for base in base_rows():
        for row in (base, '|'.join(inventory_row(base))):
            ident = row.split('|')[1]
            if ident in rows:
                if rows[ident] != row:
                    raise ValueError('Existing chassis catalogue entry differs: '+ident)
            else:
                additions.append(row)
    if not additions:
        return data
    return data+(b'' if data.endswith(b'\n') else b'\n')+(
        '# Reviewed chassis: one intrinsic texture per new model.\n'+'\n'.join(additions)+'\n').encode('ascii')


def collections():
    return [dict(id=s['collection'], key=k, name=s['title'], family=s['family'],
                 item_suffix='', intrinsic_weapon_texture=True) for k, s in SPECS.items()]


def pool_entry(fields, index):
    spec = INTRINSIC[fields[15]]
    medieval=fields[16]=='medieval_forge'
    return dict(id=fields[1], name=fields[3], family=fields[4], collection='medieval-forge' if medieval else spec['collection'],
                slot='receiver', status='authored', weight=1, equipment_id=fields[1],
                equipment_index=index, weapon_style=2 if medieval else 0, intrinsic_texture=True,
                model='models/vf_r01/'+fields[15]+'.mdl')


def revision_api():
    if str(WORKSHOP) not in sys.path:
        sys.path.insert(0, str(WORKSHOP))
    spec = importlib.util.spec_from_file_location('_reviewed_chassis_revision', WORKSHOP/'stage_legacy_triggers.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_modules(folder, records=None):
    """Patch only receiver MDLs. A changed skin bank is rebuilt from that bank."""
    from studio_assets import Studio
    from build_r01_finish import is_current
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    old = json.loads((WORKSHOP/'legacy-trigger-review/manifest.json').read_text(encoding='utf-8'))
    byid = {r['id']: r for r in (records or [])}
    audit = []
    api = None
    for revision in old['assets']:
        key = revision['key']; ident = 'r01_receiver_'+key
        destination = folder/(ident+'.mdl')
        if not destination.is_file():
            raise FileNotFoundError('Existing receiver missing: '+str(destination))
        before = digest(destination)
        if is_current(destination):
            audit.append(dict(id=ident,action='reviewed fitted atlases',after=before,skin_families=14))
            continue
        if before == revision['staged_sha256']:
            action = 'already reviewed'
        elif before == revision['source_sha256']:
            source = WORKSHOP/'legacy-trigger-review'/key/destination.name
            assert digest(source) == revision['staged_sha256']
            shutil.copy2(source, destination); action = 'reviewed native geometry'
        else:
            # Retopology is joined to the latest receiver, preserving that file's
            # textures, families, sequences, normals and retained native UVs.
            api = api or revision_api()
            original = Studio(destination)
            removed = api.old_trigger_ids(original.mesh())
            expected = 112 if key in ('arch', 'arch_top', 'gyre') else 164
            if len(removed) != expected:
                raise ValueError('Receiver geometry changed; re-review before replacement: '+ident)
            removed_axial, translations, _ = api.alignment_changes(key, original)
            authored = api.parts()+api.legacy_parts(key)
            construction = folder/'identity-revisions'/key
            area, remap = api.compile_area(original, construction, authored)
            candidate = construction/destination.name
            api.join_native(original, area, remap, removed|removed_axial, candidate, translations)
            if digest(destination) != before:
                raise RuntimeError('Receiver changed during revision: '+str(destination))
            shutil.copy2(candidate, destination); action = 'rebased on current texture bank'
        model = Studio(destination)
        if ident in byid:
            byid[ident].update(triangles=len(model.mesh()), bytes=len(model.data), sha256=digest(destination),
                              skin_families=model.numskinfamilies, geometry_revision='identity-2026-10-11')
        audit.append(dict(id=ident, action=action, before=before, after=digest(destination),
                          skin_families=model.numskinfamilies))
    proposal = json.loads((WORKSHOP/'manifest.json').read_text(encoding='utf-8'))
    proposals = {r['key']: r for r in proposal['assets']}
    for variant, (key, spec) in enumerate(SPECS.items(), 9):
        ident = 'r01_receiver_'+key
        source = WORKSHOP/key/'export'/(ident+'.mdl'); destination = folder/source.name
        assert digest(source) == proposals[key]['compiled_sha256']
        polished=is_current(destination)
        if destination.exists() and digest(destination) != digest(source) and not polished:
            raise ValueError('New chassis destination already contains another revision: '+str(destination))
        if not destination.exists():
            shutil.copy2(source, destination)
        model = Studio(destination)
        assert model.numskinfamilies == (14 if polished else 1) and model.names == ['module_root']
        record = dict(id=ident, slot='receiver', slot_index=9, variant=variant, name=spec['name'],
                      triangles=len(model.mesh()), bytes=len(model.data), sha256=digest(destination),
                      skin_families=model.numskinfamilies, intrinsic_texture=True, feed_mount='bottom',
                      geometry_revision='identity-2026-10-11')
        if records is not None:
            if ident in byid:
                byid[ident].update(record)
            else:
                records.append(record)
        audit.append(dict(id=ident, action='intrinsic texture chassis', after=digest(destination), skin_families=model.numskinfamilies))
    return audit


def update_manifest(manifest, folder):
    audit = apply_modules(folder, manifest['pieces'])
    slots = {r['slot'] for r in manifest['pieces']}
    manifest['combinations'] = math.prod(sum(r['slot']==slot for r in manifest['pieces']) for slot in slots)
    manifest['reviewed_chassis'] = dict(revision='identity-2026-10-11', new_models=list(INTRINSIC),
                                      organic_skin_families=1, retained_legacy_skin_families=14)
    return audit

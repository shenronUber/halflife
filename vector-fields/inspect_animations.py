"""Build an offline workshop from the compiled FP models and CS reload donors.

The current third-person carrier stays untouched. Donor motions are retargeted
onto its 28 existing bones and exported as editable SMDs in generated/animation-workshop.
"""
import base64, hashlib, io, json, struct
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
from studio_assets import Studio, canonical
from animation_assets import sequence_info, sequence_frames, packed_frames, globals_of
from build_personas import donor, ASSETS
import build_modular as base

ROOT = Path(__file__).resolve().parent
FP = ROOT/'generated/r01'
TP = ROOT/'generated/personas'
OUT = ROOT/'generated/animation-workshop'


class Export:
    def __init__(self):
        self.textures = []
        self.texture_ids = {}
        self.models = {}

    def texture(self, texture):
        _, w, h, pixels, palette = texture
        key = hashlib.sha256(struct.pack('<ii', w, h)+pixels+palette).hexdigest()
        if key not in self.texture_ids:
            im = Image.frombytes('P', (w, h), pixels)
            im.putpalette(palette)
            b = io.BytesIO()
            im.convert('RGB').save(b, format='PNG')
            self.texture_ids[key] = len(self.textures)
            self.textures.append('data:image/png;base64,'+base64.b64encode(b.getvalue()).decode())
        return self.texture_ids[key]

    def model(self, key, model, bones, kind, choices=None, socket=None):
        buckets = defaultdict(list)
        for material, rows in model.mesh(choices):
            for row in rows:
                inv = np.linalg.inv(model.bind[row['b']]) if socket is None else np.eye(4)
                p = (inv@np.r_[row['p'], 1])[:3]
                n = inv[:3, :3]@row['n']
                bone = bones.index(model.names[row['b']]) if socket is None else bones.index(socket)
                buckets[material].append([*p, *n, *row['uv'], bone])
        groups = []
        for material, vertices in buckets.items():
            # mesh() returns a texture index from skin zero. Resolve its slot
            # across the actual compiled skin table, preserving skin families.
            ref = model.skin[:model.numskinref].index(material) if model.skin else material
            textures = [self.texture(model.textures[model.skin[skin*model.numskinref+ref] if model.skin else ref])
                        for skin in range(max(1, model.numskinfamilies) if kind in ('gloves', 'sleeves', 'body', 'weapon', 'magazine') else 1)]
            groups.append(dict(vertices=np.round(vertices, 6).tolist(), textures=textures))
        self.models[key] = dict(kind=kind, groups=groups, source=str(model.path))
        return key


def clip(model, name, label=None):
    info = sequence_info(model, name)
    return dict(label=label or name, source=name, fps=info['fps'], frames=packed_frames(sequence_frames(model, name)))


def retarget(source, target, name):
    lookup = {canonical(n): i for i, n in enumerate(source.names)}
    mapping = [lookup[canonical(n)] for n in target.names]
    result = []
    for frame in sequence_frames(source, name):
        g = globals_of(frame, source.parents)
        posed = np.array([g[b]@np.linalg.inv(source.bind[b])@target.bind[i] for i, b in enumerate(mapping)])
        result.append([np.linalg.inv(posed[target.parents[i]])@m if target.parents[i]>=0 else m
                       for i, m in enumerate(posed)])
    return np.array(result)


def smd_motion(target, name, frames):
    """StudioMDL applies +90 degrees around Z to roots when compiling SMD."""
    lines = ['version 1', 'nodes']
    lines += [f'{i} "{n}" {target.parents[i]}' for i, n in enumerate(target.names)]
    lines += ['end', 'skeleton']
    undo = np.eye(4)
    undo[:3, :3] = Rotation.from_euler('z', -90, degrees=True).as_matrix()
    for t, frame in enumerate(frames):
        lines.append('time '+str(t))
        for i, m in enumerate(frame):
            m = undo@m if target.parents[i]<0 else m
            v = [*m[:3, 3], *Rotation.from_matrix(m[:3, :3]).as_euler('xyz')]
            lines.append(str(i)+' '+' '.join(f'{x:.8f}' for x in v))
    lines.append('end')
    path = OUT/(name+'.smd')
    path.write_text('\n'.join(lines)+'\n', encoding='ascii')
    return path


def merge_weapon(rig, weapon):
    names = list(rig.names)
    parents = list(rig.parents)
    local = [np.linalg.inv(rig.bind[rig.parents[i]])@m if rig.parents[i]>=0 else m for i, m in enumerate(rig.bind)]
    for i, name in enumerate(weapon.names):
        if name in names:
            continue
        parent = weapon.parents[i]
        parents.append(names.index(weapon.names[parent]) if parent>=0 else -1)
        local.append(np.linalg.inv(weapon.bind[parent])@weapon.bind[i] if parent>=0 else weapon.bind[i])
        names.append(name)
    return names, parents, np.array(local)


def cache_fingerprints():
    """Hash compiled inputs separately from the UI for fast repeat openings."""
    sources = []
    for folder in ['generated/r01', 'generated/personas', 'generated/third-person',
                   'generated/deaths', 'build/animation-workshop/baseline']:
        sources.extend((ROOT/folder).glob('*.mdl'))
    sources.extend((ROOT/'generated/effects').glob('*.spr'))
    sources.extend((ROOT/'assets/audio/operator-deaths').glob('*/*_v2.wav'))
    from inspector_death_emissions import sources as emission_sources
    sources.extend(emission_sources())
    sources += [ROOT/rel for rel in [
        'inspect_animations.py', 'inspector_deaths.py', 'animation_assets.py', 'studio_assets.py',
        'generated/r01/manifest.json', 'generated/r01/first-person.json',
        'generated/third-person/manifest.json', 'generated/deaths/manifest.json',
        'generated/animation-workshop/persona_rig_cs_preview.mdl',
        'assets/animations/death-atlas.json', 'assets/audio/operator-deaths/manifest.json',
        'data/death_voices.json', 'data/effects.json', 'assets/personas/personas.json']]
    config = json.loads((ASSETS/'personas.json').read_text())
    sources += [Path(donor(config)['path']), ROOT.parent/'runtime/vector-engine/vf_visual/models/p_9mmAR.mdl']
    def digest(paths):
        h = hashlib.sha256()
        for path in sorted(set(paths)):
            h.update(str(path).encode('utf-8'))
            h.update(path.read_bytes() if path.exists() else b'MISSING')
        return h.hexdigest()
    return dict(assets=digest(sources), ui=digest([ROOT/'animation_inspector.template.html', ROOT/'animation_inspector_deaths.js', ROOT/'animation_inspector_emissions.js']))


def save_cache():
    record = cache_fingerprints()
    record['page_bytes'] = (ROOT/'build/animation-inspector.html').stat().st_size
    (OUT/'export-cache.json').write_text(json.dumps(record, indent=2), encoding='utf-8')


def use_cached_page():
    page = ROOT/'build/animation-inspector.html'
    cache = OUT/'export-cache.json'
    if not page.exists() or not cache.exists():
        return False
    record = json.loads(cache.read_text(encoding='utf-8'))
    current = cache_fingerprints()
    if record['assets'] != current['assets'] or page.stat().st_size != record['page_bytes']:
        return False
    if record['ui'] != current['ui']:
        # Reuse the embedded meshes and WAVs when only controls/rendering change.
        contents = page.read_text(encoding='utf-8')
        data = contents.split('<script id="data" type="application/json">', 1)[1].split('</script>', 1)[0]
        template = (ROOT/'animation_inspector.template.html').read_text(encoding='utf-8-sig')
        template = template.replace('__DEATH_SCRIPT__', (ROOT/'animation_inspector_deaths.js').read_text(encoding='utf-8')+'\n'+(ROOT/'animation_inspector_emissions.js').read_text(encoding='utf-8'))
        page.write_text(template.replace('__DATA__', data), encoding='utf-8')
        save_cache()
    print('Atelier disponible:', page)
    return True


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    e = Export()
    scenes = {}
    manifest = json.loads((FP/'manifest.json').read_text())
    common = [p for p in manifest['pieces'] if p['variant']==0 and p['slot'] not in ('receiver', 'feed')]
    for key, receiver, suffix in [('bottom','a',''), ('side','side','_side'), ('top','top','_top')]:
        rig = Studio(FP/f'r01_rig{suffix}.mdl')
        models = []
        for kind in ('gloves','sleeves'):
            modelkey = key+'_'+kind
            models.append(e.model(modelkey, Studio(FP/f'r01_fp_{kind}.mdl'), rig.names, kind))
        for record in [p for p in common if p['slot']!='underbarrel']+[dict(id='r01_receiver_'+receiver,slot='receiver')]:
            modelkey = key+'_'+record['id']
            offset = [3.4,0,0] if key=='top' and record['slot']=='optic' else [0,0,0]
            e.model(modelkey, Studio(FP/(record['id']+'.mdl')), rig.names, 'weapon', socket='R01_Bolt' if record['slot']=='chamber' else 'Bone76')
            if any(offset):
                for group in e.models[modelkey]['groups']:
                    for row in group['vertices']:
                        row[:3] = [a+b for a,b in zip(row[:3],offset)]
            models.append(modelkey)
        mags = [e.model(key+'_mag_'+v, Studio(FP/f'r01_feed_{v}.mdl'), rig.names, 'magazine', socket='Bone71') for v in 'abcd']
        underbarrels = [e.model(key+'_underbarrel_'+v, Studio(FP/f'r01_underbarrel_{v}.mdl'), rig.names, 'weapon', socket='Bone76') for v in 'abcd']
        fg = Studio(FP/f'r01_rig{suffix}_fg.mdl')
        previous = ROOT/'build/animation-workshop/baseline'/f'r01_rig{suffix}.mdl'
        before = {k:clip(Studio(previous), name, label) for k,name,label in [('aim','idle','Maintien'),('shoot','shoot1_1','Tir'),('reload','reload','Rechargement')]} if previous.exists() else {}
        scenes[key] = dict(before_clips=before,label={'bottom':'Première personne · dessous','side':'Première personne · latéral','top':'Première personne · dessus'}[key],
            bones=rig.names, parents=rig.parents, models=models, magazines=mags, underbarrels=underbarrels,
            foregrip_clips={k:clip(fg, name, label) for k,name,label in [('aim','idle','Maintien'),('shoot','shoot1_1','Tir'),('reload','reload','Rechargement')]}, hand=rig.names.index('Bone42'),
            index=[rig.names.index(n) for n in ['Bone47','Bone48','Bone49','Bone50']],
            clips={k:clip(rig, name, label) for k,name,label in [('aim','idle','Maintien'),('shoot','shoot1_1','Tir'),('reload','reload','Rechargement')]},
            note='La prise suit l’accessoire équipé : poignée inclinée ou appui standard. La main revient sur la poignée après la recharge de 1,5 s. « Prise précédente » compare la version de départ. Les curseurs restent locaux.')
    rig = Studio(TP/'persona_rig.mdl')
    weapon = Studio(ROOT.parent/'runtime/vector-engine/vf_visual/models/p_9mmAR.mdl')
    names, parents, rest = merge_weapon(rig, weapon)
    body = e.model('operator', Studio(TP/'persona_scout.mdl'), names, 'body', choices={i:1 for i in range(5)})
    carried = e.model('carried', weapon, names, 'weapon')
    def extended(frames):
        return np.concatenate([frames, np.repeat(rest[None, len(rig.names):], len(frames), axis=0)], axis=1)
    current = {}
    for k,name,label in [('aim','ref_aim_mp5','Maintien actuel'),('shoot','ref_shoot_mp5','Tir actuel'),('crouch_shoot','crouch_shoot_mp5','Tir accroupi actuel')]:
        current[k] = dict(label=label, source=name, fps=sequence_info(rig,name)['fps'], frames=packed_frames(extended(sequence_frames(rig,name))))
    current['reload'] = dict(current['aim'],label='Recharge actuelle · aucun geste dédié')
    scenes['third_current'] = dict(label='Troisième personne · jeu actuel',bones=names,parents=parents,models=[body,carried],magazines=[],hand=names.index('Bip01 L Hand'),index=[],clips=current,
        note='Animations TFC ajustées à la géométrie GIGN. Arme portée historique. La recharge conserve la pose de maintien : aucun geste dédié n’est présent dans le jeu.')
    config = json.loads((ASSETS/'personas.json').read_text())
    source = Studio(donor(config)['path'])
    borrowed = {}
    motions = []
    for k,name,label in [('aim','ref_aim_mp5','Maintien CS'),('shoot','ref_shoot_mp5','Tir CS'),('reload','ref_reload_mp5','Recharge MP5 · 1,5 s'),('rifle','ref_reload_rifle','Recharge fusil · 3 s'),('carbine','ref_reload_carbine','Recharge carabine · 2 s'),('crouch_reload','crouch_reload_mp5','Recharge MP5 accroupie')]:
        frames = retarget(source,rig,name)
        smd_motion(rig,name,frames)
        preview_path = OUT/'persona_rig_cs_preview.mdl'
        preview = Studio(preview_path) if preview_path.exists() else None
        if preview and name in preview.sequences:
            frames = sequence_frames(preview,name)
        borrowed[k] = dict(label=label,source=name,fps=sequence_info(source,name)['fps'],frames=packed_frames(extended(frames)))
        motions.append(dict(sequence=name,frames=len(frames),fps=sequence_info(source,name)['fps'],smd=str(OUT/(name+'.smd'))))
    scenes['third_cs'] = dict(label='Troisième personne · essais Counter-Strike',bones=names,parents=parents,models=[body,carried],magazines=[],hand=names.index('Bip01 L Hand'),index=[],clips=borrowed,
        note='Gestes Counter-Strike transférés sur nos 28 os. Essai hors jeu : le chargeur de l’arme historique reste fixe. Contact, chargeur mobile et déclenchement en jeu restent à adapter.')
    from third_person import OUT as CUSTOM, RECIPE
    custom_manifest = CUSTOM/'manifest.json'
    if custom_manifest.exists():
        authored = json.loads(custom_manifest.read_text(encoding='utf-8'))
        for platform,suffix in [('bottom',''),('side','_side'),('top','_top')]:
            custom = Studio(CUSTOM/f'r01_tp{suffix}.mdl')
            key = 'third_'+platform
            models = [e.model(key+'_body', Studio(TP/'persona_scout.mdl'), custom.names, 'body', choices={i:1 for i in range(5)})]
            for record in common+[dict(id='r01_receiver_'+dict(bottom='a',side='side',top='top')[platform],slot='receiver')]:
                modelkey = key+'_'+record['id']
                e.model(modelkey, Studio(FP/(record['id']+'.mdl')), custom.names, 'weapon', socket='VF_Bolt' if record['slot']=='chamber' else 'VF_Weapon')
                for group in e.models[modelkey]['groups']:
                    for row in group['vertices']:
                        if platform=='top' and record['slot']=='optic':row[0]+=3.4
                        row[:3]=[x*authored['recipe']['weapon']['scale'] for x in row[:3]]
                models.append(modelkey)
            mags=[]
            for v in 'abcd':
                modelkey=e.model(key+'_mag_'+v, Studio(FP/f'r01_feed_{v}.mdl'), custom.names, 'magazine', socket='VF_Magazine')
                for group in e.models[modelkey]['groups']:
                    for row in group['vertices']:row[:3]=[x*authored['recipe']['weapon']['scale'] for x in row[:3]]
                mags.append(modelkey)
            clips={k:clip(custom,n,label) for k,n,label in [('aim','ref_aim_mp5','Tenue R-01'),('shoot','ref_shoot_mp5','Tir R-01'),('reload','ref_reload_mp5','Recharge adaptée · MP5'),('rifle','ref_reload_rifle','Recharge adaptée · fusil'),('crouch_aim','crouch_aim_mp5','Tenue accroupie'),('crouch_reload','crouch_reload_mp5','Recharge accroupie')]}
            scenes[key]=dict(label='R-01 · troisième personne · '+dict(bottom='dessous',side='latéral',top='dessus')[platform],bones=custom.names,parents=custom.parents,models=models,magazines=mags,hand=17,index=[],clips=clips,
                author_chest=globals_of(sequence_frames(custom,'ref_aim_mp5')[0],custom.parents)[11].T.flatten().tolist(),
                gaits={k:clip(custom,n,label) for k,n,label in [('walk','walk','Marche'),('run','run','Course'),('crouch','crawl','Déplacement accroupi')]},author=authored['recipe'],
                note='Arme modulaire réelle, bras ajustés, jambes et torse conservés. Recharge adaptée depuis CS avec chargeur mobile. Régler la tenue, exporter la recette JSON puis la déposer sur « Atelier - Animations.cmd » pour compiler cet essai. Recharges raccordées dans le runtime de test. Animations de déplacement de base conservées.')
    from inspector_deaths import export_deaths
    deaths, death_record = export_deaths(e, scenes, clip)
    data = dict(deaths=deaths, scenes=scenes, models=e.models, textures=e.textures,
        themes=json.loads((FP/'first-person.json').read_text())['themes'])
    path = ROOT/'build/animation-inspector.html'
    path.parent.mkdir(exist_ok=True)
    template = (ROOT/'animation_inspector.template.html').read_text(encoding='utf-8-sig')
    template = template.replace('__DEATH_SCRIPT__', (ROOT/'animation_inspector_deaths.js').read_text(encoding='utf-8')+'\n'+(ROOT/'animation_inspector_emissions.js').read_text(encoding='utf-8'))
    path.write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'),ensure_ascii=False)),encoding='utf-8')
    (OUT/'deaths.json').write_text(json.dumps(death_record,indent=2,ensure_ascii=False),encoding='utf-8')
    record = dict(page=str(path),donor=str(source.path),donor_sha256=hashlib.sha256(source.data).hexdigest(),target=str(rig.path),target_bones=len(rig.names),
        target_sequences=len(rig.sequences),current_reload_sequences=[n for n in rig.sequences if 'reload' in n],motions=motions,
        limits=['CS code studied, not copied; original model motions only','historical donor comparison does not implement a moving magazine; custom R-01 scenes do','FP reload motion retimed to match the existing 1.5s gameplay delay; foregrip variants only in first person'])
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    save_cache()
    print(path)
    print('Scenes:',len(scenes),'Models:',len(e.models),'Textures:',len(e.textures),'Bytes:',path.stat().st_size)
    return data


if __name__=='__main__':
    import argparse,shutil
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,help='Compile a recipe exported by the workshop')
    parser.add_argument('--cached',action='store_true',help='Reuse the offline page while its game assets are unchanged')
    parser.add_argument('--rebuild',action='store_true',help='Recompile the six FP carriers and the isolated CS preview')
    args=parser.parse_args()
    if args.rebuild:
        baseline=ROOT/'build/animation-workshop/baseline'
        baseline.mkdir(parents=True,exist_ok=True)
        for suffix in ('','_side','_top'):
            name=f'r01_rig{suffix}.mdl'
            if (FP/name).exists() and not (baseline/name).exists():shutil.copy2(FP/name,baseline/name)
        from build_reference_weapon import prepare_rig
        from build_reference_platforms import build_rigs
        from build_third_person_preview import build
        prepare_rig();build_rigs(FP);build()
        from build_foregrip import build as build_foregrip
        build_foregrip(FP)
        from third_person import build as build_custom,RECIPE
        build_custom(args.recipe or RECIPE,ensure=True)
    if not args.cached or args.rebuild or not use_cached_page():
        export()


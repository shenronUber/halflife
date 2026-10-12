"""Fixed R1 finishes, bespoke compiled modules and player-data preservation."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r01_finish_policy import policy,curated_catalog
from build_fitted_modules import INTRINSIC,WORKSHOP
from studio_assets import Studio
from build_r01_finish import is_current as fitted_current

def run():
    specs=policy()['models'];manifest=json.loads((ROOT/'generated/r01/manifest.json').read_text())
    assert set(specs)=={r['id'] for r in manifest['pieces']}
    data=(ROOT/'data/equipment.txt').read_bytes();assert curated_catalog(data)==(data,b'')
    rows=[r.split('|') for r in data.decode('ascii').splitlines() if r and not r.startswith(('#','limits|'))]
    styles={s['id']:s['skin'] for s in manifest['styles']}
    for ident,spec in specs.items():
        selected=[r[16].replace('_','-') for r in rows if len(r)==17 and r[15]==ident]
        assert sorted(selected)==sorted(spec['styles']) and 1<=len(selected)<=2
        model=Studio(ROOT/'generated/r01'/(ident+'.mdl'))
        for style in selected:assert styles[style]<model.numskinfamilies
        if spec['intrinsic']:
            assert (model.numskinfamilies,len(model.textures))==((14,2) if fitted_current(model.path) else (1,1))
    assert specs['r01_power_a']['styles']==['original']
    approved=json.loads((WORKSHOP/'manifest.json').read_text())
    assert len(approved['assets'])==len(INTRINSIC)==7
    atlas_hashes=set();sections=0
    for asset in approved['assets']:
        ident=asset['id'];path=ROOT/'generated/r01'/(ident+'.mdl');model=Studio(path)
        assert hashlib.sha256(model.data).hexdigest()==asset['compiled_sha256']
        assert model.names==['module_root'] and np.allclose(model.bind[0],np.eye(4))
        points=np.unique(np.array([v['p'] for _,tri in model.mesh() for v in tri]),axis=0)
        assert len(points)<=2048 and asset['uv_audit']['overlap_samples']==0
        for section in asset['axial_sections']:
            points_at_y=points[abs(points[:,1]-section['y'])<3e-6]
            radii=np.linalg.norm(points_at_y[:,[0,2]]-[0,1.3],axis=1)
            ring=points_at_y[abs(radii-section['radius'])<3e-6]
            assert len(ring)>=8
            assert np.linalg.norm(ring.mean(0)[[0,2]]-[0,1.3])<3e-6
            sections+=1
        atlas_hashes.add(asset['atlas_sha256'])
        live=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'/path.name
        if live.exists():assert path.read_bytes()==live.read_bytes()
    assert len(atlas_hashes)==7
    pool=json.loads((ROOT/'data/lootpool.json').read_text());index={r[1]:i for i,r in enumerate(rows,1)}
    assert all(index[e['id']]==e['equipment_index'] for e in pool['entries'])
    assert len(pool['entries'])==len({e['id'] for e in pool['entries']})==len({e['name'] for e in pool['entries']})
    assert sum(e['id'].startswith('r01_') for e in pool['entries'])==sum(len(s['styles']) for s in specs.values())
    backup=WORKSHOP/'integration-backup/vector-fields/data/lootpool.json'
    if backup.exists():
        old=json.loads(backup.read_text());assert old['operator_sets']==pool['operator_sets']
        current={e['id']:e for e in pool['entries']}
        for e in old['entries']:
            if e['id'].startswith('r01_'):continue
            strip=lambda x:{k:v for k,v in x.items() if k!='equipment_index'}
            assert strip(e)==strip(current[e['id']])
    print('PASS fitted R1:',len(specs),'shapes;',sum(len(s['styles']) for s in specs.values()),'fixed finishes;',sections,'native concentric sections; player metadata preserved')
if __name__=='__main__':run()

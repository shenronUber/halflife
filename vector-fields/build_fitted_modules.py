"""Install seven authored static modules, independently of animated carriers."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WORKSHOP=ROOT/'weapon-workshop/fitted-2026-10-11'
SPECS={
 'barrel_e':dict(name='Canon Aigrette',family='Baseline',title='Aigrette',description='Tube acier droit, ailettes longitudinales, bois rouge et frettes.'),
 'barrel_f':dict(name='Canon Relique',family='Rogue',title='Relique',description='Fourreau d os, tendons et brides sur un tube mecanique apparent.'),
 'muzzle_e':dict(name='Silencieux Sourdine',family='Baseline',title='Sourdine',description='Silencieux long bleui, bagues moletees et nez a pans.'),
 'muzzle_f':dict(name='Silencieux Tresse',family='Fortress',title='Tresse',description='Gaine textile sable ajustee, brides et coutures sur noyau acier.'),
 'muzzle_g':dict(name='Silencieux Campanule',family='Engine',title='Campanule',description='Chambres etagees en laiton patine, cerclages et agrafes acier.'),
 'muzzle_h':dict(name='Silencieux Ossifie',family='Rogue',title='Ossifie',description='Fourreau d os irregulier, tendon et insert mecanique apparent.'),
 'muzzle_i':dict(name='Silencieux Etouffoir',family='Anomalous',title='Etouffoir',description='Carene ceramique facettee, joints graphite et nez metallique.'),
}
INTRINSIC={'r01_'+key:dict(spec,slot=key.split('_')[0],collection='module-'+spec['title'].lower()) for key,spec in SPECS.items()}

def inputs():return [Path(__file__),WORKSHOP/'manifest.json']+[WORKSHOP/key/'export'/('r01_'+key+'.mdl') for key in SPECS]
def base_rows():return ['|'.join([s['slot'],ident,'1',s['name'],s['family'],s['title'],'4','4','4','4','0','0',s['description']+' Atlas exclusif. Raccord coaxial R1.','0']) for ident,s in INTRINSIC.items()]
def inventory_row(row):
    r=row.split('|') if isinstance(row,str) else list(row);out=r[:14]+['',r[1],'original'];out[1]+='__original';return out
def collections():return [dict(id=s['collection'],key=k,name=s['title'],family=s['family'],item_suffix='',intrinsic_weapon_texture=True) for k,s in SPECS.items() for s in [INTRINSIC['r01_'+k]]]
def pool_entry(row,index):
    s=INTRINSIC[row[15]]
    return dict(id=row[1],name=row[3],family=row[4],collection=s['collection'],slot=s['slot'],status='authored',weight=1,equipment_id=row[1],equipment_index=index,weapon_style=0,intrinsic_texture=True,model='models/vf_r01/'+row[15]+'.mdl')
def append_catalog(data):
    ids={r.split('|')[1] for r in data.decode('ascii').splitlines() if r and not r.startswith(('#','limits|'))};add=[]
    for base in base_rows():
        for r in [base,'|'.join(inventory_row(base))]:
            if r.split('|')[1] not in ids:add.append(r)
    return data+(b'' if not add else ('\n# Fitted barrels and silencers: intrinsic atlases.\n'+'\n'.join(add)+'\n').encode('ascii'))
def apply_modules(folder,records=None):
    from studio_assets import Studio
    folder=Path(folder);report=json.loads((WORKSHOP/'manifest.json').read_text());assets={a['id']:a for a in report['assets']}
    byid={r['id']:r for r in (records or [])}
    for ident,s in INTRINSIC.items():
        key=ident[4:];src=WORKSHOP/key/'export'/(ident+'.mdl');dst=folder/src.name
        data=src.read_bytes();assert hashlib.sha256(data).hexdigest()==assets[ident]['compiled_sha256']
        if dst.exists():assert dst.read_bytes()==data,'Another module revision exists: '+str(dst)
        else:shutil.copy2(src,dst)
        model=Studio(dst);assert model.names==['module_root'] and model.numskinfamilies==1
        r=dict(id=ident,slot=s['slot'],slot_index=10 if s['slot']=='barrel' else 11,variant='efghi'.index(key[-1])+4,
               name=s['name'],triangles=len(model.mesh()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),skin_families=1,intrinsic_texture=True,geometry_revision='fitted-2026-10-11')
        if records is not None:
            if ident in byid:byid[ident].update(r)
            else:records.append(r)

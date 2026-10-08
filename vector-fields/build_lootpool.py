"""Register authored GIGN equipment, R1 parts and retained accessory placeholders."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GEAR={'head':('Masque',0),'torso':('Veste',1),'gloves':('Gants',2),'legs':('Pantalon',3),'boots':('Bottes',4)}
PROVISIONAL={'shoulders','belt','shield','special'}

def build():
    config=json.loads((ROOT/'data/gameplay-content.json').read_text())
    appearances={r.split('|')[1]:int(r.split('|')[0]) for r in (ROOT/'generated/visual_skins/skins.txt').read_text().splitlines() if r}
    target=ROOT/'data/equipment.txt'
    lines=[r for r in target.read_text().splitlines() if '|gign_' not in r and not r.startswith('# GIGN gameplay')]
    for i,line in enumerate(lines):
        fields=line.split('|')
        if len(fields)>=14 and fields[1].startswith('r01_'):
            pair=config['weapon_families'][fields[0]]
            fields[4]=pair[1 if fields[1].endswith('_b') else 0]
            lines[i]='|'.join(fields)
    lines.append('# GIGN gameplay: named equipment / gameplay family / cosmetic collection / fitted appearance key.')
    for collection in config['collections']:
        family=collection['family'];f=config['families'].index(family)
        for slot,(name,zone) in GEAR.items():
            key='persona_'+collection['key'];assert key in appearances,key
            fields=[slot,'gign_'+slot+'_'+collection['key'],'1',name+' '+collection['suffix'],family,collection['name'],'0','0','0','0',str(4+f),str(3+f),name+' de la tenue '+collection['operator']+'.','0',key]
            assert len(fields[3])<48 and len(fields[1])<40 and len(fields[5])<32
            lines.append('|'.join(fields))
    text='\n'.join(lines)+'\n';target.write_text(text,encoding='ascii')
    records=[r.split('|')for r in lines if r and not r.startswith('#') and not r.startswith('limits|')]
    assert len(records)<255
    entries=[];sets=[]
    styles=json.loads((ROOT/'generated/r01/manifest.json').read_text())['styles']
    collections={c['id']:c for c in config['collections']}
    (ROOT/'data/r01_styles.txt').write_text(''.join(f"{st['skin']}|{st['id'].replace('-', '_')}|{collections[st['id']]['name']}|0|r01|{st['skin']}\n" for st in styles),encoding='ascii')
    for index,r in enumerate(records,1):
        slot,key,tier,name,family,collection=r[:6]
        if key.startswith('gign_'):
            theme=next(c for c in config['collections']if r[14]=='persona_'+c['key'])
            entries.append(dict(id=key,name=name,family=family,collection=theme['id'],slot=slot,status='authored',weight=1,equipment_index=index,appearance_key=r[14],appearance_index=appearances[r[14]],model='models/vf_skins/persona_scout.mdl',zone=GEAR[slot][1]))
        elif key.startswith('r01_'):
            for style in styles:
                c=collections[style['id']]
                entries.append(dict(id=key+'__'+style['id'],name=name+' / '+c['name'],family=family,collection=c['id'],slot=slot,status='authored',weight=1,equipment_id=key,equipment_index=index,weapon_style=style['skin'],model='models/vf_r01/'+key+'.mdl'))
        elif slot in PROVISIONAL:
            entries.append(dict(id=key,name=name,family=family,collection=None,slot=slot,status='placeholder',weight=1,equipment_index=index,model='models/vf_equipment/eq_'+slot+'.mdl'))
    for c in config['collections']:
        sets.append(dict(id='operator_'+c['id'],name=c['operator'],family=c['family'],collection=c['id'],items=['gign_'+s+'_'+c['key']for s in GEAR]))
    pool=dict(schema=1,families=config['families'],collections=config['collections'],operator_base_model='models/vf_skins/persona_scout.mdl',operator_rig='models/vf_skins/persona_rig.mdl',weapon_platforms=['r01_rig','r01_rig_side','r01_rig_top'],entries=entries,operator_sets=sets,limits=['Catalog registration; world drops and inventory acquisition are not implemented yet.','Accessory geometry remains provisional for shoulders, belt, shield and special.','Cosmetic collections do not modify gameplay families or weapon statistics.'])
    assert len({x['id']for x in entries})==len(entries)
    (ROOT/'data/lootpool.json').write_text(json.dumps(pool,indent=2)+'\n')
    print('Lootpool:',len(entries),'entries;',len(sets),'operator sets;',len(records),'equipment objects')
    return pool
if __name__=='__main__':build()

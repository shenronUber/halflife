"""Validate the shared model contract against the actual compiled assets/catalog."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from model_contract import load,generate
from studio_assets import Studio


def run():
    data=load();generate(check=True)
    manifest=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))
    for slot,field in [('receiver','receivers'),('underbarrel','underbarrels')]:
        shapes={p['id'] for p in manifest['pieces'] if p['slot']==slot}
        assert shapes==set(data[field]),(slot,'missing or unused model traits',shapes^set(data[field]))
    checked=0
    for platform in data['platforms']:
        for view in ('first_person','foregrip','third_person'):
            name=Path(platform[view]).name
            folder='third-person' if view=='third_person' else 'r01'
            carrier=Studio(ROOT/'generated'/folder/name)
            sockets=data['sockets']['third_person' if view=='third_person' else 'first_person']
            assert all(socket in carrier.names for socket in sockets.values()),(name,sockets)
            assert len(carrier.sequences)==(data['persona_sequences']+4 if view=='third_person' else 9)
            checked+=1
    assert manifest['socket']==data['sockets']['first_person']['weapon']
    assert manifest['animated_sockets']=={k:data['sockets']['first_person'][k] for k in ('feed','chamber')}
    counts={key:0 for field in ('receivers','underbarrels') for key in data[field]}
    for line in (ROOT/'data/equipment.txt').read_text(encoding='ascii').splitlines():
        fields=line.split('|')
        if len(fields)==17 and fields[15] in counts:counts[fields[15]]+=1
    assert all(count==manifest['skin_families'] for count in counts.values()),counts
    print('PASS model contract:',checked,'compiled carriers,',len(counts),'explicit traits,',sum(counts.values()),'immutable variants')


if __name__=='__main__':run()

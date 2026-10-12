"""Explicit reviewed finishes. A missing model is a build error, never all styles."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PATH=ROOT/'data/r01-fitted-finishes.json'

def policy():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    assert data['schema']==1
    for ident,spec in data['models'].items():
        assert ident.startswith('r01_') and 1<=len(spec['styles'])<=2
        assert len(set(spec['styles']))==len(spec['styles'])
    return data

def allowed(ident):
    return policy()['models'][ident]['styles']

def curated_catalog(data):
    """Preserve all non-weapon lines and retained IDs; remove only unfit R1 finishes.

    GoldSrc saves equipment by stable ID, so surviving selections remain intact
    when the wire indices change. Removed finishes fall back in their own slot
    using the existing engine migration. Full historical rows are archived.
    """
    specs=policy()['models'];lines=[];removed=[]
    for line in data.decode('ascii').splitlines(keepends=True):
        fields=line.rstrip('\r\n').split('|')
        if len(fields)==17 and fields[1].startswith('r01_'):
            if fields[16].replace('_','-') not in specs[fields[15]]['styles']:
                removed.append(line);continue
        lines.append(line)
    return ''.join(lines).encode('ascii'),''.join(removed).encode('ascii')

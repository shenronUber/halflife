"""Keep the small public contract table in sync with the actual C++ declarations."""
import argparse
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DOCUMENTS=[ROOT/'engine/README.md',ROOT/'docs/ARCHITECTURE.md']
START='<!-- generated-contract:start -->';END='<!-- generated-contract:end -->'


def facts():
    api=(ROOT.parent/'game_shared/vf_engine_api.h').read_text()
    loadout=(ROOT.parent/'game_shared/vf_loadout.h').read_text()
    renderer=(ROOT/'engine/gl_vf.inc').read_text()
    define=lambda key:int(re.search(r'#define\s+'+key+r'\s+(\d+)',api)[1])
    enum=lambda key:int(re.search(r'\b'+key+r'\s*=\s*(\d+)',loadout)[1])
    return [('API renderer',define('VF_ENGINE_API_VERSION')),('Pièces par assemblage',define('VF_MAX_PARTS')),
            ('Assemblages actifs',define('VF_MAX_ASSEMBLIES')),('Modèles en cache',int(re.search(r'vf_models\[(\d+)\]',renderer)[1])),
            ('Protocole équipement',enum('Protocol')),('VFBuild (octets)',enum('BuildMessageSize')),
            ('VFState (octets)',enum('StateMessageSize')),('Capacité catalogue',enum('MaxItems'))]


def block():
    return START+'\n\n| Contrat courant | Valeur |\n| --- | ---: |\n'+''.join(f'| {key} | {value} |\n' for key,value in facts())+'\n'+END


def update(text):
    pattern=re.escape(START)+r'.*?'+re.escape(END)
    if START in text:return re.sub(pattern,lambda _:block(),text,flags=re.S)
    first,rest=text.split('\n',1)
    return first+'\n\n'+block()+'\n'+rest


def generate(check=False):
    for path in DOCUMENTS:
        old=path.read_text(encoding='utf-8-sig');new=update(old)
        if check and old!=new:raise ValueError(f'Stale contract documentation: {path}; run contract_documentation.py')
        if not check and old!=new:path.write_text(new,encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');generate(p.parse_args().check)

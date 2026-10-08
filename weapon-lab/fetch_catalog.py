"""Cache public GameBanana metadata and selected archives for local research."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IDS = [636816, 640447, 640445, 682919, 660140, 641014, 618001, 615797, 536775, 706926]

def fetch(item_id):
    target = ROOT / 'catalog' / f'{item_id}-raw.json'
    target.parent.mkdir(exist_ok=True)
    if not target.exists():
        req = urllib.request.Request(f'https://gamebanana.com/apiv11/Mod/{item_id}/ProfilePage',
                                     headers={'User-Agent':'VectorFields-local-asset-study/0.1'})
        with urllib.request.urlopen(req, timeout=40) as response:
            target.write_bytes(response.read())
    record = json.loads(target.read_bytes())
    return {'id':item_id, 'name':record['_sName'], 'url':record['_sProfileUrl'],
            'description_html':record.get('_sText',''), 'license':record.get('_sLicense'),
            'license_checklist':record.get('_aLicenseChecklist'),
            'credits':record.get('_aCredits'), 'files':record.get('_aFiles',[])}

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, IDS))
    (ROOT/'catalog'/'selection.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    for r in records:
        print(json.dumps({k:r[k] for k in ['id','name','license','license_checklist']},ensure_ascii=True))
        print(json.dumps([{'id':f['_idRow'],'file':f['_sFile'],'bytes':f['_nFilesize'],
                          'archived':f.get('_bIsArchived',False)} for f in r['files']]))

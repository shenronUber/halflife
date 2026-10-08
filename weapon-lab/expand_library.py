"""Expand the local donor library; keep public provenance and verify each archive."""
import concurrent.futures,json,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from download_assets import download
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'catalog'/'expansion'
IDS=[394799,567446,179738,179724,498695,179784,179772,391277,179785,179782,179674,179733,179775,179773,618463,224147,227148,227227,410921,355401,231336,224405,236099,236019,210349,210399,217436,635773,210269,210406]
def run(i):
 d=json.loads((OUT/f'{i}-raw.json').read_bytes())
 record={'id':i,'name':d['_sName'],'url':d['_sProfileUrl'],'game':d['_aGame']['_sName'],
 'likes':d.get('_nLikeCount'), 'downloads':d.get('_nDownloadCount'),
 'license':d.get('_sLicense'),'license_checklist':d.get('_aLicenseChecklist'),'credits':d.get('_aCredits'),
 'description_html':d.get('_sText',''),'files':d.get('_aFiles',[]),'retrieved':'2026-10-08'}
 try:record['download']=download(record)
 except Exception as e:record['error']=str(e);print(f'{i}: ERROR {e}',flush=True)
 (OUT/f'{i}-record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
 return record
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(run,IDS))
 (OUT/'collection.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 print(json.dumps({'packs':len(records),'downloaded':sum('download'in r for r in records),'bytes':sum(r.get('download',{}).get('bytes',0) for r in records)}))

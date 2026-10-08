"""Build a self-contained catalogue (no remote JavaScript or CDN)."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'catalog/expansion/inventory.json').read_bytes());packs=[]
for path in sorted((ROOT/'catalog/ww2').glob('*-record.json')):
 r=json.loads(path.read_bytes());raw=json.loads(path.with_name(str(r['id'])+'-raw.json').read_bytes());rows.append(dict(id=r['id'],name=r['name'],game=raw['_aGame']['_sName'],likes=raw.get('_nLikeCount',0),downloads=raw.get('_nDownloadCount',0),url=raw['_sProfileUrl'],formats=['10'],inventory=[],credits=raw.get('_aCredits'),license=raw.get('_sLicense'),download=r['download']))
for r in rows:
 tags=' '.join(t for m in r['inventory']for t in m.get('textures',[]))
 credits='\n'.join(a.get('_sName','?')+' — '+a.get('_sRole','')for g in r.get('credits')or[] for a in g.get('_aAuthors',[]))
 preview='catalog/expansion/previews/'+str(r['id'])+'.png'
 fmt='gold' if '10'in r['formats'] else 'source'
 packs.append({'id':r['id'],'name':r['name'],'game':r['game'],'likes':r['likes']or 0,'downloads':r['downloads']or 0,'mb':round(r['download']['bytes']/1e6,1),'url':r['url'],'format':fmt,'preview':preview if (ROOT/preview).exists() else None,'tags':tags,'note':('Intégré dans Arsenal / GameBanana ou WW2. Filtre En main pour les modèles équipables.' if fmt=='gold' else 'MDL Source archivé : conversion à réaliser, sauf le premier M4 RIS déjà intégré.'),'license':html.unescape(re.sub('<[^>]+>','',r.get('license')or'')),'credits':credits})
data={'packs':packs,'parts':json.loads((ROOT/'generated/accessories/viewer-data.json').read_bytes()),'reports':json.loads((ROOT/'generated/accessories/manifest.json').read_bytes())}
template=(ROOT/'catalogue.template.html').read_text(encoding='utf-8');out=template.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
(ROOT/'catalogue.html').write_text(out,encoding='utf-8');print('Catalogue:',len(out),'characters')

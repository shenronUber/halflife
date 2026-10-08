"""Validate the fitted GIGN topology, shared texture families and native workshop."""
import collections,hashlib,json,re,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_personas import ROOT,ASSETS,OUT,tailored_mesh,fitted_skeleton,donor
from studio_assets import Studio,transform
from play_personas import MOD,ENGINE,command,deploy
from library_engine_test import click

def digest(mesh):
 h=hashlib.sha256()
 for _,tri in mesh:
  for v in tri:
   for key in ('p','n','uv'):h.update(v[key].tobytes())
   h.update(bytes([v['b']]))
 return h.hexdigest()

def geometry():
 config=json.loads((ASSETS/'personas.json').read_text());zones,meta=tailored_mesh(config)
 studio=Studio(OUT/'persona_scout.mdl');rig=Studio(OUT/'persona_rig.mdl');legacy=Studio(ROOT/'generated/modular/vf_operator.mdl')
 assert meta['source_triangles']==sum(map(len,zones))==740 and meta['collars']==0 and meta['added_triangles']==0
 assert studio.numskinfamilies==1+len(config['themes']) and rig.sequences==legacy.sequences and len(rig.sequences)==77
 for name,bind in zip(studio.names,studio.bind):assert np.allclose(bind,rig.bind[rig.names.index(name)],atol=1e-6)
 source=Studio(donor(config)['path']);source_faces=source.mesh()
 assert np.allclose(np.array([v['p']for _,t in source_faces for v in t]).min(0),np.array([v['p']for zone in zones for _,t in zone for v in t]).min(0))
 edges=collections.defaultdict(set);vertices=collections.defaultdict(list)
 for z,mesh in enumerate(zones):
  for _,tri in mesh:
   for v in tri:vertices[tuple(np.round(v['p'],5))].append((z,v))
   for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted(tuple(np.round(v['p'],5))for v in (a,b)))].add(z)
 interfaces=collections.Counter(tuple(sorted(zs))for zs in edges.values()if len(zs)>1)
 assert set(interfaces)=={(0,1),(1,2),(1,3),(3,4)}
 shared=[rows for rows in vertices.values()if len({z for z,v in rows})>1]
 for rows in shared:
  assert len({v['b']for z,v in rows})==1
  assert np.ptp([v['p']for z,v in rows],axis=0).max()<1e-7
 compiled=[studio.mesh({i:int(i==z)for i in range(5)})for z in range(5)]
 assert [len(m)for m in compiled]==meta['zone_triangles']
 for z in range(5):
  expected=digest(compiled[z])
  for skin in range(studio.numskinfamilies):assert digest(studio.mesh({i:int(i==z)for i in range(5)},skin=skin))==expected
 # Match every shared source vertex on both compiled sides, then pose the
 # compiled coordinates with real idle/run/crouch/shoot/jump animation frames.
 joints=[]
 for rows in shared:
  z0,v0=rows[0];name=__import__('build_skins').NODES[v0['b']];bone=studio.names.index(name);matches=[]
  for z in sorted({z for z,v in rows}):
   options=[v for _,t in compiled[z]for v in t if v['b']==bone]
   v=min(options,key=lambda v:np.linalg.norm(v['p']-v0['p']))
   assert np.linalg.norm(v['p']-v0['p'])<.018 # StudioMDL truncates each local axis to 0.01.
   matches.append(v)
  joints.append((bone,matches))
 from build_modular import skeleton
 _,parents,_=skeleton(OUT/'persona_anchors.smd');source_names=__import__('build_skins').NODES
 max_gap=0;poses=0
 for animation in ('look_idle','run2','walk','crouch_idle','jump','2handshoot'):
  frames=[];current=None
  for line in (OUT/(animation+'.smd')).read_text().splitlines():
   if line.startswith('time '):current={};frames.append(current)
   elif current is not None:
    values=line.split()
    if len(values)==7:current[int(values[0])]=transform(list(map(float,values[1:])))
  for frame in (frames[0],frames[len(frames)//2],frames[-1]):
   posed={}
   for b,local in frame.items():posed[b]=posed[parents[b]]@local if parents[b]>=0 else local
   for bone,points in joints:
    sourcebone=next(b for b,name in source_names.items()if name==studio.names[bone])
    skinning=posed[sourcebone]@np.linalg.inv(studio.bind[bone])
    positions=np.array([(skinning@np.r_[v['p'],1])[:3]for v in points])
    max_gap=max(max_gap,float(np.ptp(positions,axis=0).max()))
   poses+=1
 assert max_gap<.001,max_gap
 return dict(triangles=740,collars=0,skin_zone_checks=5*studio.numskinfamilies,seam_edges={str(k):v for k,v in interfaces.items()},shared_boundary_vertices=len(shared),animation_samples=poses,max_compiled_seam_gap=max_gap,animations=77)

def run():
 manifest=deploy();checks=geometry();captures=[]
 def snap(name):
  name='persona_'+name;captures.append(name);return f'wait 20\nscreenshot scrshots/{name}.png\nwait 4\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\nvf_skins\nwait 35\nvf_skin_tab 0\nvf_skin_filter 7\nvf_animation_time 0\n'
 s+='vf_skin_all 157\n'+snap('legacy_gign')+f'vf_skin_all {manifest["base_entry"]}\n'+snap('fitted_gign')
 for t in manifest['themes']:
  s+=f'vf_skin_all {t["id"]}\nvf_skin_commit\nwait 20\nvf_animation_time 0\n'+snap(t['key']+'_front')
  s+='vf_rotate\n'*6+snap(t['key']+'_back')+'vf_rotate\n'*6
 # Actual pointer route: select the jungle card, apply it to all five zones.
 s+=click(1040,425)+click(160,539)+click(1160,690)+'wait 30\n'+snap('ui_jungle')
 assert manifest['themes'][3]['id']==179
 s+='vf_animation 0\nvf_animation_time 0\n'
 # One original body, independently chosen textures at all five fitted seams.
 ids=[181,177,178,179,180]
 for z,id in enumerate(ids):s+=f'vf_skin_set {z} {id}\n'
 s+='vf_skin_commit\nwait 25\n'+snap('mixed')
 s+='vf_skin_all 176\n'+click(970,690)+snap('cancel_restored')
 for z in range(5):
  s+=f'vf_skin_set {z} {ids[z]}\nvf_skin_isolate\n'+snap('zone_'+str(z))+'vf_skin_isolate\n'
 for seq,label in [(3,'run'),(7,'crouch'),(8,'jump'),(5,'shoot')]:
  for t in (0,.2):s+=f'vf_animation {seq}\nvf_animation_time {t}\n'+snap(f'{label}_{int(t*10)}')
 s+='vf_animation 0\nvf_animation_time 0\nvf_visual_bench personas\nwait 215\n'
 s+=click(1220,40)+'wait 20\ncmd vf_body_info\n+forward\nwait 12\n-forward\n+attack\nwait 15\n-attack\nwait 20\nsave vf_personas_test\nwait 40\nload vf_personas_test\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_skins\nwait 30\nvf_animation_time 0\n'+snap('restored')+'vf_engine_stats\nquit\n'
 cfg=MOD/'vf_personas_validation.cfg';cfg.write_text(s,encoding='ascii');started=time.time()
 p=subprocess.Popen(command(cfg.name,'vf-personas-validation.log'),cwd=ENGINE)
 try:p.wait(timeout=130)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0
 log=(ENGINE/'vf-personas-validation.log').read_text(errors='replace')
 for t in manifest['themes']:assert f'VFSkin client: result=0 ids='+','.join([str(t['id'])]*5)in log,t
 assert 'VFUI click: Appliquer aux 5 zones'in log
 assert 'VFSkin client: result=0 ids=179,179,179,179,179'in log
 after=log.split('Loading game from save/vf_personas_test.sav')[-1]
 assert 'VFState player=1 skins='+','.join(map(str,ids))+' weapon='in after
 assert 'VFState rejected'not in log and 'rejected=0'in log
 assert re.search(r'VFBench personas:.*loads=0\b',log)
 assert 'VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1'in log
 for name in captures:
  path=MOD/'scrshots'/(name+'.png');assert path.stat().st_mtime>=started
  assert Image.open(path).size==(1920,1080)
 def viewport(name):return Image.open(MOD/'scrshots'/('persona_'+name+'.png')).convert('RGB').crop((490,305,1220,800))
 assert ImageChops.difference(viewport('mixed'),viewport('cancel_restored')).getbbox()is None
 original=viewport('fitted_gign')
 for t in manifest['themes']:
  assert sum(max(px)>20 for px in ImageChops.difference(original,viewport(t['key']+'_front')).getdata())>5000
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
 board=Image.new('RGB',(1350,550*((len(manifest['themes'])+2)//3)),'#131c24');draw=ImageDraw.Draw(board)
 for i,t in enumerate(manifest['themes']):
  x=(i%3)*450;y=(i//3)*550
  im=viewport(t['key']+'_front').crop((240,15,485,490))
  board.paste(im,(x+102,y+65));draw.text((x+16,y+16),t['title'],font=font,fill='#e5f3ed')
 board.save(ROOT/'build/gign-personas-in-game.jpg',quality=95,subsampling=0)
 comparison=Image.new('RGB',(1350,565),'#131c24');draw=ImageDraw.Draw(comparison)
 for i,(key,label)in enumerate([('legacy_gign','Anciennes interfaces universelles'),('fitted_gign','Base GIGN ajustee'),('mixed','Cinq zones / cinq finitions')]):
  comparison.paste(viewport(key).crop((240,15,485,490)),(i*450+102,65));draw.text((i*450+14,16),label,font=font,fill='#e5f3ed')
 comparison.save(ROOT/'build/gign-fitted-comparison.jpg',quality=95,subsampling=0)
 report=dict(geometry=checks,captures=captures,checks=['all complete themes rendered from front and back','five isolated body zones on GIGN topology','UI applies a complete set; mixed styles, cancel and save/load work','run, crouch, jump and shooting poses rendered','original player collision hull retained','warm skin switching requires zero model loads'],limits=['original GIGN geometry remains the shared silhouette','surface materials are painted diffuse, not physical relief','other character families retain their legacy interfaces'])
 (ROOT/'build/personas-verification.json').write_text(json.dumps(report,indent=2))
 print('PASS GIGN personas:',len(captures),'native captures;',checks)
if __name__=='__main__':run()

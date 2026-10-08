"""Planar segmentation, shared sockets, closed caps and common animated rigs."""
import argparse,hashlib,json,re,shutil,struct,sys
from pathlib import Path
import numpy as np
import build_modular as base
from studio_assets import Studio,canonical
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/skins';OUT.mkdir(parents=True,exist_ok=True)
STEAM=Path('F:/SteamLibrary/steamapps/common/Half-Life')
HEADER,NODES,_=base.read_smd(ROOT/'generated/tfc-soldier/soldier_reference_2.smd')
_,_,BIND=base.skeleton(ROOT/'generated/tfc-soldier/soldier_reference_2.smd')
_,_,IDLE=base.skeleton(ROOT/'generated/tfc-soldier/look_idle.smd')
TARGET={canonical(n):b for b,n in NODES.items()}
POSE={b:IDLE[b]@np.linalg.inv(BIND[b]) for b in BIND}
ZONES=['head','torso','hands','legs','feet']

def vertex(p,n,uv,b):return dict(p=np.array(p),n=np.array(n),uv=np.array(uv),b=b)

def plane(name,center,normal,radii,bone,band_zone):
 normal=np.array(normal);normal=normal/np.linalg.norm(normal)
 u=np.cross(normal,[0,1,0] if abs(normal[1])<.95 else [0,0,1]);u/=np.linalg.norm(u);v=np.cross(normal,u)
 return dict(name=name,c=np.array(center),n=normal,u=u,v=v,r=np.array(radii),bone=bone,band_zone=band_zone)

PLANES=[plane('neck',[.23,-.6,63.5],[0,0,1],[2.35,2.4],TARGET['neck'],1),
        plane('waist',[.23,.37,41],[0,0,1],[6.0,4.15],TARGET['pelvis'],1)]
for side in ['l','r']:
 hand=BIND[TARGET[side+' hand']][:3,3];elbow=BIND[TARGET[side+' arm2']][:3,3]
 normal=hand-elbow;normal/=np.linalg.norm(normal)
 PLANES.append(plane(side+'_wrist',hand-normal*.3,normal,[1.3,1.1],TARGET[side+' hand'],1))
 foot=BIND[TARGET[side+' foot']][:3,3].copy();foot[2]=7.2
 PLANES.append(plane(side+'_ankle',foot,[0,0,-1],[1.4,1.6],TARGET[side+' foot'],3))
P={p['name']:p for p in PLANES}
for p in PLANES:p['width']=4.5 if p['name']=='neck' else 7.0 if p['name']=='waist' else 2.5

def clone(v):return {k:(x.copy() if isinstance(x,np.ndarray) else x) for k,x in v.items()}

def clip(poly,p,positive):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=float(np.dot(a['p']-p['c'],p['n']));db=float(np.dot(b['p']-p['c'],p['n']));ina=da>=-1e-6 if positive else da<=1e-6;inb=db>=-1e-6 if positive else db<=1e-6
  if ina:out.append(clone(a))
  if ina!=inb:
   t=da/(da-db);bone=(a['b'] if t<.5 else b['b']) if p.get('refine') else p['bone'];v=vertex(a['p']+(b['p']-a['p'])*t,a['n']+(b['n']-a['n'])*t,a['uv']+(b['uv']-a['uv'])*t,bone)
   v['p']-=p['n']*np.dot(v['p']-p['c'],p['n']);out.append(v)
 return out

def fan(material,poly):
 return [(material,[clone(poly[0]),clone(poly[i]),clone(poly[i+1])]) for i in range(1,len(poly)-1) if np.linalg.norm(np.cross(poly[i]['p']-poly[0]['p'],poly[i+1]['p']-poly[0]['p']))>1e-7]

def socket(poly,p):
 for v in poly:
  d=np.dot(v['p']-p['c'],p['n']);t=max(0.,1-abs(d)/p.get('width',2.5));t=t*t*t*(t*(t*6-15)+10)
  if t<=0:continue
  delta=v['p']-p['c'];a=np.dot(delta,p['u']);b=np.dot(delta,p['v']);angle=np.arctan2(b/p['r'][1],a/p['r'][0]);ring=p['u']*p['r'][0]*np.cos(angle)+p['v']*p['r'][1]*np.sin(angle)
  v['p']=(1-t)*v['p']+t*(p['c']+p['n']*d+ring)
  radial=p['u']*np.cos(angle)/p['r'][0]+p['v']*np.sin(angle)/p['r'][1];radial/=np.linalg.norm(radial)
  v['n']=(1-t)*v['n']+t*radial;v['n']/=max(1e-8,np.linalg.norm(v['n']))
  if abs(d)<1e-4:v['b']=p['bone']

def refine_band(poly,p):
 # Add cross sections before deforming: a long triangle must follow the
 # transition instead of spanning it with one hard diagonal.
 pieces=[poly]
 for fraction in [-1,-.66,-.33,.33,.66,1]:
  cut=dict(p,c=p['c']+p['n']*p['width']*fraction,refine=True)
  out=[]
  for part in pieces:
   distances=[np.dot(v['p']-cut['c'],cut['n']) for v in part]
   if min(distances)<-1e-5 and max(distances)>1e-5:
    out.extend([clip(part,cut,True),clip(part,cut,False)])
   else:out.append(part)
  pieces=out
 return pieces

def segments(poly,p):
 return [(a['p'].copy(),b['p'].copy()) for a,b in zip(poly,poly[1:]+poly[:1]) if abs(np.dot(a['p']-p['c'],p['n']))<1e-4 and abs(np.dot(b['p']-p['c'],p['n']))<1e-4 and np.linalg.norm(a['p']-b['p'])>1e-5]

def close_cap(edges,p,positive,material,uv):
 # Every boundary edge receives a closing triangle. This also handles separate
 # loops (coat shells, double-sided cuffs) without dropping their boundaries.
 norm=-p['n'] if positive else p['n'];out=[]
 for a,b in edges:
  center=p['c'];v=[vertex(center,norm,uv,p['bone']),vertex(a,norm,uv,p['bone']),vertex(b,norm,uv,p['bone'])]
  if np.dot(np.cross(a-center,b-center),norm)<0:v=[v[0],v[2],v[1]]
  out+=fan(material,v)
 return out

def band(p,material,uv):
 out=[];n=32
 for i in range(n):
  vertices=[]
  for j,d in [(i,-.55),(i+1,-.55),(i+1,.55),(i,.55)]:
   a=j*2*np.pi/n;radial=p['u']*np.cos(a)+p['v']*np.sin(a)
   pos=p['c']+p['u']*(p['r'][0]+.14)*np.cos(a)+p['v']*(p['r'][1]+.14)*np.sin(a)+p['n']*d
   vertices.append(vertex(pos,radial,uv,p['bone']))
  if np.dot(np.cross(vertices[1]['p']-vertices[0]['p'],vertices[2]['p']-vertices[0]['p']),vertices[0]['n'])<0:vertices.reverse()
  out+=fan(material,vertices)
 return out

def segment(triangles,materials,studio,conform=True):
 zones=[[] for _ in ZONES];edges={};caps=0
 def adapt(poly,p):
  if conform:socket(poly,p)
 # A constant UV selects a dark neutral texel from an existing source texture.
 colors=np.frombuffer(studio.textures[0][4],np.uint8).reshape(256,3).astype(float)
 used=np.unique(np.frombuffer(studio.textures[0][3],np.uint8))
 idx=int(used[np.argmin(np.linalg.norm(colors[used]-np.array([40,43,45]),axis=1))])
 pixels=studio.textures[0][3];where=pixels.find(bytes([idx]));w=studio.textures[0][1]
 uv=np.array([((max(0,where)%w)+.5)/w,1-((max(0,where)//w)+.5)/studio.textures[0][2]])
 def store(zone,mat,poly,p=None,pos=True):
  if len(poly)<3:return
  if p:
   adapt(poly,p);edges.setdefault((zone,p['name'],pos),[]).extend(segments(poly,p))
  zones[zone]+=fan(mat,poly)
 refined=[]
 for mat,poly in triangles:
  if not conform:refined.append((mat,poly));continue
  bones=[canonical(NODES[v['b']]) for v in poly]
  if any('arm' in b or 'hand' in b or 'finger' in b for b in bones):refined.append((mat,poly));continue
  pieces=refine_band(poly,P['neck'])
  pieces=[part for piece in pieces for part in refine_band(piece,P['waist'])]
  refined.extend((mat,piece) for piece in pieces)
 for mat,poly in refined:
  mat=materials[mat];bones=[canonical(NODES[v['b']]) for v in poly]
  side='l' if any(x.startswith('l ') and ('arm' in x or 'hand' in x or 'finger' in x) for x in bones) else 'r' if any(x.startswith('r ') and ('arm' in x or 'hand' in x or 'finger' in x) for x in bones) else None
  if side:
   p=P[side+'_wrist'];store(2,mat,clip(poly,p,True),p,True);store(1,mat,clip(poly,p,False),p,False);continue
  neck=P['neck'];head=clip(poly,neck,True);rest=clip(poly,neck,False)
  store(0,mat,head,neck,True)
  if not rest:continue
  # Preserve the neck boundary in the torso before the independent waist cut.
  adapt(rest,neck);edges.setdefault((1,'neck',False),[]).extend(segments(rest,neck))
  waist=P['waist'];store(1,mat,clip(rest,waist,True),waist,True);legs=clip(rest,waist,False)
  if not legs:continue
  adapt(legs,waist);edges.setdefault((3,'waist',False),[]).extend(segments(legs,waist))
  side='l' if np.mean([v['p'][0] for v in legs])>.2 else 'r';ankle=P[side+'_ankle']
  store(4,mat,clip(legs,ankle,True),ankle,True);store(3,mat,clip(legs,ankle,False),ankle,False)
 for (zone,key,pos),e in edges.items():
  cap=close_cap(e,P[key],pos,materials[0],uv);zones[zone]+=cap;caps+=len(cap)
 if conform:
  for p in PLANES:zones[p['band_zone']]+=band(p,materials[0],uv)
 return zones,{'caps':caps,'boundary_segments':sum(len(e) for e in edges.values()),'planes':6,'collars':6 if conform else 0}

def smd_tri(triangles):
 return [(m,[str(v['b'])+' '+' '.join(f'{x:.6f}' for x in [*v['p'],*v['n'],*v['uv']]) for v in verts]) for m,verts in triangles]

def candidates():
 entries=[];skipped=[];seen={}
 excluded={'chumtoad','bigrat','bullsquid','houndeye','icky','nihilanth','controller','construction','agrunt','garg','baby_strooper','v_squeak','w_squeak','v_hgun'}
 for game,label in [('tfc','TFC'),('valve','HL'),('gearbox','OF'),('bshift','BS')]:
  folder=STEAM/game/'models'
  for path in sorted(folder.rglob('*.mdl')):
   if game=='tfc' and 'player' not in path.relative_to(folder).parts:continue
   if path.stem.lower() in excluded or path.stem.lower().startswith(('v_','p_','w_')):continue
   try:s=Studio(path)
   except (AssertionError,struct.error,IndexError,FileNotFoundError,ValueError):continue
   names={canonical(n) for n in s.names}
   if not {'head','l hand','r hand','l foot','r foot','pelvis'}.issubset(names) or not s.parts or not s.textures:continue
   digest=hashlib.sha256(path.read_bytes()).hexdigest()
   if digest in seen:seen[digest]['also_in'].append(str(path));continue
   name=path.stem;choice={};entry=dict(path=str(path),game=label,name=name,choices=choice,sha256=digest,also_in=[])
   entries.append(entry);seen[digest]=entry
   # Make alternate native heads accessible too, without multiplying every
   # body/weapon combination in the source MDL.
   for j,(part,n,_) in enumerate(s.parts):
    if 'head' in part.lower():
     for v in range(1,n):
      choices={j:v};off=s.parts[j][2]+112*v;nv,vi=struct.unpack_from('<ii',s.data,off+80)
      bones={canonical(s.names[b]) for b in s.data[vi:vi+nv]}
      # Opposing Force's G-Man stores an alternate whole body in "heads".
      # Do not superpose that body on the default one.
      if {'l foot','r foot','head','pelvis'}.issubset(bones):choices.update({k:-1 for k in range(len(s.parts)) if k!=j})
      entries.append(dict(entry,name=name+f' head {v+1}',choices=choices,also_in=[]))
  if not folder.exists():skipped.append({'game':label,'reason':'not installed'})
 entries.sort(key=lambda e: ({"soldier2":0,"hvyweapon2":1,"scout2":2}.get(Path(e["path"]).stem,3) if e["game"]=="TFC" else 4))
 return entries,skipped

def build_character(entry,index,conform=True,key=None,export=True):
 s=Studio(entry['path']);mapping={}
 for b,name in enumerate(s.names):
  a=b
  while canonical(s.names[a]) not in TARGET and s.parents[a]>=0:a=s.parents[a]
  mapping[b]=(a,TARGET.get(canonical(s.names[a]),0))
 triangles=s.mesh(entry['choices'],BIND,mapping)
 # Weld coincident donor positions after retargeting, including UV seams.
 buckets={}
 for _,poly in triangles:
  for v in poly:buckets.setdefault(tuple(np.round(v['source'],4)),[]).append(v)
 for verts in buckets.values():
  avg=np.mean([v['p'] for v in verts],axis=0)
  for v in verts:v['p']=avg.copy()
 materials=s.write_textures(OUT,f's{index}')
 zones,stats=segment(triangles,materials,s,conform)
 if any(len(z)<4 for z in zones):raise ValueError('incomplete body zones')
 name=key or f'skin_{index:03}'
 for i,z in enumerate(zones):base.write_smd(OUT/f'{name}_{i}.smd',HEADER,smd_tri(z))
 qc=f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n'
 for i in range(5):qc+=f'$bodygroup {ZONES[i]}\n{{\n blank\n studio "{name}_{i}"\n}}\n'
 qc+='$sequence idle "look_idle" fps 10 loop\n$sequence walk "walk" fps 20 loop\n'
 (OUT/(name+'.qc')).write_text(qc)
 mdl=base.compile_model(OUT/(name+'.qc'))
 old=base.OUT;base.OUT=OUT
 preview=base.export_preview(name,[(i,0,smd_tri(z)) for i,z in enumerate(zones)],POSE) if export else None
 base.OUT=old
 return dict(entry,id=index,key=name,triangles=[len(z) for z in zones],**stats,preview=preview,sequences=s.sequences)

def build_weapons():
 records=[]
 extra={'conc_grenade','emp_grenade','mirv_grenade','napalm','ngrenade','spy_grenade','pipebomb','detpack','caltrop','nail','bomblet','sentry1','sentry2','sentry3','dispenser','teleporter'}
 for path in sorted((STEAM/'tfc/models').glob('*.mdl')):
  if not path.stem.startswith(('p_','v_')) and path.stem not in extra:continue
  s=Studio(path);index=len(records);name=f'arsenal_{index:03}';materials=s.write_textures(OUT,name);triangles=s.mesh()
  if not triangles:continue
  # Center the source preview and align its longest horizontal axis with Y.
  points=np.array([v['p'] for _,t in triangles for v in t]);center=(points.min(axis=0)+points.max(axis=0))*.5;span=np.ptp(points,axis=0)
  for _,t in triangles:
   for v in t:
    # Strip vertices can share source arrays. Never translate them in place:
    # a vertex reused in three faces would otherwise move three times.
    v['p']=v['p']-center
    if span[0]>span[1]:v['p']=v['p'][[1,0,2]];v['n']=v['n'][[1,0,2]]
  old=base.OUT;base.OUT=OUT
  preview=base.export_preview(name,[(-1,0,smd_tri([(materials[m],t) for m,t in triangles]))])
  base.OUT=old
  records.append(dict(id=index,key=name,name=path.stem,source=str(path),type='Vue en main' if path.stem.startswith('v_') else 'Modele externe' if path.stem.startswith('p_') else 'Equipement / projectile',animations=len(s.sequences),sequences=s.sequences,preview=preview))
 return records

def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);parser.add_argument('--weapons-only',action='store_true');parser.add_argument('--output',type=Path);args=parser.parse_args()
 if args.output:OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
 for name in ['look_idle','walk']:
  shutil.copy2(ROOT/'generated/tfc-soldier'/(name+'.smd'),OUT/(name+'.smd'))
 entries,skipped=candidates();records=[]
 print('Humanoid source variants:',len(entries),flush=True)
 if not args.weapons_only:
  for entry in entries[:args.limit]:
   try:
    record=build_character(entry,len(records));records.append(record);print('Built',record['id'],record['game'],record['name'],record['triangles'],flush=True)
   except (ValueError,RuntimeError,AssertionError,KeyError) as e:
    skipped.append(dict(source=entry['path'],name=entry['name'],reason=str(e)[-1600:]));print('SKIP',entry['name'],str(e)[-120:],flush=True)
  assert len(records)<240
  (OUT/'skins.json').write_text(json.dumps(dict(characters=records,skipped=skipped,interfaces=[dict(name=p['name'],center=p['c'].tolist(),normal=p['n'].tolist(),radii=p['r'].tolist()) for p in PLANES]),indent=2))
  (OUT/'skins.txt').write_text('\n'.join(f'{r["id"]}|{r["key"]}|{r["game"]} / {r["name"]}' for r in records)+'\n',encoding='ascii')
 weapons=build_weapons();(OUT/'arsenal.json').write_text(json.dumps(weapons,indent=2));(OUT/'arsenal.txt').write_text('\n'.join(f'{r["id"]}|{r["key"]}|{r["name"]}|{r["animations"]}' for r in weapons)+'\n',encoding='ascii')
 import pack_previews
 pack_previews.ROOT=OUT
 pack_previews.pack()
 print('Finished:',len(records),'characters;',len(weapons),'weapon/equipment models; skipped',len(skipped),flush=True)
if __name__=='__main__':main()

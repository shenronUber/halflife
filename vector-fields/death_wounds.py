"""Measured wound charts: uniform texel scale and animated boundary ownership."""
import hashlib,json,math,struct
from pathlib import Path
import numpy as np
from PIL import Image
from build_skins import vertex
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/deaths'
PIXELS=256
WORLD_SIDE=16.0
DENSITY=PIXELS/WORLD_SIDE
REGIONS=[(1,'neck','neck',12),(2,'arm_left','arm',15),(4,'arm_right','arm',22),(8,'thigh_left','thigh',2),(16,'thigh_right','thigh',5)]

def point_key(v):return tuple(np.round(v['p'],5))
def edge_key(a,b):return tuple(sorted((point_key(a),point_key(b))))
def components(edges):
 remaining=list(edges);out=[]
 while remaining:
  group=[remaining.pop()];points={point_key(v) for e in group for v in e};changed=True
  while changed:
   changed=False
   for i in range(len(remaining)-1,-1,-1):
    keys={point_key(v) for v in remaining[i]}
    if points&keys:points|=keys;group.append(remaining.pop(i));changed=True
  out.append(group)
 return out

def frame(edges):
 points=np.array(sorted({point_key(v) for e in edges for v in e}));center=points.mean(0)
 if len(points)<3:return None
 _,singular,axes=np.linalg.svd(points-center,full_matrices=False)
 if singular[1]<1e-6:return None
 for i in [0,1]:
  if axes[i,np.argmax(np.abs(axes[i]))]<0:axes[i]*=-1
 axes[2]=np.cross(axes[0],axes[1]);q=(points-center)@axes.T
 low,high=q.min(0),q.max(0);mid=(low+high)*.5;origin=center+mid[0]*axes[0]+mid[1]*axes[1]
 # Padding is in model units; it is never an arbitrary triangle-wide UV strip.
 assert max(high[:2]-low[:2])<WORLD_SIDE-.25,'Wound exceeds its physical UV canvas'
 return dict(center=center,origin=origin,axes=axes,width=high[0]-low[0],height=high[1]-low[1],depth=high[2]-low[2],points=points)

def uv(position,f):return .5+((position-f['origin'])@f['axes'][:2].T)/WORLD_SIDE

def cap(edges,bone,material,outward=None):
 triangles=[];charts=[]
 for loop in components(edges):
  f=frame(loop)
  if f is None:continue
  area=projected=0
  for a,b in loop:
   center=f['center'];n=np.cross(b['p']-center,a['p']-center);length=np.linalg.norm(n)
   if length<1e-7:continue
   n/=length
   # Keep both edge vertices on the exact same bones as the retained clothing.
   tri=[vertex(center,n,uv(center,f),bone),vertex(b['p'],n,uv(b['p'],f),b['b']),vertex(a['p'],n,uv(a['p'],f),a['b'])]
   if outward is not None and np.dot(n,outward)<0:
    tri=[tri[0],tri[2],tri[1]]
    for v in tri:v['n']=-v['n']
   triangles.append((material,tri));area+=length*.5
   p=np.array([v['uv'] for v in tri]);projected+=abs(np.linalg.det(np.column_stack((p[1]-p[0],p[2]-p[0]))))*.5*WORLD_SIDE**2
  charts.append(dict(width_u=float(f['width']),height_v=float(f['height']),depth_n=float(f['depth']),bounds_xyz=np.ptp(f['points'],axis=0).tolist(),center=f['center'].tolist(),uv_origin=f['origin'].tolist(),uv_axes=f['axes'][:2].tolist(),surface_area=float(area),projected_triangle_area=float(projected),edge_bones=sorted({v['b'] for e in loop for v in e}),edge_count=len(loop),pixel_extent=[float(f['width']*DENSITY),float(f['height']*DENSITY)],uv_world_side=WORLD_SIDE,texels_per_unit=DENSITY,texture=material,uv_bounds=np.array([uv(p,f) for p in f['points']]).min(0).tolist()+np.array([uv(p,f) for p in f['points']]).max(0).tolist()))
 return triangles,charts

def textures(destination):
 records=[]
 for region,label,family,bone in REGIONS:
  source=ASSETS/(family+'-source.png');name='death_'+label+'.bmp'
  with Image.open(source) as im:
   size=list(im.size);im=im.convert('RGB').resize((PIXELS,PIXELS),Image.Resampling.LANCZOS)
   im.quantize(256,dither=Image.Dither.NONE).save(destination/name)
  records.append(dict(region=region,label=label,family=family,material=name,size=[PIXELS,PIXELS],source=str(source.relative_to(ROOT)),lighting='GoldSrc flatshade (ambient + 0.8 shade light)',source_pixels=size,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),uv_world_side=WORLD_SIDE,texels_per_unit=DENSITY))
 return records


def cut_planes(model):
 planes={1:dict(c=np.array([.234,-.611,59.05]),n=np.array([0.,0.,1.]),bone=12,method='original_collar_boundary')}
 for region,bone,child,distance in [(2,15,16,1.9),(4,22,23,1.9),(8,2,3,2.5),(16,5,6,2.5)]:
  joint=model.bind[bone][:3,3];normal=model.bind[child][:3,3]-joint;normal/=np.linalg.norm(normal)
  planes[region]=dict(c=joint+normal*distance,n=normal,bone=bone)
  if region in (8,16):planes[region]=dict(c=np.array([joint[0],joint[1],30.]),n=np.array([0.,0.,-1.]),bone=bone)
 return planes


def partition(poly,plane):
 from build_skins import clip,clone
 # Original vertices exactly on a cut also share the cut's bone.
 poly=[clone(v) for v in poly]
 for v in poly:
  if abs(np.dot(v['p']-plane['c'],plane['n']))<1e-5:v['b']=plane['bone']
 distances=[np.dot(v['p']-plane['c'],plane['n']) for v in poly]
 if max(distances)<=1e-6:return poly,[]
 if min(distances)>=-1e-6:return [],poly
 return clip(poly,plane,False),clip(poly,plane,True)


def detached_clothing(zones):
 mesh=[t for triangles in zones for t in triangles];parents=list(range(len(mesh)));owners={}
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for i,(_,tri) in enumerate(mesh):
  for v in tri:
   key=point_key(v)
   if key in owners:parents[root(i)]=root(owners[key])
   else:owners[key]=i
 parts={}
 for i in range(len(mesh)):parts.setdefault(root(i),[]).append(mesh[i])
 largest=max(map(len,parts.values()));kept=set()
 for part in parts.values():
  # The separate thigh holster is equipment, and has no exposed flesh surface.
  if len(part)<largest and max(v['p'][2] for _,tri in part for v in tri)<40:
   kept.update(id(tri) for _,tri in part)
 return kept


def segment(zones,model):
 from build_skins import fan
 groups=[[] for _ in range(11)];planes=cut_planes(model);accessories=detached_clothing(zones)
 def append(material,poly,region,zone):
  if len(poly)<3:return
  group=0 if region==1 else (4 if region==2 else 5) if zone==2 else (8 if region==8 else 9) if zone==4 else (6 if region==8 else 7 if region==16 else 10) if zone==3 else {2:2,4:3}.get(region,1)
  groups[group]+=fan(material,poly)
 for zone,triangles in enumerate(zones):
  for material,tri in triangles:
   if id(tri) in accessories:append(material,tri,0,zone);continue
   if zone==0:append(material,tri,1,0);continue
   trunk=tri
   if zone in (0,1,2):
    trunk,left=partition(trunk,planes[2]);append(material,left,2,zone)
    if trunk:trunk,right=partition(trunk,planes[4]);append(material,right,4,zone)
    append(material,trunk,0,zone)
   else:
    # Keep belt/holster geometry on the pelvis. The two leg tubes are separate
    # below the crotch; planar cuts at z=30 never split a leg by world x.
    left=sum(v['b'] in (2,3,4) for v in trunk);right=sum(v['b'] in (5,6,7) for v in trunk)
    region=8 if left>right else 16 if right else 0
    if region:
     retained,removed=partition(trunk,planes[region]);append(material,retained,0,zone);append(material,removed,region,zone)
    else:append(material,trunk,0,zone)
 return groups,planes,len(accessories)


def shade_materials(path):
 # GoldSrc's ordinary flat lighting keeps downward cut faces readable while
 # still using the entity's ambient/shade light. These textures are opaque,
 # non-additive and non-emissive; no fullbright flag is enabled.
 data=bytearray(path.read_bytes());count,offset=struct.unpack_from('<ii',data,180)
 for i in range(count):
  at=offset+i*80;name=data[at:at+64].split(b'\0')[0].decode('latin1')
  if name.startswith('death_'):
   flags=struct.unpack_from('<i',data,at+64)[0];struct.pack_into('<i',data,at+64,flags|1)
 path.write_bytes(data)


def align_collar(groups):
 """Give the shared, slightly non-planar neck ring the same bone on both sides."""
 from collections import defaultdict
 def boundary(triangles):
  edges=defaultdict(list)
  for _,tri in triangles:
   for a,b in zip(tri,tri[1:]+tri[:1]):
    key=edge_key(a,b)
    if key[0]!=key[1]:edges[key].append((a,b))
  return [e[0] for e in edges.values() if len(e)==1]
 head_keys={edge_key(a,b) for a,b in boundary(groups[0])}
 points={point_key(v) for a,b in boundary([t for g in groups[1:] for t in g]) if edge_key(a,b) in head_keys for v in (a,b)}
 for group in groups:
  for _,tri in group:
   for v in tri:
    if point_key(v) in points:v['b']=12
 return groups

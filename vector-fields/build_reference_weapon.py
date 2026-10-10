"""Relais R-01: reproducible textured meshes, 12 interfaces, four core variants per slot, four extra receivers and eight themed modules.
All geometry is authored here. Hands and their timing come from the MP40 rig.
The generated diffuse atlas is archived with its exact imagegen prompt.
"""
import json, math, re, shutil, hashlib, struct, unicodedata, argparse
from pathlib import Path
import numpy as np
from PIL import Image
import build_modular as base
import build_skins as geo
from build_weapon_visuals import HEADER
from studio_assets import Studio
import build_reference_extensions as extensions
import build_reference_chassis as chassis
import build_reference_themes as themes
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/r01'; SOURCE=ROOT/'generated/weapon_visuals'
KEYS=['receiver','barrel','muzzle','feed','chamber','ammo','projectile','optic','underbarrel','grip','power','cooling']
NAMES=[('R-01 / Chassis Atelier','R-01 / Chassis Circuit'),('Canon chemise','Canon a induction'),('Frein ajoure','Moderateur court'),('Chargeur nervure','Chargeur double pile'),('Culasse a levier','Culasse a glissiere'),('Cassette balistique','Cassette energetique'),('Porte-flechettes','Porte-ampoules'),('Viseur cadre','Lunette compacte'),('Poignee inclinee','Tube auxiliaire'),('Crosse squelette','Crosse amortie'),('Cellule ambre 24V','Condensateur teal 48V'),('Radiateur a ailettes','Circuit cuivre')]
DESCS=[('Capot ocre, pontets metalliques et plaque de serie.','Capot clair, renforts sombres et panneau de service.'),('Chemise ventilee et bagues usinees.','Enroulements de cuivre et isolateurs ceramiques.'),('Chambres ouvertes et couronne metallique.','Corps cylindrique court, colliers et bouche creuse.'),('Coque emboutie et sabot. Suit la main au rechargement.','Corps elargi et deux nervures. Meme point d insertion.'),('Levier lateral et capot mobile au tir.','Glissiere renforcee animee avec le meme cycle.'),('Cartouches visibles dans une cassette laterale.','Cellules encastrees et indicateur de charge.'),('Trois flechettes retenues dans un berceau.','Deux ampoules sous un capot de protection.'),('Cadre rectangulaire et lentille texturee a reflets bleus, sans croix ajoutee.','Deux bagues, oculaire et tourelles de reglage.'),('Prise caoutchouc inclinee sur collier commun.','Capsule sous canon avec verrou et collier.'),('Poignee textilee et crosse tubulaire.','Poignee moulee et crosse a plaque amortissante.'),('Batterie amovible, verrou, bornes et etiquette 24V.','Deux capaciteurs, etrier, bornes et etiquette 48V.'),('Six ailettes metalliques sur semelle commune.','Deux conduites cuivre et echangeur ceramique.')]

def tex(i):return f'r01_t{i:02}.bmp'
# Square texture tiles have one physical scale in both directions. Long faces
# are clipped into UV cells because StudioMDL crops UVs outside the 0..1 domain.
TILE_SIZE={0:4.0,1:2.8,2:3.2,3:3.2,4:2.7,5:3.0,6:1.6,7:2.5,8:2.8,9:2.8,10:1.6,11:1.8,13:2.0,14:1.8,15:1.4}
class Mesh:
 def __init__(self):self.tris=[]
 def emit(self,p,n,uv,mat):
  for i in range(1,len(p)-1):
   indices=[0,i,i+1]
   if np.linalg.norm(np.cross(p[i]-p[0],p[i+1]-p[0]))<1e-9:continue
   self.tris.append((tex(mat),[geo.vertex(p[j],n,uv[j],0)for j in indices]))
 def tiled(self,p,n,uv,mat):
  polygon=np.column_stack((p,uv))
  low=np.floor(np.min(uv,axis=0)+1e-9).astype(int)
  high=np.ceil(np.max(uv,axis=0)-1e-9).astype(int)
  def clip(poly,axis,bound,sign):
   result=[]
   for a,b in zip(poly,np.roll(poly,-1,axis=0)):
    da=(a[axis]-bound)*sign;db=(b[axis]-bound)*sign
    if da>=-1e-10:result.append(a)
    if (da>1e-10 and db<-1e-10)or(da<-1e-10 and db>1e-10):
     result.append(a+(b-a)*(bound-a[axis])/(b[axis]-a[axis]))
   return np.array(result)
  for u in range(low[0],high[0]):
   for v in range(low[1],high[1]):
    cell=polygon
    for axis,bound,sign in [(3,u,1),(3,u+1,-1),(4,v,1),(4,v+1,-1)]:
     if len(cell)<3:break
     cell=clip(cell,axis,bound,sign)
    if len(cell)>=3:self.emit(cell[:,:3],n,np.clip(cell[:,3:]-[u,v],0,1),mat)
 def face(self,points,mat=0,center=None,uv=None,tile=False):
  p=[np.array(x,float) for x in points]
  n=np.cross(p[1]-p[0],p[2]-p[0]);length=np.linalg.norm(n)
  if length<1e-8:return
  n/=length
  if center is not None and np.dot(n,np.mean(p,axis=0)-center)<0:
   p.reverse();n=-n
   if uv is not None:uv=list(reversed(uv))
  if uv is None:
   # An orthonormal plane basis also preserves scale on chamfers and oblique
   # faces; dropping a world axis would compress their short direction.
   axis=int(np.argmax(abs(n)));u=np.eye(3)[1 if axis==0 else 0]
   u=u-n*np.dot(u,n);u/=np.linalg.norm(u)
   if axis==0 and n[0]<0:u=-u
   v=np.cross(n,u)
   if v[2]<-1e-6 or(abs(v[2])<1e-6 and v[1]<0):v=-v
   uv=np.array([[np.dot(q,u),np.dot(q,v)]for q in p])/TILE_SIZE.get(mat,3.0)+.5
   tile=True
  if tile:self.tiled(p,n,np.array(uv),mat)
  else:self.emit(p,n,uv,mat)
 def box(self,c,d,mat=0,bevel=.15):
  c=np.array(c,float);h=np.array(d,float)/2;b=min(bevel,h[0]*.7,h[2]*.7)
  cross=[(-h[0]+b,-h[2]),(h[0]-b,-h[2]),(h[0],-h[2]+b),(h[0],h[2]-b),(h[0]-b,h[2]),(-h[0]+b,h[2]),(-h[0],h[2]-b),(-h[0],-h[2]+b)]
  rings=[[c+np.array([x,y,z])for x,z in cross]for y in [-h[1],h[1]]]
  for r in rings:self.face(r,mat,c)
  for i in range(8):j=(i+1)%8;self.face([rings[0][i],rings[1][i],rings[1][j],rings[0][j]],mat,c)
 def cyl(self,a,b,r,mat=0,n=12,r2=None,cap=True):
  a=np.array(a,float);b=np.array(b,float);axis=b-a;axis/=np.linalg.norm(axis)
  u=np.cross(axis,[0,0,1]if abs(axis[2])<.9 else[0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u)
  ring=lambda p,rad:[p+rad*(u*math.cos(i*2*math.pi/n)+v*math.sin(i*2*math.pi/n))for i in range(n)]
  aa,bb=ring(a,r),ring(b,r if r2 is None else r2);c=(a+b)/2
  size=TILE_SIZE.get(mat,3.0);step=2*r*math.sin(math.pi/n)/size;length=np.linalg.norm(b-a)/size
  for i in range(n):
   j=(i+1)%n;points=[aa[i],aa[j],bb[j],bb[i]]
   if mat==11:self.face(points,mat,c,[(i/n,0),((i+1)/n,0),((i+1)/n,1),(i/n,1)])
   elif r2 is not None and abs(r2-r)>1e-6:self.face(points,mat,c)
   else:self.face(points,mat,c,[(i*step,.5-length/2),((i+1)*step,.5-length/2),((i+1)*step,.5+length/2),(i*step,.5+length/2)],tile=True)
  if cap:self.face(aa,mat,c);self.face(bb,mat,c)
 def tube(self,a,b,r,inner,mat=0,n=12):
  a=np.array(a,float);b=np.array(b,float);axis=(b-a)/np.linalg.norm(b-a)
  u=np.cross(axis,[0,0,1]if abs(axis[2])<.9 else[0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u)
  rings=[[p+rad*(u*math.cos(i*2*math.pi/n)+v*math.sin(i*2*math.pi/n))for i in range(n)]for p,rad in [(a,r),(b,r),(a,inner),(b,inner)]]
  # Outer, inner and end rings; open bore is real geometry.
  for i in range(n):
   j=(i+1)%n
   for first,rad,material in [(0,r,mat),(2,inner,0)]:
    size=TILE_SIZE.get(material,3.0);step=2*rad*math.sin(math.pi/n)/size;length=np.linalg.norm(b-a)/size
    points=[rings[first][i],rings[first][j],rings[first+1][j],rings[first+1][i]]
    uv=[(i*step,.5-length/2),((i+1)*step,.5-length/2),((i+1)*step,.5+length/2),(i*step,.5+length/2)]
    if first==2:points.reverse();uv.reverse()
    self.face(points,material,(a+b)/2 if first==0 else None,uv,tile=True)
   for k in [0,1]:self.face([rings[k][i],rings[k+2][i],rings[k+2][j],rings[k][j]],5,(a+b)/2)
 def panel(self,x,y,z,w,h,mat,side=1,rotate=False,repeat=0):
  # Repeat along the long direction. Crop the small residual margin instead
  # of stretching each square motif; never alternate/mirror adjacent cells.
  count=max(1,round(max(w/h,h/w)))if repeat==0 else max(1,int(repeat))
  nx,nz=(count,1)if w>=h else(1,count)
  cw,ch=w/nx,h/nz;size=max(cw,ch)
  uv=np.array([(-cw/2,-ch/2),(cw/2,-ch/2),(cw/2,ch/2),(-cw/2,ch/2)])/size+.5
  if side<0:uv[:,0]=1-uv[:,0]
  if rotate:uv=np.column_stack((uv[:,1],1-uv[:,0]))
  for iy in range(nx):
   for iz in range(nz):
    lo=y-w/2+iy*cw;hi=lo+cw;bottom=z-h/2+iz*ch;top=bottom+ch
    self.face([[x,lo,bottom],[x,hi,bottom],[x,hi,top],[x,lo,top]],mat,np.array([x-side,y,z]),uv)
 def screws(self,x,y,z,w,h,side=1):
  for dy in [-w/2,w/2]:
   for dz in [-h/2,h/2]:self.cyl([x,y+dy,z+dz],[x+side*.12,y+dy,z+dz],.115,5,6)
 def rail(self,y0,y1,z=3.3):
  self.box([0,(y0+y1)/2,z],[1.2,y1-y0,.35],0,.07)
  for y in np.arange(y0+.3,y1,.65):self.box([0,y,z+.24],[1.8,.32,.3],5,.07)

def part(slot,v,mount=0):
 if v>=2:return extensions.part(slot,v,Mesh)
 m=Mesh();paint=2 if not v else 3
 if slot=='receiver':
  m.box([0,5,0],[3.5,24,4],0,.45)
  m.box([0,3,1.8],[3.9,18,1.4],paint,.35)
  if mount==0:m.box([0,15,-1.6],[3,5,2],0,.3)
  elif mount==1:
   # Open lateral well; the same neck now enters along +X.
   for z in [-1.35,1.55]:m.box([-2.05,15.25,z],[1.4,3.7,.6],5,.12)
   for y in [13.7,16.8]:m.box([-2.05,y,.1],[1.4,.6,2.4],0,.12)
   m.box([0,15,-2],[3,4,.4],paint,.12)
  else:
   # Open top well with a closed underside and an offset optic bridge.
   for x in [-1.35,1.35]:m.box([x,15.25,2.45],[.55,3.4,1.4],5,.12)
   for y in [13.85,16.65]:m.box([0,y,2.45],[2.5,.55,1.4],0,.12)
   m.box([0,15,-2],[3,4,.4],paint,.12)
   m.box([1.7,3,3.05],[5.2,3,.55],5,.15)
   m.box([3.4,3,3.35],[1.8,4,.45],0,.12)
  for side in [-1,1]:
   m.panel(side*1.77,6,.1,8,2.8,1,side);m.screws(side*1.8,6,.1,7,2,side)
   m.panel(side*1.96,-2.5,1.8,2,1,3,side,repeat=1)
   m.panel(side*1.8,13.1,.6,3,1.6,6,side)
  m.rail(-4,12,2.7)
  # Trigger guard, genuinely open between four narrow members.
  m.box([0,3,-6],[.65,6,.45],5,.12)
  m.box([0,5.8,-4],[.65,.45,4],0,.1)
  m.box([0,.2,-4],[.65,.45,4],0,.1)
  m.cyl([0,2.2,-1.8],[0,3,-4.6],.2,5,8)
  m.box([0,-6,0],[3.9,1,3.7],5,.3)
 elif slot=='barrel':
  m.tube([0,17,1.3],[0,31,1.3],.75,.35,5)
  for y in [17.5,22,28.5,30]:m.tube([0,y,1.3],[0,y+.55,1.3],1.15,.78,0)
  if not v:
   m.box([0,22.5,1.3],[2.45,9,2.35],0,.4)
   for side in [-1,1]:m.panel(side*1.24,22.5,1.3,7.8,1.25,6,side)
   m.box([0,22.5,2.55],[1.5,8,.15],2,.04)
  else:
   for y in np.arange(19,28,.65):m.tube([0,y,1.3],[0,y+.37,1.3],1.1,.79,7)
   for side in [-1,1]:m.box([side*1.18,23,1.3],[.24,8,1],13,.08)
  m.rail(17.7,20,2.6)
 elif slot=='muzzle':
  m.tube([0,30.8,1.3],[0,31.7,1.3],1.08,.4,5)
  if not v:
   for y in [31.7,33.2,34.7]:m.tube([0,y,1.3],[0,y+.5,1.3],1.15,.5,0)
   for x in [-.85,.85]:m.box([x,33.3,1.3],[.38,3.5,.55],5,.1)
  else:
   m.tube([0,31.7,1.3],[0,36.5,1.3],1.38,.5,0,16)
   for y in [32,35.7]:m.tube([0,y,1.3],[0,y+.3,1.3],1.48,1.39,5,16)
 elif slot=='feed':
  w=1.8 if not v else 2.35
  m.box([-.15,15.25,-2.3],[1.65,1.75,3],5,.12)
  m.box([-.15,15.25,-8.3],[w,2.05,10.8],0,.22)
  for side in [-1,1]:
   m.panel(-.15+side*(w/2+.02),15.25,-8.2,1.8,9.5,14,side,rotate=True)
   if v:
    for z in [-6,-10]:m.box([-.15+side*w/2,15.25,z],[.18,2.1,.5],5,.05)
  m.box([-.15,15.25,-13.9],[w+.28,2.35,.6],4,.1)
  m.box([-.15,15.25,-3.1],[w+.15,2.2,.4],5,.1)
 elif slot=='chamber':
  m.box([2.02,5,.6],[.45,7,1.7],0,.15)
  m.panel(2.27,5,.6,6,1.4,15,repeat=0)
  if not v:m.cyl([2.1,6,.5],[3.4,6,.5],.19,5,8);m.cyl([3.4,5.5,.5],[3.4,6.5,.5],.38,4,8)
  else:
   m.box([2.6,5,.6],[.5,3,1.5],5,.22)
   for y in [4.3,5,5.7]:m.box([2.9,y,.6],[.14,.28,1.4],0,.03)
 elif slot=='ammo':
  m.box([2.05,-2,-.4],[.55,4,2.3],0,.12)
  for y in [-3.2,-2.4,-1.6,-.8]:m.cyl([2.47,y,-1.25],[2.47,y,.45],.22,7 if not v else 9,8)
  for z in [-1,.35]:m.box([2.67,-2,z],[.2,3.6,.24],5,.04)
  m.box([2.08,-4,-.4],[.7,.35,2.7],paint,.1)
 elif slot=='projectile':
  m.box([-2.03,12,-.1],[.4,3.3,2.8],0,.12)
  for y in ([10.9,12,13.1]if not v else[11.2,12.8]):
   m.cyl([-2.4,y,-1.4],[-2.4,y,.4],.18 if not v else .38,5 if not v else 9,8)
   m.cyl([-2.4,y,.4],[-2.4,y,1],.18 if not v else .38,7 if not v else 5,8,r2=.03)
  for z in [-1,.15]:m.box([-2.65,12,z],[.2,3.4,.25],paint,.05)
 elif slot=='optic':
  m.box([0,3,3.8],[1.8,4,.55],0,.14)
  if not v:
   # Rectangular sight with a chamfered rim and the generated lens image.
   # UVs isolate the glass inside the source tile; additive glass keeps the scene visible.
   def profile(w,h,b):
    return [(-w/2+b,-h/2),(w/2-b,-h/2),(w/2,-h/2+b),(w/2,h/2-b),(w/2-b,h/2),(-w/2+b,h/2),(-w/2,h/2-b),(-w/2,-h/2+b)]
   center=np.array([0,3,5.2]);rings=[[center+np.array([x,y,z])for x,z in profile(w,h,b)]for y,w,h,b in [(-.34,2.8,2.25,.26),(.34,2.8,2.25,.26),(-.34,2.26,1.72,.15),(.34,2.26,1.72,.15)]]
   for i in range(8):
    j=(i+1)%8
    m.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],0,center)
    m.face([rings[2][i],rings[2][j],rings[3][j],rings[3][i]],5)
    for k in [0,1]:m.face([rings[k][i],rings[k][j],rings[k+2][j],rings[k+2][i]],0,center)
   # The existing r01_t11 lens image is used directly. Its metal surround
   # stays out of the UV window; the physical frame supplies that geometry.
   glass=[center+np.array([x,-.02,z])for x,z in profile(2.26,1.72,.15)]
   glass_uv=[(.5+x/2.26*.5,.5+z/1.72*.5)for x,z in profile(2.26,1.72,.15)]
   m.face(glass,11,uv=glass_uv)
   m.face(list(reversed(glass)),11,uv=list(reversed(glass_uv)))
   m.box([0,3,4.04],[2.65,.95,.32],5,.09)
   # The lens image is the visual treatment; no added cross over the glass.
   for x in [-.93,.93]:m.box([x,2.63,4.18],[.38,.07,.11],2,.025)
   m.cyl([1.3,3,4.75],[1.7,3,4.75],.24,5,8)
  else:
   for y in [1,5]:m.box([0,y,4.4],[1.3,.65,1.3],5,.12)
   m.tube([0,-.7,5.3],[0,7,5.3],.9,.66,0,16)
   for y in [-.7,5.8]:m.tube([0,y,5.3],[0,y+1.2,5.3],1.15,.68,4,16)
   m.cyl([0,-.6,5.3],[0,-.58,5.3],.66,11,16)
   m.cyl([0,6.85,5.3],[0,6.86,5.3],.66,11,16)
   m.cyl([0,3,6],[0,3,6.8],.55,0,12)
   m.cyl([.6,3,5.3],[1.4,3,5.3],.5,0,12)
 elif slot=='underbarrel':
  m.box([0,23,-.55],[1.55,4,.4],5,.1)
  if not v:
   m.cyl([0,23,-.5],[0,21,-4.1],.68,4,8,r2=.85)
   m.box([0,21,-4.2],[1.7,1.4,.5],0,.2)
  else:
   m.cyl([0,20.2,-1.9],[0,27,-1.9],.85,0,12)
   for y in [21,25.5]:m.tube([0,y,-1.9],[0,y+.5,-1.9],1,.86,5)
   m.box([0,24,-2.8],[1.1,2,.15],13,.04)
 elif slot=='grip':
  # Grip fits the original right hand. The supporting hand grips the magazine.
  m.box([0,-1.8,-5.2],[2.3,3.3,7],4,.45)
  m.box([0,-1.8,-8.8],[2.6,3.65,.5],0,.15)
  for side in [-1,1]:m.panel(side*1.16,-1.8,-5.2,2.7,5.5,4,side);m.screws(side*1.2,-1.8,-5.2,1.7,4,side)
  if not v:
   for x in [-1.1,1.1]:m.cyl([x,-6,1],[x,-16,1],.3,5,8)
   m.box([0,-16,0],[2.8,1,5],4,.4)
   m.cyl([0,-7,-1.1],[0,-15,-1.1],.28,0,8)
  else:
   m.box([0,-11,1],[2.7,10,2.5],0,.45)
   m.box([0,-14,1.5],[2.9,4,2],2,.35)
   m.box([0,-16.5,0],[3,1.2,5.3],4,.5)
   for side in [-1,1]:m.panel(side*1.38,-10.4,1,4,1.4,1,side)
 elif slot=='power':
  m.box([-2.02,5,-.2],[.7,4.6,3.8],5,.2)
  if not v:
   m.box([-3,5,-.25],[1.8,4.2,3.4],2,.35)
   m.panel(-3.92,5,-.25,3.7,2.8,8,-1,repeat=1)
  else:
   for y in [3.8,6.2]:m.cyl([-3,y,-1.8],[-3,y,1.5],.92,9,12)
   m.box([-3.05,5,-.2],[1.9,4.4,.9],0,.1)
   m.panel(-4.02,5,-.15,3.8,1.8,9,-1,repeat=1)
  for y in [3.7,6.3]:m.cyl([-2.8,y,1.35],[-2.8,y,2.1],.23,7,8)
  for z in [-1.8,1.6]:m.box([-3,5,z],[2,4.6,.3],0,.1)
  m.box([-3.1,2.6,-.15],[1,.5,1.3],5,.1)
  m.panel(-4.06,5,1,1.6,.5,10,-1,repeat=1)
 elif slot=='cooling':
  for side in [-1,1]:
   m.box([side*1.4,25,1.2],[.3,4,1.7],0,.1)
   if not v:
    for y in np.arange(23.3,26.9,.6):m.box([side*1.75,y,1.2],[.75,.24,2.3],5,.12)
   else:
    m.box([side*1.8,25,1.2],[.6,3.8,1.8],13,.12)
    for z in [.65,1.8]:
     m.cyl([side*2.2,23,z],[side*2.2,27,z],.17,7,8)
     for y in [23,27]:m.cyl([side*1.5,y,z],[side*2.2,y,z],.17,7,8)
 return m.tris

def prepare_rig():
 for p in SOURCE.glob('*.bmp'):shutil.copy2(p,OUT/p.name)
 names,parents,bind=base.skeleton(SOURCE/'mp40_hands.smd');bone=next(i for i,n in names.items()if n=='Bone76');bid=max(names)+1
 files=['mp40_hands','idle','idle_1','shoot1','reload','draw','shoot1_1','shoot2','shoot2_1','empty_idle']
 for name in files:
  text=(SOURCE/(name+'.smd')).read_text(encoding='utf-8');start=text.index('nodes\n')+6;end=text.index('end',start)
  text=text[:end]+f'{bid} "R01_Bolt" {bone}\n'+text[end:]
  skstart=text.index('skeleton\n')+9;skend=text.index('end',skstart);sk=text[skstart:skend];frames=re.split(r'(time \d+\n)',sk);times=[int(x.split()[1])for x in frames if x.startswith('time ')]
  for i in range(1,len(frames),2):
   t=int(frames[i].split()[1]);f=t/max(times[-1],1)
   motion=math.sin(math.pi*min(f*1.8,1))*.9 if name.startswith('shoot')else max(0,1-abs(f-.88)/.06)*1.3 if name=='reload'else 0
   frames[i+1]+=f'{bid} 0 {-motion:.6f} 0 0 0 0\n'
  text=text[:skstart]+''.join(frames)+text[skend:];(OUT/(name+'.smd')).write_text(text,encoding='ascii')
 qc=(SOURCE/'mp40_rig.qc').read_text(encoding='utf-8').replace('mp40_rig.mdl','r01_rig.mdl')
 qc=re.sub(r'\$bodygroup magazine\s*\{.*?\}','',qc,flags=re.S)
 qc=re.sub(r'(\$sequence "reload" \{.*?fps )50',lambda m:m[1]+str(139/1.5),qc,flags=re.S)
 qc=qc.replace('$attachment 0 "Bone76" 0.000000 29.500000 1.750000','$attachment 0 "Bone76" 0.000000 36.500000 1.300000')
 header,_,_=base.read_smd(OUT/'mp40_hands.smd')
 anchors=[]
 for anchor in [bone,next(i for i,n in names.items()if n=='Bone71'),bid]:
  origin=bind[bone if anchor==bid else anchor][:3,3]
  rows=[f'{anchor} {origin[0]+dx:.6f} {origin[1]+dy:.6f} {origin[2]:.6f} 0 0 1 0 0'for dx,dy in [(0,0),(.01,0),(0,.01)]]
  anchors.append((tex(0),rows))
 base.write_smd(OUT/'r01_anchors.smd',header,anchors)
 qc+='\n$bodygroup anchors\n{\n blank\n studio "r01_anchors"\n}\n'
 qc+='\n$attachment 2 "R01_Bolt" 0 0 0\n';(OUT/'r01_rig.qc').write_text(qc,encoding='ascii')
 from first_person_grips import bottom_reload
 bottom_reload(OUT)
 base.compile_model(OUT/'r01_rig.qc');s=Studio(OUT/'r01_rig.mdl');assert 'R01_Bolt'in s.names
 return s

def prepare_styles():
 from build_r01_texture_variants import split_atlas
 styles=[dict(id='original',title='Atelier original',skin=0)]
 config=json.loads((ROOT/'assets/r01/variants/variants.json').read_text(encoding='utf-8'))
 for index,entry in enumerate(config['variants'],1):
  folder=ROOT/'assets/r01/variants'/entry['id']
  split_atlas(folder/'texture-atlas.png',folder/'tiles')
  for material in range(16):shutil.copy2(folder/'tiles'/tex(material),OUT/f's{index:02}_t{material:02}.bmp')
  styles.append(dict(id=entry['id'],title=entry['title'],skin=index))
 from catalog_assets import weapon_style_catalog
 content=json.loads((ROOT/'data/gameplay-content.json').read_text(encoding='utf-8'))
 (ROOT/'data/r01_styles.txt').write_text(weapon_style_catalog(styles,content),encoding='ascii')
 return styles

def style_texture(style,material):
 return tex(material)if style['skin']==0 else f"s{style['skin']:02}_t{material:02}.bmp"

def texture_group(mesh,styles):
 materials=sorted({int(name[5:7])for name,_ in mesh})
 if len(materials)*len(styles)>100:raise ValueError('GoldSrc texture limit exceeded; reduce styles or materials per mesh.')
 rows=['{ '+' '.join(tex(i)if style['skin']==0 else f"s{style['skin']:02}_t{i:02}.bmp"for i in materials)+' }'for style in styles]
 return '\n$texturegroup r01_styles\n{\n'+'\n'.join(rows)+'\n}\n'

def stage_inputs():
 from build_cache import compiler_inputs
 common=[Path(__file__),ROOT/'model_contract.py',ROOT/'data/model_contract.json']+compiler_inputs()
 config=json.loads((ROOT/'assets/r01/variants/variants.json').read_text(encoding='utf-8'))
 modules=common+[ROOT/p for p in ['build_reference_extensions.py','build_reference_chassis.py','build_reference_themes.py','build_weapon_visuals.py','build_r01_texture_variants.py','catalog_assets.py','data/gameplay-content.json','assets/r01/texture-atlas.png','assets/r01/variants/variants.json']]
 modules += [ROOT/'assets/r01/variants'/entry['id']/'texture-atlas.png' for entry in config['variants']]
 # Only the bind pose affects magazine vertices, not gesture or foregrip recipes.
 modules += [SOURCE/'mp40_hands.smd',SOURCE/'mp40_rig.qc']
 rigs=common+[ROOT/'assets/r01/texture-atlas.png',ROOT/'build_reference_platforms.py',ROOT/'first_person_grips.py',ROOT/'build_foregrip.py',ROOT/'assets/animations/r01-first-person-foregrip.json']
 rigs += [p for p in SOURCE.iterdir() if p.suffix in ('.smd','.qc','.bmp')]
 return dict(modules=modules,rigs=rigs)


def inputs_hash():
 from build_cache import fingerprint
 return fingerprint([p for paths in stage_inputs().values() for p in paths])


def stage_outputs(stage,manifest):
 if stage=='modules':
  return [OUT/(r['id']+'.mdl') for r in manifest['pieces']]+[ROOT/'data/r01_styles.txt',OUT/'module_idle.smd']+list(OUT.glob('r01_t*.bmp'))+list(OUT.glob('s*_t*.bmp'))
 sequences=['idle','idle_1','shoot1','reload','draw','shoot1_1','shoot2','shoot2_1','empty_idle']
 names=['mp40_hands','r01_anchors']+sequences
 names += [prefix+seq for prefix in ['side_','top_'] for seq in sequences]
 names += [prefix+seq+'_fg' for prefix in ['','side_','top_'] for seq in sequences]
 paths=[OUT/(name+'.smd') for name in names]
 paths += [OUT/(name+ext) for name in ['r01_rig','r01_rig_side','r01_rig_top','r01_rig_fg','r01_rig_side_fg','r01_rig_top_fg'] for ext in ['.mdl','.qc']]
 return paths+[OUT/'platform-motion.json',OUT/'foregrip-motion.json']+[OUT/p.name for p in SOURCE.glob('*.bmp')]


def module_catalog_current(manifest):
 if not manifest.get('pieces') or not (ROOT/'data/equipment.txt').exists():return False
 keys={x.split('|')[1] for x in (ROOT/'data/equipment.txt').read_text(encoding='utf-8').splitlines() if x and not x.startswith('#') and '|' in x}
 return all(r['id'] in keys for r in manifest['pieces'])


def ensure_current():
 from build_cache import fingerprint,current,read
 saved=read(OUT/'build-state.json');manifest=read(OUT/'manifest.json')
 return module_catalog_current(manifest) and all(current(saved.get(stage),fingerprint(paths)) for stage,paths in stage_inputs().items())


def prepare_tiles():
 im=Image.open(ROOT/'assets/r01/texture-atlas.png').convert('RGB');w,h=im.size
 for i in range(16):
  x,y=i%4,i//4
  tile=im.crop((round(x*w/4)+3,round(y*h/4)+3,round((x+1)*w/4)-3,round((y+1)*h/4)-3))
  tile.resize((256,256),Image.Resampling.LANCZOS).quantize(256).save(OUT/tex(i))


def build_rigs():
 rig=prepare_rig()
 from build_reference_platforms import build_rigs as mounted_rigs
 from build_foregrip import build as foregrip
 mounted_rigs(OUT);foregrip(OUT)
 return rig


def build(ensure=False):
 from build_cache import fingerprint,current,read,record,write
 from model_contract import generate
 generate();OUT.mkdir(parents=True,exist_ok=True)
 saved=read(OUT/'build-state.json');manifest=read(OUT/'manifest.json')
 identities={stage:fingerprint(paths) for stage,paths in stage_inputs().items()}
 dirty={stage:not ensure or not current(saved.get(stage),identity) for stage,identity in identities.items()}
 dirty['modules'] |= not module_catalog_current(manifest)
 if not any(dirty.values()):
  print('R-01 modules and animated rigs are current.');return manifest
 prepare_tiles()
 rig=build_rigs() if dirty['rigs'] else Studio(OUT/'r01_rig.mdl')
 if dirty['modules']:
  build_modules(rig);manifest=read(OUT/'manifest.json')
 else:
  manifest['inputs_sha256']=inputs_hash();write(OUT/'manifest.json',manifest)
 for stage in identities:
  if dirty[stage]:saved[stage]=record(identities[stage],stage_outputs(stage,manifest))
 write(OUT/'build-state.json',saved)
 return manifest


def main():
 return build()

def build_modules(rig):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'module_idle.smd').write_text('\n'.join(HEADER)+'\n',encoding='ascii')
 styles=prepare_styles()
 mag=np.linalg.inv(rig.bind[rig.names.index('Bone71')])@rig.bind[rig.names.index('Bone76')]
 records=[];lines=[]
 for z,key in enumerate(KEYS):
  names=(*NAMES[z],*(r[0]for r in extensions.VARIANTS[key]));descs=(*DESCS[z],*(r[1]for r in extensions.VARIANTS[key]))
  for v in range(4):
   mesh=part(key,v);name=f'r01_{key}_{"abcd"[v]}'
   if key=='feed':
    for _,tri in mesh:
     for p in tri:p['p']=(mag@np.r_[p['p'],1])[:3];p['n']=mag[:3,:3]@p['n']
   base.write_smd(OUT/(name+'.smd'),HEADER,geo.smd_tri(mesh))
   qc=OUT/(name+'.qc');render='\n'+''.join(f'$texrendermode "{style_texture(st,11)}" additive\n'for st in styles)if key=='optic'and v!=1 else'';qc.write_text(f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body module "{name}"\n$sequence idle "module_idle" fps 1\n'+texture_group(mesh,styles)+render,encoding='ascii')
   model=base.compile_model(qc);s=Studio(model);assert np.allclose(s.bind[0],np.eye(4),atol=1e-5)
   assert struct.unpack_from('<i',s.data,196)[0]==len(styles)
   record=dict(id=name,slot=key,slot_index=z+9,variant=v,name=names[v],triangles=len(mesh),bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest());records.append(record)
   lines.append('|'.join([key,name,'1',names[v],'Baseline'if not v else'Engine','Relais R-01','4','4','4','4','0','0',descs[v]+' Visuel uniquement.','0']))
   print(name,len(mesh),'triangles',flush=True)
 from build_reference_platforms import PLATFORMS
 for variant,(key,spec) in enumerate(PLATFORMS.items(),4):
  mesh=part('receiver',variant%2,variant-3);name='r01_receiver_'+key
  base.write_smd(OUT/(name+'.smd'),HEADER,geo.smd_tri(mesh))
  qc=OUT/(name+'.qc');qc.write_text(f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body module "{name}"\n$sequence idle "module_idle" fps 1\n'+texture_group(mesh,styles),encoding='ascii')
  model=base.compile_model(qc)
  records.append(dict(id=name,slot='receiver',slot_index=9,variant=variant,name=spec['name'],triangles=len(mesh),bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest()))
  description=('Alimentation laterale. Extraction sur le cote et main animee.'if key=='side'else'Alimentation superieure. Extraction vers le haut et viseur decale.')+' Memes chargeurs et proprietes.'
  lines.append('|'.join(['receiver',name,'1',spec['name'],'Baseline','Relais R-01','4','4','4','4','0','0',description,'0']))
  print(name,len(mesh),'triangles',flush=True)
 for variant,(key,spec) in enumerate(chassis.CHASSIS.items(),6):
  mesh=chassis.part(key,Mesh);name='r01_receiver_'+key
  base.write_smd(OUT/(name+'.smd'),HEADER,geo.smd_tri(mesh))
  qc=OUT/(name+'.qc');qc.write_text(f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body module "{name}"\n$sequence idle "module_idle" fps 1\n'+texture_group(mesh,styles),encoding='ascii')
  model=base.compile_model(qc)
  records.append(dict(id=name,slot='receiver',slot_index=9,variant=variant,name=spec['name'],triangles=len(mesh),bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest()))
  lines.append('|'.join(['receiver',name,'1',spec['name'],spec['family'],'Relais R-01','4','4','4','4','0','0',spec['description']+(' Alimentation superieure.' if spec.get('mount')==2 else ' Alimentation dessous.'),'0']))
  print(name,len(mesh),'triangles',flush=True)
 # Append themed pieces after every established ID to retain catalogue ordering.
 for key,specs in themes.PARTS.items():
  for v,spec in enumerate(specs,4):
   mesh=themes.part(key,spec['key'],Mesh);name=f"r01_{key}_{spec['key']}"
   base.write_smd(OUT/(name+'.smd'),HEADER,geo.smd_tri(mesh))
   render='\n'+''.join(f'$texrendermode "{style_texture(st,11)}" additive\n'for st in styles)if key=='optic'else''
   qc=OUT/(name+'.qc');qc.write_text(f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body module "{name}"\n$sequence idle "module_idle" fps 1\n'+texture_group(mesh,styles)+render,encoding='ascii')
   model=base.compile_model(qc);compiled=Studio(model)
   assert compiled.numskinfamilies==len(styles) and len(compiled.names)==1
   records.append(dict(id=name,slot=key,slot_index=KEYS.index(key)+9,variant=v,name=spec['name'],theme=spec['key'],triangles=len(mesh),bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest()))
   lines.append('|'.join([key,name,'1',spec['name'],spec['family'],'Relais R-01','4','4','4','4','0','0',spec['description']+' Visuel uniquement.','0']))
   print(name,len(mesh),'triangles',flush=True)
 catalog=ROOT/'data/equipment.txt';old=catalog.read_text(encoding='utf-8');old='\n'.join(x for x in old.splitlines()if '|r01_'not in x and not x.startswith('# Relais R-01'))
 catalog.write_text(old.rstrip()+'\n# Relais R-01: four core variants per slot, four extra receivers and eight themed modules.\n'+'\n'.join(lines)+'\n',encoding='utf-8')
 report=dict(inputs_sha256=inputs_hash(),name='Relais R-01',version=7,platforms=[dict(id="bottom",name="Atelier / Circuit",rig="r01_rig"),dict(id="side",name="Traverse",rig="r01_rig_side"),dict(id="top",name="Zenith",rig="r01_rig_top")],uv_mapping='isotropic-tiled-v1',styles=styles,skin_families=len(styles),pieces=records,combinations=math.prod(sum(r['slot']==key for r in records)for key in KEYS),texture_source='assets/r01/texture-atlas.png',socket='Bone76',animated_sockets={'feed':'Bone71','chamber':'R01_Bolt'},rig='r01_rig',limits=['MP5 gameplay retained','bottom reload from MP40; side/top authored feed tracks and left-arm IK on the same hands','first-person angled foregrip variants; third-person contacts authored separately'])
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print('Built',len(records),'textured modules and six animated rigs;',sum(x['triangles']for x in records),'triangles across four core sets and two themed selections')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--ensure',action='store_true',help='Rebuild only when atlas/catalog/builder inputs change')
 args=parser.parse_args()
 build(ensure=args.ensure)

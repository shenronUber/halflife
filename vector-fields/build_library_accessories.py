"""Fit extracted textured parts to the existing animated prototype sockets."""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from studio_assets import Studio
import build_modular as base
import build_skins as geo
from build_weapon_visuals import HEADER,box
ROOT=Path(__file__).resolve().parent;LAB=ROOT.parent/'weapon-lab';OUT=ROOT/'generated/library';WORK=OUT/'accessory-build';WORK.mkdir(exist_ok=True)
def main():
 shutil.copy2(ROOT/'generated/weapon_visuals/connector.bmp',WORK/'connector.bmp')
 items=json.loads((LAB/'generated/accessories/manifest.json').read_bytes());rig=Studio(ROOT/'generated/weapon_visuals/mp40_rig.mdl');mounts=[];meshes={}
 for a in items:
  p=LAB/a['mdl'];key='a'+hashlib.sha256(p.read_bytes()).hexdigest()[:16];s=Studio(p);names=s.write_textures(WORK,key);mesh=s.mesh();points=np.array([v['p']for _,vs in mesh for v in vs]);align=np.eye(3)
  if a['kind']=='Optique':
   _,basis=np.linalg.eigh(np.cov(points.T));forward=basis[:,np.argmax(abs(basis[1,:]))];forward*=1 if forward[1]>0 else -1
   right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward);align=np.array([right,forward,up])
  points=points@align.T;lo,hi=points.min(0),points.max(0);size=hi-lo;R=np.diag([-1,-1,1])if a['key']!='acog_mp5'else np.eye(3)
  if a['kind']=='Optique':scale=min(6/max(size[1],.1),2.3/max(size[0],.1),3.2/max(size[2],.1));center=np.array([-1,9,2.3+size[2]*scale/2])
  elif a['kind']=='Bouche':scale=1.45/max(size[0],size[2]);center=np.array([0,31+size[1]*scale/2,2])
  elif a['kind']=='Crosse':scale=9/max(size[1],.1);center=np.array([0,-6-size[1]*scale/2,2-size[2]*scale/2])
  elif a['kind'].startswith('Poign'):scale=4.5/max(size[2],.1);center=np.array([0,16,-.7-size[2]*scale/2])
  else:scale=8/max(size[2],.1);center=np.array([0,4.6,-.5-size[2]*scale/2])
  bone='Bone71'if a['kind']=='Chargeur'else'Bone76';T=np.linalg.inv(rig.bind[rig.names.index(bone)])@rig.bind[rig.names.index('Bone76')]
  tri=[]
  for mat,vs in mesh:
   rows=[]
   for v in vs:
    pos=R@(align@v['p']-(lo+hi)/2)*scale+center;normal=R@align@v['n'];pos=(T@np.r_[pos,1])[:3];normal=T[:3,:3]@normal;rows.append(geo.vertex(pos,normal,v['uv'],0))
   tri.append((names[mat],rows))
  if a['kind']=='Optique':tri+=box([-1.6,6,.4],[-.4,7,2.1])+box([-1.6,11,.4],[-.4,12,2.1])+box([-1.8,5.5,2.1],[-.2,12.5,2.3])
  base.write_smd(WORK/(key+'.smd'),HEADER,geo.smd_tri(tri));(WORK/'idle.smd').write_text('\n'.join(HEADER)+'\n')
  qc=WORK/(key+'.qc');qc.write_text(f'$modelname "{key}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body part "{key}"\n$sequence idle "idle" fps 1\n');mdl=base.compile_model(qc);target=OUT/'models/vf_attach'/mdl.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(mdl,target)
  meshes[a['key']]=key;mounts.append(dict(key=key,original=a['key'],bone=bone,model='models/vf_attach/'+mdl.name,kind=a['kind'],scale=scale))
 # Replace three procedural equipment slots with the imported meshes, preserving 6 family indices.
 choices={'optic':['acog_mp5','aimpoint_m4','eotech_aug','eotech_hk','eotech_cso','holosight_scar'],'muzzle':['suppressor_hk','gemtech_m4']*3,'feed':['mag_m4']*6}
 for slot,keys in choices.items():
  qc=WORK/('eq_'+slot+'.qc');qc.write_text(f'$modelname "eq_{slot}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$bodygroup family\n{{\n'+''.join(' studio "'+meshes[k]+'"\n'for k in keys)+'}\n$sequence idle "idle" fps 1\n');mdl=base.compile_model(qc);target=OUT/'models/vf_equipment'/mdl.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(mdl,target)
 (OUT/'accessory-mounts.json').write_text(json.dumps(mounts,indent=2),encoding='utf-8');print('Mounted pieces',len(mounts),'equipment slots replaced',len(choices))
if __name__=='__main__':main()

"""Global R-01 UV scale and native receiver views, with preserved surfaces."""
import argparse,json,sys,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from library_engine_test import ROOT,MOD,run_cfg
sys.path.insert(0,str(ROOT))
from build_reference_weapon import part,KEYS,Mesh
from studio_assets import Studio

BASELINE=ROOT/'tests/fixtures/r01-surface-before-isotropic-uv.json'
def surface(mesh):
 p=np.array([[v['p']for v in tri]for _,tri in mesh]);cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);areas=np.linalg.norm(cross,axis=1)/2
 return dict(bounds=[p.min((0,1)).tolist(),p.max((0,1)).tolist()],area=float(areas.sum()),centroid=(np.sum(p.mean(1)*areas[:,None],axis=0)/areas.sum()).tolist(),oriented_area=cross.sum(0).tolist())

def assert_surface(current,expected,compiled=False):
 # StudioMDL welds vertices within its 0.01-unit tolerance. Subdivision can
 # change that rounding; require exact bounds and <0.1% area variation.
 for metric in ('bounds','area','centroid','oriented_area'):
  atol=({'bounds':1e-6,'area':.002,'centroid':.001,'oriented_area':.02}[metric]if compiled else 1e-7)
  rtol=.001 if compiled and metric=='area'else 1e-7
  assert np.allclose(current[metric],expected[metric],atol=atol,rtol=rtol),(metric,current[metric],expected[metric])

def mapping():
 baseline=json.loads(BASELINE.read_text());records=[]
 for key in KEYS:
  for variant in range(2):
   name=f'r01_{key}_{"ab"[variant]}';mesh=part(key,variant);ratios=[]
   for material,tri in mesh:
    uv=np.array([v['uv']for v in tri]);p=np.array([v['p']for v in tri])
    assert np.isfinite(uv).all()and uv.min()>=-1e-9 and uv.max()<=1+1e-9,(name,uv)
    if material=='r01_t11.bmp':continue # Existing optical glass window is intentionally preserved.
    # Singular values compare physical distance per UV unit in every direction,
    # including bevels, cylinders, rotated magazine panels and triangle interiors.
    physical=(p[1:]-p[0]).T@np.linalg.inv((uv[1:]-uv[0]).T)
    scales=np.linalg.svd(physical,compute_uv=False);ratio=scales[0]/scales[1]
    assert ratio<1.00001,(name,material,ratio)
    ratios.append(ratio)
   studio=Studio(ROOT/'generated/r01'/(name+'.mdl'))
   for domain,current in [('source',surface(mesh)),('compiled',surface(studio.mesh()))]:
    assert_surface(current,baseline[name][domain],compiled=domain=='compiled')
   assert studio.numskinfamilies==len(json.loads((ROOT/'assets/r01/variants/variants.json').read_text(encoding='utf-8'))['variants'])+1
   assert all(0<w<=256 and 0<h<=256 for _,w,h,_,_ in studio.textures)
   records.append(dict(model=name,triangles=len(mesh),non_glass_triangles=len(ratios),max_anisotropy=max(ratios)))
 # Asymmetric details must not alternate direction, on either side or axis.
 for side in (-1,1):
  for w,h,rotate in [(8,2.8,False),(1.8,9.5,True),(6,1.4,False)]:
   m=Mesh();m.panel(side,0,0,w,h,14,side,rotate)
   for _,tri in m.tris:
    for a in tri:
     for b in tri:
      dy=a['p'][1]-b['p'][1]
      if abs(dy)>.01:assert (a['uv'][1 if rotate else 0]-b['uv'][1 if rotate else 0])*dy*side*(-1 if rotate else 1)>0
 return records

def capture(phase):
 names=[];script='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\n'
 for variant in range(2):
  for style in ((0,4)if phase=='before'else range(len(json.loads((ROOT/'assets/r01/variants/variants.json').read_text(encoding='utf-8'))['variants'])+1)):
   script+=f'vf_reference {variant}\nwait 20\nvf_select_slot 9\nvf_reference_isolate\nvf_animation_time 0\nvf_reference_style {style}\n'
   previous=0
   for angle in (0,2,6):
    script+='vf_rotate\n'*(angle-previous);previous=angle
    name=f'r01_uv_{phase}_{variant}_{style}_{angle}';names.append(name)
    script+='wait 18\nscreenshot scrshots/'+name+'.png\nwait 4\n'
 script+='vf_engine_stats\nquit\n'
 log=run_cfg('vf_r01_uv_'+phase,script,captures=names,timeout=110)
 assert 'rejected=0'in log
 return names

def compare():
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
 image=Image.new('RGB',(1440,970),'#171b20');draw=ImageDraw.Draw(image)
 for row,(style,label)in enumerate([(0,'Original'),(4,'Jungle')]):
  for col,phase in enumerate(('before','after')):
   src=Image.open(MOD/'scrshots'/f'r01_uv_{phase}_0_{style}_2.png').convert('RGB').crop((490,305,1210,726))
   draw.text((col*720+12,row*485+12),label+' - '+('Avant'if col==0 else'Apres : proportions corrigees'),font=font,fill='#f1eee6')
   image.paste(src,(col*720,row*485+54))
 image.save(ROOT/'build/r01-receiver-uv-comparison.jpg',quality=96,subsampling=0)

def run(before=False):
 if before:
  print('Captured before:',len(capture('before')));return
 records=mapping();names=capture('after');compare()
 report=dict(mapping='isotropic-tiled-v1',models=records,captures=names,checks=['identical scale along both UV axes for every non-glass source triangle','source surfaces identical; compiled bounds identical and area within 0.1 percent StudioMDL welding tolerance','UV cells stay within 0..1 and texture dimensions within 256x256','asymmetric motif orientation consistent on both sides including rotated vertical panels','both receiver variants, all installed styles, three native camera angles'],exception='Existing glass UV window preserved')
 (ROOT/'build/r01-global-uv-verification.json').write_text(json.dumps(report,indent=2))
 print('PASS global UV:',len(records),'models;',sum(r['non_glass_triangles']for r in records),'isotropic source triangles;',len(names),'native receiver views')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--before',action='store_true');run(parser.parse_args().before)

"""Breech UV mapping: near-square repetition, no mirrored asymmetric motifs."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from library_engine_test import ROOT,MOD,run_cfg
sys.path.insert(0,str(ROOT))
from build_reference_weapon import Mesh,part
from r01_styles_engine_test import assets

def mapping():
 for variant in range(2):
  faces=[triangle for material,triangle in part('chamber',variant)if material=='r01_t15.bmp']
  assert len(faces)==8
  ranges=set()
  for triangle in faces:
   y=np.array([v['p'][1]for v in triangle]);z=np.array([v['p'][2]for v in triangle])
   ranges.add((round(float(y.min()),5),round(float(y.max()),5)))
   assert .9<(y.max()-y.min())/(z.max()-z.min())<1.1
   for a in triangle:
    assert (a['uv']>=0).all()and(a['uv']<=1).all()
    for b in triangle:
     dy=a['p'][1]-b['p'][1]
     if abs(dy)>.01:assert (a['uv'][0]-b['uv'][0])*dy>0
  assert len(ranges)==4
 # Readable orientation from either visible side; no ping-pong mirror tiling.
 for side in (-1,1):
  mesh=Mesh();mesh.panel(side,5,.6,6,1.4,15,side=side,repeat=0)
  for _,triangle in mesh.tris:
   for a in triangle:
    for b in triangle:
     dy=a['p'][1]-b['p'][1]
     if abs(dy)>.01:assert (a['uv'][0]-b['uv'][0])*dy*side>0

def run():
 mapping();assets()
 captures=[]
 def snap(name):
  name='r01_breech_'+name;captures.append(name)
  return 'wait 15\nscreenshot scrshots/'+name+'.png\nwait 4\n'
 script='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\nvf_reference 0\nwait 35\nvf_select_slot 13\nvf_reference_isolate\nvf_animation_time 0\n'
 for variant in range(2):
  if variant:script+='vf_reference 1\nwait 20\nvf_reference_isolate\nvf_select_slot 13\nvf_animation_time 0\n'
  for style in range(7):
   script+=f'vf_reference_style {style}\n'+snap(f'{variant}_{style}')
 script+='vf_engine_stats\nquit\n'
 log=run_cfg('vf_r01_breech_validation',script,captures=captures,timeout=80)
 assert 'rejected=0'in log
 before=Image.open(MOD/'scrshots/r01_part_13_a.png').convert('RGB').crop((490,305,1210,726))
 after=Image.open(MOD/'scrshots/r01_breech_0_0.png').convert('RGB').crop((490,305,1210,726))
 comparison=Image.new('RGB',(1440,480),'#171b20');draw=ImageDraw.Draw(comparison)
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
 for x,label,image in [(0,'Avant : une texture etiree sur la longueur',before),
                       (720,'Apres : quatre repetitions sans miroir',after)]:
  draw.text((x+12,10),label,fill='#f1eee6',font=font);comparison.paste(image,(x,55))
 comparison.save(ROOT/'build/r01-breech-uv-comparison.jpg',quality=95,subsampling=0)
 report=dict(cells=4,old_aspect=6/1.4,new_aspect=1.5/1.4,new_texture_anisotropy=1.0,
             variants=2,styles=7,captures=captures,checks=[
             'four near-square copies fill the same coplanar breech surface',
             'no UV coordinates outside the native 0..1 range',
             'every repeated cell preserves asymmetric pattern direction',
             'side-aware visible orientation verified on both face directions',
             'all fourteen shape/style combinations rendered in the real engine'])
 (ROOT/'build/r01-breech-uv-verification.json').write_text(json.dumps(report,indent=2))
 print('PASS breech UV:',len(captures),'native views; four repeats; no mirrored cells.')
if __name__=='__main__':run()

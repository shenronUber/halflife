"""R-01 skin families: real renderer, geometry reuse, atomic validation and saves."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from library_engine_test import run_cfg,click,ROOT,MOD
sys.path.insert(0,str(ROOT))
from studio_assets import Studio

def fingerprint(path):
 value=2166136261
 for b in path.read_bytes():value=((value^b)*16777619)&0xffffffff
 return value

def geometry_digest(studio,skin):
 h=hashlib.sha256()
 mesh=studio.mesh(skin=skin)
 for _,tri in mesh:
  for v in tri:
   for key in ('p','n','uv'):h.update(v[key].tobytes())
   h.update(bytes([v['b']]))
 return h.hexdigest()

def assets():
 data=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))
 from r01_uv_mapping_test import surface,BASELINE,assert_surface
 before=json.loads(BASELINE.read_text())
 assert data['uv_mapping']=='isotropic-tiled-v1'
 assert data['skin_families']==len(data['styles']) and len(data['pieces'])==26
 total=0
 for record in data['pieces']:
  s=Studio(ROOT/'generated/r01'/(record['id']+'.mdl'))
  assert s.numskinfamilies==data['skin_families'] and len(s.textures)<=100
  assert len(s.mesh())==record['triangles']
  original=geometry_digest(s,0)
  current=surface(s.mesh())
  if record['id']in before:assert_surface(current,before[record['id']]['compiled'],compiled=True)
  for family in range(data['skin_families']):
   assert geometry_digest(s,family)==original,(record['id'],family)
   table=s.skin[family*s.numskinref:(family+1)*s.numskinref]
   assert all(0<=i<len(s.textures)for i in table)
   if family:assert table!=s.skin[:s.numskinref]
   total+=1
 return data,total

def run():
 manifest,checked=assets();families=manifest['skin_families'];last=families-1
 captures=[]
 def snap(name):
  name='r01_style_'+name;captures.append(name)
  return f'wait 18\nscreenshot scrshots/{name}.png\nwait 4\n'
 script='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\n+forward\nwait 25\n-forward\nvf_reference 0\nwait 35\nvf_animation_time 0\n'
 script+=snap('preview_0')+'vf_commit\nwait 25\n'+click(1220,40)+snap('hand_0')+'vf_reference\nwait 25\nvf_animation_time 0\nvf_engine_stats\n'
 for style in range(1,families):
  # Actual mouse route: the right arrow of the finish chooser.
  script+=click(1232,386)+snap(f'preview_{style}')+click(1120,690)+'wait 25\n'
  script+=click(1220,40)+snap(f'hand_{style}')+'vf_reference\nwait 25\nvf_animation_time 0\n'
 script+='vf_engine_stats\nvf_visual_bench r01_styles\nwait 215\n'
 # Per-part scope selected with the actual UI, keeping the other eleven choices.
 script+='vf_select_slot 16\n'+click(1150,424)+click(1232,386)+'wait 10\n'
 # At the last style, one step wraps only this optic back to original.
 script+='vf_reference_style 4 16\nvf_reference_style 3 12\n'+snap('mixed_preview')+click(1120,690)+'wait 25\n'
 script+='vf_reference_style 1\n'+click(970,690)+snap('cancel_restored')
 rows=[line.split('|')for line in (ROOT/'data/equipment.txt').read_text().splitlines()if line and not line.startswith(('#','limits'))]
 slots=['head','shoulders','gloves','torso','belt','legs','boots','shield','special','receiver','barrel','muzzle','feed','chamber','ammo','projectile','optic','underbarrel','grip','power','cooling']
 # Reuse current applied character defaults from the normal minimum-cost catalog rule.
 # For invalid-style transactions, zero character items are legal and still must NOT commit.
 items=[0]*9+[next(i+1 for i,r in enumerate(rows)if r[1]==f'r01_{slot}_a')for slot in slots[9:]]
 items[9]=next(i+1 for i,r in enumerate(rows)if r[1]=='r01_receiver_b')
 styles=[last]*12;styles[7]=4;styles[3]=99
 equipHash=fingerprint(ROOT/'data/equipment.txt');styleHash=fingerprint(ROOT/'data/r01_styles.txt')
 script+='echo R01_INVALID_STYLE\ncmd vf_apply '+str(equipHash)+' '+' '.join(map(str,items))+' '+str(styleHash)+' '+' '.join(map(str,styles))+'\nwait 25\n'
 styles[3]=3
 script+='echo R01_STALE_STYLES\ncmd vf_apply '+str(equipHash)+' '+' '.join(map(str,items))+' '+str(styleHash^1)+' '+' '.join(map(str,styles))+'\nwait 25\n'
 script+=snap('after_rejections')+click(1220,40)+'+attack\nwait 20\n-attack\nwait 30\n+reload\nwait 50\n'+snap('mixed_reload')+'-reload\nwait 100\nsave vf_r01_styles\nwait 50\nload vf_r01_styles\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_reference\nwait 35\nvf_animation_time 0\n'+snap('after_load')+'vf_engine_stats\nquit\n'
 log=run_cfg('vf_r01_styles_validation',script,captures=captures,timeout=150)
 for style in range(1,families):
  assert f'VFR01 styles accepted: player=1 first={style} optic={style} feed={style}'in log,style
 assert 'VFUI click: Cette piece'in log
 assert 'VFR01 draft style: id=0 slot=16'in log,'Per-part arrow must preserve global styles.'
 assert 'VFUI click: Annuler'in log
 assert f'VFR01 styles accepted: player=1 first={last} optic=4 feed=3'in log
 invalid=log.split('R01_INVALID_STYLE')[-1].split('R01_STALE_STYLES')[0]
 assert 'VFBuild received: result=2'in invalid and 'receiver=r01_receiver_a'in invalid
 stale=log.split('R01_STALE_STYLES')[-1].split('save vf_r01_styles')[0]
 assert 'VFBuild received: result=1'in stale and 'receiver=r01_receiver_a'in stale
 after=log.split('Loading game from save/vf_r01_styles.sav')[-1]
 assert f'VFR01 state: player=1 first={last} optic=4 feed=3'in after
 assert 'rejected=0'in log and 'VFState rejected'not in log
 benches=__import__('re').findall(r'VFBench r01_styles:.*?loads=(\d+)',log)
 assert benches==['0'],benches
 def viewport(name):
  return Image.open(MOD/'scrshots'/f'r01_style_{name}.png').convert('RGB').crop((490,305,1210,726))
 changed={}
 original=viewport('preview_0')
 for style in range(1,families):
  count=sum(max(px)>20 for px in ImageChops.difference(original,viewport(f'preview_{style}')).getdata())
  assert count>1000,(style,count);changed[style]=count
 assert ImageChops.difference(viewport('mixed_preview'),viewport('cancel_restored')).getbbox()is None
 assert ImageChops.difference(viewport('mixed_preview'),viewport('after_rejections')).getbbox()is None
 collage=Image.new('RGB',(2160,485*((families+3)//3)),'#171b20');draw=ImageDraw.Draw(collage)
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
 names=['Original']+[s['title']for s in manifest['styles'][1:]]+['Melange : optique jungle / chargeur en os']
 images=[f'preview_{i}'for i in range(families)]+['mixed_preview']
 for i,(name,image)in enumerate(zip(names,images)):
  x=(i%3)*720;y=(i//3)*485
  draw.text((x+10,y+10),name,fill='#f1eee6',font=font)
  collage.paste(viewport(image),(x,y+54))
 collage.save(ROOT/'build/r01-styles-in-game.jpg',quality=94,subsampling=0)
 report=dict(meshes=len(manifest['pieces']),skin_families=families,mesh_family_checks=checked,geometry_reused=True,
             changed_pixels=changed,captures=captures,checks=[
             '24 model surfaces match their pre-UV baseline; the new UV cells preserve the optical window; all installed families share each geometry',
             'all native skin families per module',
             'real UI global cycling, per-part scope, Apply and Cancel',
             'invalid style and stale catalog reject the complete equipment transaction',
             'mixed optic/feed styles survive save and load',
             'first-person styles, shooting and reload rendered',
             'native preview model-load count remains zero during warm switching'])
 (ROOT/'build/r01-styles-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS R01 styles:',len(captures),'1080p captures;',checked,'geometry/skin-family checks')
if __name__=='__main__':run()

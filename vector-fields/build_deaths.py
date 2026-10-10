"""GIGN death bodygroups and electrical contraction; living 77 sequences unchanged."""
import argparse,collections,copy,json,math,re,shutil
import death_atlas
import fragment_skins
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
import build_personas as personas
import build_skins as geometry
from build_modular import write_smd,compile_model
from studio_assets import Studio,canonical
from animation_assets import sequence_frames
import build_cache
import death_wounds as wounds
import external_death_animations as external
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/deaths'
GROUPS=['head','torso','left_sleeve','right_sleeve','left_hand','right_hand','left_leg','right_leg','left_boot','right_boot','pelvis']
REGIONS=[1,0,2,4,2,4,8,16,8,16,0];ZONES=[0,1,1,1,2,2,3,3,4,4,3]
def region(tri,names):
 votes=[]
 for v in tri:
  n=canonical(names[v['b']]);votes.append(1 if n in ('head','neck') else 2 if n.startswith(('l arm1','l arm2','l hand','l finger')) else 4 if n.startswith(('r arm1','r arm2','r hand','r finger')) else 8 if n.startswith(('l leg','l foot')) else 16 if n.startswith(('r leg','r foot')) else 0)
 return collections.Counter(votes).most_common(1)[0][0]
def boundary(triangles):
 edges=collections.defaultdict(list)
 for _,tri in triangles:
  for a,b in zip(tri,tri[1:]+tri[:1]):
   key=tuple(sorted((tuple(np.round(a['p'],5)),tuple(np.round(b['p'],5)))))
   if key[0]!=key[1]:edges[key].append((a,b))
 return [e[0] for e in edges.values() if len(e)==1]
def electrical(model,header):
 fall=sequence_frames(model,'die_simple');frames=[]
 for i in range(19):
  pose=fall[0].copy();envelope=math.sin(math.pi*i/19)**.5
  for bone,amp in [(9,.09),(10,-.14),(11,.12),(12,.16),(15,.22),(16,-.28),(22,-.22),(23,.28),(3,.06),(6,-.06)]:
   twitch=amp*envelope*math.sin(i*2.15+bone*.6);pose[bone,:3,:3]=pose[bone,:3,:3]@Rotation.from_euler('xyz',[twitch,twitch*.4,0]).as_matrix()
  pose[0,2,3]+=envelope*.6;frames.append(pose)
 frames+=list(fall);rows=header[:header.index('skeleton')]+['skeleton']
 for frame,pose in enumerate(frames):
  pose=pose.copy();undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',-90,degrees=True).as_matrix();pose[0]=undo@pose[0]
  rows.append('time '+str(frame))
  for bone,m in enumerate(pose):
   values=[*m[:3,3],*Rotation.from_matrix(m[:3,:3]).as_euler('xyz')];rows.append(str(bone)+' '+' '.join(f'{v:.8f}' for v in values))
 rows.append('end');(OUT/'vf_electro.smd').write_text('\n'.join(rows)+'\n');return len(frames)
def build(ensure=False):
 inputs=[Path(__file__),ROOT/'death_wounds.py',ROOT/'fragment_skins.py',ROOT/'external_death_animations.py',ROOT/'death_atlas.py',death_atlas.DATA,*sorted(external.ASSETS.glob('*.gl*')),*sorted(external.ASSETS.glob('*.bin')),*sorted(wounds.ASSETS.glob('*-source.png')),personas.ASSETS/'personas.json',*[ROOT/n for n in ('build_personas.py','build_skins.py','build_modular.py','studio_assets.py','animation_assets.py','build_cache.py')],ROOT.parent/'game_shared/vf_death_visual.h',personas.OUT/'persona_rig.mdl',personas.OUT/'persona_rig.qc']+sorted(personas.OUT.glob('*.smd'))+sorted(personas.OUT.glob('*.bmp'))
 digest=build_cache.fingerprint(inputs+build_cache.compiler_inputs());manifest=OUT/'manifest.json'
 if ensure and manifest.exists() and build_cache.current(json.loads(manifest.read_text()).get('build_cache'),digest):return json.loads(manifest.read_text())
 OUT.mkdir(parents=True,exist_ok=True)
 for source in personas.OUT.iterdir():
  if source.suffix in ('.bmp','.smd'):shutil.copy2(source,OUT/source.name)
 texture_records=wounds.textures(OUT);legacy=OUT/'death_flesh.bmp'
 if legacy.exists():legacy.unlink()
 config=json.loads((personas.ASSETS/'personas.json').read_text());model=Studio(personas.OUT/'persona_rig.mdl');header,*_=personas.fitted_skeleton(Studio(personas.donor(config)['path']))
 zones,_=personas.tailored_mesh(config);groups,planes,accessories=wounds.segment(zones,model)
 wounds.align_collar(groups)
 stumps=[];gibs=[];gibmeta=[];whole=[];wholemeta=[];woundmeta=[]
 atlas=death_atlas.generate()
 for r,label,family,bone in wounds.REGIONS:
  limb=[t for i,g in enumerate(groups) if REGIONS[i]==r for t in g];kept=[t for i,g in enumerate(groups) if REGIONS[i]!=r for t in g]
  removed_keys={wounds.edge_key(a,b) for a,b in boundary(limb)};edges=[(a,b) for a,b in boundary(kept) if wounds.edge_key(a,b) in removed_keys]
  material='death_'+label+'.bmp';stump,charts=wounds.cap(edges,bone,material,planes[r]['n']);assert stump and len(charts)==1,(label,charts)
  stumps.append(stump);woundmeta.append(dict(region=r,label=label,family=family,bone=bone,charts=charts))
  fragment_limb=[(fragment_skins.DETAIL_MATERIAL if ZONES[i] in (2,4) else mat,tri) for i,g in enumerate(groups) if REGIONS[i]==r for mat,tri in g]
  intact=copy.deepcopy(fragment_limb);closing,limb_charts=wounds.cap(boundary(intact),bone,material);intact+=closing;center=np.mean([v['p'] for _,t in intact for v in t],axis=0)
  for _,tri in intact:
   for v in tri:v['p']=v['p']-center;v['b']=0
  points=np.array([v['p'] for _,tri in intact for v in tri]);pitch=90 if r in (1,8,16) else 0;rest=points@Rotation.from_euler('y',-pitch,degrees=True).as_matrix().T
  whole.append(intact);wholemeta.append(dict(region=r,kind='whole',center=center.tolist(),triangles=len(intact),wound_charts=limb_charts,rest_pitch=pitch,floor_offset=float(-rest[:,2].min()+.1)))
  coordinates=np.array([v['p'] for _,t in limb for v in t]);axis=2 if r in (1,8,16) else 0;cuts=np.quantile(coordinates[:,axis],[1/3,2/3])
  for chunk in range(3):
   piece=[]
   for mat,tri in fragment_limb:
    poly=tri
    if chunk:poly=geometry.clip(poly,dict(c=np.eye(3)[axis]*cuts[chunk-1],n=np.eye(3)[axis],bone=bone),True)
    if chunk<2:poly=geometry.clip(poly,dict(c=np.eye(3)[axis]*cuts[chunk],n=np.eye(3)[axis],bone=bone),False)
    piece+=geometry.fan(mat,poly)
   assert piece,(r,chunk);closing,fragment_charts=wounds.cap(boundary(piece),bone,material);piece+=closing;center=np.mean([v['p'] for _,t in piece for v in t],axis=0)
   for _,tri in piece:
    for v in tri:v['p']=v['p']-center;v['b']=0
   gibs.append(piece);gibmeta.append(dict(region=r,chunk=chunk,center=center.tolist(),triangles=len(piece),wound_charts=fragment_charts))
 gibs+=whole;gibmeta+=wholemeta
 qc=(personas.OUT/'persona_rig.qc').read_text().replace('persona_rig.mdl','persona_death.mdl');qc=re.sub(r'^\$body\s+.*$','',qc,flags=re.M)
 qc+='\n$body rig "persona_anchors"\n'
 for i,triangles in enumerate(groups+stumps):
  name=GROUPS[i] if i<len(GROUPS) else 'wound_'+str(i-len(GROUPS));write_smd(OUT/(name+'.smd'),header,geometry.smd_tri(triangles));qc+=f'\n$bodygroup {name}\n{{\n blank\n studio "{name}"\n}}\n'
 catalog=ROOT.parent/'game_shared/vf_wound_catalog.h'
 rows=['// Generated from measured GIGN cut boundaries by build_deaths.py.', '#ifndef VF_WOUND_CATALOG_H', '#define VF_WOUND_CATALOG_H', 'namespace vfwound {', 'struct Cut { int bone; float offset[3], normal[3]; };', 'static const Cut Cuts[]={']
 for info in woundmeta:
  local=(np.linalg.inv(model.bind[info['bone']])@np.r_[info['charts'][0]['center'],1])[:3];info['bone_offset']=local.tolist();normal=np.linalg.inv(model.bind[info['bone']][:3,:3])@planes[info['region']]['n'];info['bone_normal']=normal.tolist()
  rows.append('{'+str(info['bone'])+',{'+','.join(f'{v:.8f}f' for v in local)+'},{'+','.join(f'{v:.8f}f' for v in normal)+'}}, // '+info['label'])
 rows+=['};','}','#endif'];catalog.write_text('\n'.join(rows)+'\n')
 # Reset the compiler's rotation state after body/attachment declarations.
 imported=external.export(model,header,OUT)
 frames=electrical(model,header);qc+='\n$sequence vf_electro "vf_electro" fps 22 rotate 0\n';mats=['persona_original.bmp']+['persona_'+t['key']+'.bmp' for t in config['themes']]
 fixed=' '.join('"'+t['material']+'"' for t in texture_records)
 for clip in imported:qc+=f'\n$sequence {clip["id"]} "{clip["id"]}" fps {clip["fps"]:.8f} rotate 0\n'
 textures='\n$texturegroup personas\n{\n'+''.join('{ "'+m+'" '+fixed+' }\n' for m in mats)+'}\n';qc+=textures
 (OUT/'persona_death.qc').write_text(qc);compiled=compile_model(OUT/'persona_death.qc');wounds.shade_materials(compiled)
 gh=['version 1','nodes','0 "fragment" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end']
 for i,piece in enumerate(gibs):write_smd(OUT/f'fragment_{i}.smd',gh,geometry.smd_tri(piece))
 write_smd(OUT/'fragment_idle.smd',gh,[])
 details=[m.replace('persona_','fragment_detail_',1) for m in mats]
 for source,target in zip(mats,details):shutil.copy2(OUT/source,OUT/target)
 fragment_textures='\n$texturegroup fragments\n{\n'+''.join('{ "'+primary+'" "'+detail+'" '+fixed+' }\n' for primary,detail in zip(mats,details))+'}\n'
 gq='$modelname "persona_death_gibs.mdl"\n$cd "."\n$cdtexture "."\n$bodygroup fragment\n{\n'+''.join(f'studio "fragment_{i}"\n' for i in range(len(gibs)))+'}\n$sequence idle "fragment_idle" fps 1\n'+fragment_textures
 (OUT/'persona_death_gibs.qc').write_text(gq,encoding='utf-8');fragment_model=compile_model(OUT/'persona_death_gibs.qc');wounds.shade_materials(fragment_model);fragment_skins.expand_file(fragment_model);built=Studio(compiled)
 assert built.sequences[:77]==model.sequences and built.sequences[77]=='vf_electro';assert len(built.parts)==len(GROUPS)+6 and built.numskinfamilies==14
 tracks=ROOT.parent/'game_shared/vf_death_tracks.h';external.effect_tracks(built,tracks)
 fragment_catalog=ROOT.parent/'game_shared/vf_fragment_geometry.h';fragment_catalog.write_text('// Generated from the five rigid anatomical meshes.\n#ifndef VF_FRAGMENT_GEOMETRY_H\n#define VF_FRAGMENT_GEOMETRY_H\nnamespace vfdeath { struct FragmentRest {float pitch,floorOffset;};static const FragmentRest FragmentPoses[]={\n'+''.join('{'+str(m['rest_pitch'])+'.f,'+str(round(m['floor_offset'],6))+'f},\n' for m in wholemeta)+'};}\n#endif\n')
 gibmodel=Studio(OUT/'persona_death_gibs.mdl')
 for record in texture_records:
  record['compiled_pixels']={}
  for key,mdl in [('corpse',built),('fragments',gibmodel)]:
   texture=next(t for t in mdl.textures if t[0]==record['material']);record['compiled_pixels'][key]=list(texture[1:3])
 report=dict(schema=6,fragment_skin_pairs=fragment_skins.skin_pairs(),death_atlas=atlas,imported_animations=imported,retained_accessory_triangles=accessories,cut_planes={str(r):{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in plane.items()} for r,plane in planes.items()},original_triangles=sum(map(len,zones)),wounds=woundmeta,wound_textures=texture_records,clothing_groups=len(GROUPS),bodygroups=GROUPS+['wound_head','wound_left_arm','wound_right_arm','wound_left_leg','wound_right_leg'],regions=REGIONS+[1,2,4,8,16],zones=ZONES+[1,1,1,3,3],fragments=gibmeta,sequence='vf_electro',electrical_frames=frames,electrical_seconds=(frames-1)/22,existing_sequences_preserved=77,skin_families=14,triangles=[len(t) for t in groups+stumps],inputs_sha256=digest)
 report['build_cache']=build_cache.record(digest,[catalog,tracks,fragment_catalog,ROOT.parent/'game_shared/vf_death_atlas.h',ROOT.parent/'game_shared/vf_death_motion.h']+[p for p in OUT.iterdir() if p.suffix in ('.mdl','.qc','.smd','.bmp')]);build_cache.write(manifest,report);print('Built anatomical deaths',json.dumps({k:v for k,v in report.items() if k not in ('build_cache','fragments','wounds','wound_textures')}));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)

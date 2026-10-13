"""Compare actual rendered and authoritative hitbox matrices in controlled live poses."""
import argparse,hashlib,itertools,json,re,shutil,struct,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import third_person_native_test as harness
import death_sounds_test as audio
from build_traversal_range import build
from studio_assets import Studio
from native_workspace import private_copy
OUT=ROOT/'build/player-pose'

def run(candidate=None,only=None,extended=False,melee_phases=False):
 candidate=Path(candidate) if candidate else None
 engine=harness.stage('player-pose',server=candidate/'server/hl.dll' if candidate else None,client=candidate/'client/client.dll' if candidate else None,renderer=candidate/'engine' if candidate else None)
 mod=engine/'vf_animation';OUT.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT.parent/'network/delta.lst',mod/'delta.lst');private_copy(build(ensure=True),mod/'maps/vf_traversal.bsp')
 lines=['wait 180','developer 1','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667','sv_cheats 1','god','map vf_traversal','wait 150','cmd give weapon_9mmAR','weapon_9mmAR','wait 30','vf_reference 0','wait 25','vf_commit','wait 25','vf_character','vf_character','wait 15','cam_snapto 1','cam_idealdist 100','cam_idealyaw 120','cam_idealpitch 12','cam_command 1']
 cases=[]
 def sample(name,commands,phase=0):
  if only and name!=only:return
  lines.extend(['developer 0','host_framerate .016666667','-duck','-jump','-forward','-back','-moveleft','-moveright','-attack','-attack2','-reload','wait 20'])
  lines.extend(commands)
  lines.extend(['host_framerate .0000001','wait 5','developer 3',f'echo POSE_BEGIN_{name}','cmd vf_hitbox_info','wait 2','cmd vf_hitbox_probe','wait 2',f'screenshot scrshots/pose_{name}.png','wait 3',f'echo POSE_END_{name}','developer 0'])
  cases.append(dict(name=name,phase=phase))
 def place(yaw=0,pitch=0):return [f'cmd vf_traversal_place 128 -750 36 {yaw}','wait 3',f'vf_traversal_look {yaw} {pitch}','wait 5']
 for yaw in (0,90,180,270):sample(f'idle_{yaw}',place(yaw))
 for pitch in (-60,0,60):sample(f'crouch_{pitch}',place(45,pitch)+['+duck','wait 22'])
 for yaw in (0,45,90,135,180,225,270,315):sample(f'strafe_{yaw}',place(yaw,20)+['+moveleft','wait 16'])
 sample('reload',place()+['+attack','wait 7','-attack','wait 10','+reload','wait 2','-reload','wait 22'])
 sample('crouch_reload',place(90,-30)+['+duck','wait 20','+attack','wait 7','-attack','wait 10','+reload','wait 2','-reload','wait 22'])
 for yaw in (0,90,180):sample(f'slide_{yaw}',[f'cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1',f'vf_traversal_look {yaw} 25','+duck','wait 12'],5)
 hang=['cmd vf_traversal_place 238 0 54 0','wait 1','vf_traversal_look 0 0','+jump','wait 22','-jump','wait 12']
 sample('hang',hang,2)
 for yaw in (0,45,90,135,180,225,270,315):sample(f'armed_{yaw}',hang+['+attack2','wait 2','-attack2','wait 22',f'vf_traversal_look {yaw} 35','wait 12'],3)
 for label,point in [('vault','-28 0 36'),('stepup','996 -450 36')]:
  sample(label,[f'cmd vf_traversal_place {point} 0','wait 2','vf_traversal_look 0 0','+forward','+jump','wait 1','-forward','-jump','wait 13'],1)
 for helmet in ('helmet_riot','helmet_gas_mask'):
  sample(helmet,place()+['vf_operator','wait 10',f'vf_item {helmet}','vf_commit','wait 15','vf_operator','wait 5','vf_headgear_toggle','wait 32'])
 if extended:
  for side,y in [('right',-1006),('left',1006)]:
   sample('wallrun_'+side,[f'cmd vf_traversal_place 0 {y} 128 0 320 0 0',f'vf_traversal_look {300 if y<0 else 60} 0','+forward','+jump','wait 3','-jump','vf_traversal_look 0 0','wait 9'],8)
   for yaw,pitch in [(90,-85),(270,85),(359.9,0)]:
    sample(f'wallrun_{side}_look_{yaw}',[f'cmd vf_traversal_place 0 {y} 128 0 320 0 0',
           f'vf_traversal_look {300 if y<0 else 60} 0','+forward','+jump','wait 3','-jump',
           f'vf_traversal_look {yaw} {pitch}','wait 9'],8)
  for mode in ['back','turn']:
   jump=['cmd vf_traversal_place 238 -500 54 0','wait 2','vf_traversal_look 0 0','+jump','wait 22','-jump','wait 20']
   jump+=['vf_traversal_look 180 0','wait 8'] if mode=='turn' else ['+back']
   sample('walljump_'+mode,jump+['+jump','wait 4'],7)
  # Body turns in flight even when the look direction changes after S+jump.
  # These samples compare the same evolving pose on render and collision.
  for yaw in [90,180,270]:
   jump=['cmd vf_traversal_place 238 -500 54 0','wait 2','vf_traversal_look 0 0','+jump','wait 22','-jump','wait 20','+back','+jump','wait 4','-back',f'vf_traversal_look {yaw} 0','wait 9']
   sample('walljump_flight_'+str(yaw),jump,7)
  for platform,receiver in [('bottom','a47'),('side','side'),('top','top')]:
   for crouch in [False,True]:
    commands=place(45,10)+['vf_reference','wait 20',f'vf_item r01_receiver_{receiver}__original','vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15']
    if crouch:commands+=['+duck','wait 22']
    name='melee_'+platform+('_crouch' if crouch else '_stand')
    sample(name,commands+['vf_melee','wait 30'])
    if melee_phases:
     for phase,frames in [('raise',16),('contact',24),('follow',30)]:
      sample(name+'_'+phase,commands+['vf_melee',f'wait {frames}'])
 lines+=['vf_sv_pose_info','quit']
 for part,start in enumerate(range(0,len(lines),70)):
  chunk=lines[start:start+70]
  if start+70<len(lines):chunk.append(f'exec player_pose_{part+1}.cfg')
  (mod/f'player_pose_{part}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
 started=time.monotonic();log=audio.launch(engine,'player_pose_0.cfg','player-pose.log');(OUT/'native.log').write_text(log,encoding='utf-8')
 for error in ['Host_Error','SV_Error','not precached','VFState rejected','Could not load']:assert error not in log,error
 pattern=r'VFPlayerPose source=(server|render) entity=(\d+) sequence=(\d+) frame=([\d.]+) time=([\d.]+) sample=([\d.]+) gait=(\d+) yaw=([-\d.]+) phase=(\d+) box=(\d+) matrix=([-\d.,]+)'
 data=(mod/'models/vf_r01/r01_tp.mdl').read_bytes();count,offset=struct.unpack_from('<ii',data,156);assert count==20
 corners=[]
 for box in range(count):
  _,_,*bounds=struct.unpack_from('<ii6f',data,offset+box*32)
  corners.append(np.array([(*point,1) for point in itertools.product(*zip(bounds[:3],bounds[3:]))]).T)
 results=[]
 for case in cases:
  name=case['name'];part=log.split('POSE_BEGIN_'+name+' ')[1].split('POSE_END_'+name+' ')[0]
  if name.startswith('melee_'):
   mount=name.split('_')[1];suffix={'bottom':'','side':'_side','top':'_top'}[mount]
   expected_model='models/vf_melee/r01_tp'+suffix+'.mdl'
   assert 'source=server model='+expected_model+' ' in part,(name,'wrong actual carrier')
   assert 'source=render model='+expected_model+' ' in part,(name,'wrong visible carrier')
  rows=[dict(source=r[0],entity=int(r[1]),sequence=int(r[2]),frame=float(r[3]),time=float(r[4]),sample=float(r[5]),gait=int(r[6]),yaw=float(r[7]),phase=int(r[8]),box=int(r[9]),matrix=np.array(list(map(float,r[10].split(',')))).reshape(3,4)) for r in re.findall(pattern,part)]
  server=[r for r in rows if r['source']=='server' and r['entity']==1];render=[r for r in rows if r['source']=='render' and r['entity']==1]
  assert server and render,(name,len(server),len(render),part[-2500:])
  assert any(r['phase']==case['phase'] for r in render),(name,{r['phase'] for r in render})
  # Compare all 20 real hitbox transformations, allowing the packet's sub-frame
  # and millisecond quantization. Studio animation time is held only during QA.
  errors=[];corner_errors=[]
  for box in range(20):
   candidates=[(a,b) for a in server for b in render if a['box']==b['box']==box and a['sequence']==b['sequence'] and abs(a['time']-b['time'])<.005]
   assert candidates,(name,box)
   error=min(float(np.max(np.abs(a['matrix']-b['matrix']))) for a,b in candidates)
   assert error<.35,(name,box,error)
   corner_error=min(float(np.max(np.linalg.norm((a['matrix']-b['matrix'])@corners[box],axis=0))) for a,b in candidates)
   assert corner_error<.35,(name,box,'world-space hitbox corners',corner_error)
   errors.append(error)
   corner_errors.append(corner_error)
  assert re.search(r'VFHitboxProbe .*found=1',part),(name,'real left-hand ray missed')
  result=dict(name=name,boxes=20,phase=case['phase'],maximum_matrix_error=max(errors),maximum_corner_error_units=max(corner_errors))
  if melee_phases and name.startswith('melee_') and name.rsplit('_',1)[-1] in ['raise','contact','follow']:
   expected={'raise':9,'contact':13,'follow':16}[name.rsplit('_',1)[-1]]
   authored=min(server,key=lambda r:abs(r['frame']/256*33-expected))['frame']/256*33
   # A 60 Hz server samples a 30 FPS clip in half-frame steps. Packet
   # millisecond quantization adds a small margin around the keyed instant.
   assert abs(authored-expected)<.55,(name,'wrong part of gesture',authored)
   result['authored_frame']=authored
  results.append(result)
  if name in ('crouch_0','slide_90','armed_180','vault','helmet_gas_mask','wallrun_right','walljump_back','melee_bottom_stand','melee_top_crouch') or melee_phases and name.startswith('melee_'):
   shutil.copy2(mod/'scrshots'/f'pose_{name}.png',OUT/f'{name}.png')
 report=dict(passed=True,seconds=round(time.monotonic()-started,2),poses=results,boxes_compared=20*len(results),maximum_matrix_error=max(r['maximum_matrix_error']for r in results),maximum_corner_error_units=max(r['maximum_corner_error_units']for r in results),engine_sha256=hashlib.sha256((engine/'xash.dll').read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest(),server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),melee_assets={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(mod/'models/vf_melee').glob('*.mdl')}if extended else {},limits=['Controlled pose/millisecond quantization; this does not measure network latency or lag compensation.'])
 (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS shared player pose',json.dumps(report),flush=True);return report
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--candidate-dir',type=Path);parser.add_argument('--only');parser.add_argument('--extended',action='store_true');parser.add_argument('--melee-phases',action='store_true');args=parser.parse_args();run(args.candidate_dir,args.only,args.extended or args.melee_phases,args.melee_phases)

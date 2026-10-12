"""Private native build: movement, ordinary gun tracks, lower-body run and saves."""
import argparse,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from slide_feet_bundle import prepare_slide_feet
from native_workspace import port
OUT=ROOT/'docs/validation/wallrun'
BUILD=ROOT/'build/wallrun'
def run():
    engine,mod=prepare_slide_feet('wallrun',build=BUILD,server=BUILD/'server/hl.dll',engine_binaries=BUILD/'engine')
    OUT.mkdir(parents=True,exist_ok=True)
    lines=['wait 180','gl_vsync 0','host_framerate 0.0166667','fps_max 60','developer 2','con_notifytime -1',
        'sv_cheats 1','god','vf_voice_subtitles 0','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR',
        'wait 20','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
    def add(*commands):lines.extend(commands)
    def probe(name,image=False):
        add('echo WR_'+name,'cmd vf_traversal_info','vf_engine_stats')
        if image:add('screenshot scrshots/wallrun_'+name.lower()+'.png')
        add('wait 2')
    def place(x=0,y=-1006,speed=320):
        entry=300 if y<0 else 60
        add('-forward','-jump','-duck','-attack','-reload','cam_command 2','wait 15',f'cmd vf_traversal_place {x} {y} 128 {entry} {speed} 0 0',f'vf_traversal_look {entry} 0','+forward','+jump','wait 2','-jump','vf_traversal_look 0 0','wait 6')
    place();probe('FIRST_ACTIVE',True);add('+attack','wait 10','-attack');probe('FIRE')
    add('+reload','wait 2','-reload','wait 12');probe('RELOAD',True)
    add('wait 95');probe('LONG_ACTIVE')
    place();add('cam_snapto 1','cam_idealdist 120','cam_idealyaw -100','cam_idealpitch 8','cam_command 1','wait 8');probe('THIRD_RIGHT',True)
    for frame in range(24):add(f'screenshot scrshots/wallrun_cycle_{frame:02}.png','wait 1')
    add('-forward','wait 1');probe('RELEASED',True)
    place(y=1006);add('cam_snapto 1','cam_idealdist 120','cam_idealyaw 100','cam_idealpitch 8','cam_command 1','wait 10');probe('THIRD_LEFT',True)
    add('vf_traversal_look 300 -30','+jump','wait 1');probe('BOUNCE',True)
    add('-jump','wait 30');probe('FLIGHT',True)
    place(speed=180);probe('TOO_SLOW')
    # True running takeoff at a wall, preserving the ordinary jump command.
    add('-forward','wait 20','cmd vf_traversal_place 0 -1006 36.1 300 320 0 0','vf_traversal_look 300 0','+forward','+jump','wait 12');probe('TAKEOFF',True)
    add('-jump','-forward','wait 15','cmd vf_traversal_place -850 1006 128 0 320 0 0','vf_traversal_look 60 0','+forward','+jump','wait 2','-jump','wait 3','vf_traversal_look 300 -35','+jump','wait 90');probe('CHAIN',True)
    place();add('save vf_wallrun','wait 4','load vf_wallrun','+forward','wait 15');probe('RESTORED')
    # Entry must be voluntary; existing momentum alone cannot attach.
    for name,yaw,pitch,jump in [('NO_JUMP',300,0,False),('PARALLEL_JUMP',0,0,True),
                                ('AWAY_JUMP',60,0,True),('SKY_JUMP',300,-89,True),('ENTRY_SQUARE',270,0,True),
                                ('ENTRY_SHALLOW',359,0,True),('ENTRY_DOWN',359,89,True)]:
        add('-forward','-jump','wait 15','cmd vf_traversal_place -700 -1006 128 0 320 0 0','wait 3',
            f'vf_traversal_look {yaw} {pitch}','+forward')
        if jump:add('+jump')
        add('wait 4');probe(name,True)
    place(x=-700);probe('FREE_START')
    add('vf_traversal_look 90 -85','wait 12');probe('FREE_POS_90',True)
    add('vf_traversal_look 270 85','wait 12');probe('FREE_NEG_90',True)
    add('vf_traversal_look 359.9 0','wait 12');probe('FREE_WRAP',True)
    for name,yaw in [('OVER_POS_90',90.1),('OVER_NEG_90',269.9)]:
        place(x=-700);add(f'vf_traversal_look {yaw} 0','wait 1');probe(name,True)
        add('vf_traversal_look 300 0','wait 20');probe(name+'_NO_REATTACH')
    add('-jump','-forward','quit')
    # Stay below the engine exec buffer limit.
    for part,start in enumerate(range(0,len(lines),100)):
        chunk=lines[start:start+100]
        if start+100<len(lines):chunk.append(f'exec wallrun_{part+1:03}.cfg')
        (mod/f'wallrun_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig',
        '-dev','2','-log','wallrun.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+developer','2',
        '+maxplayers','1','+map','vf_traversal','+exec','wallrun_000.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:process.wait(timeout=100)
    finally:
        if process.poll()is None:process.terminate();process.wait(timeout=8)
    text=(engine/'wallrun.log').read_text(errors='replace');shutil.copy2(engine/'wallrun.log',OUT/'native.log')
    for path in (mod/'scrshots').glob('wallrun_*.png'):shutil.copy2(path,OUT/path.name)
    cases={}
    for name,block in re.findall(r'WR_([A-Z_0-9]+)\s+(.*?)(?=WR_|\Z)',text,re.S):
        row=re.search(r'VFTraversal phase=(\d+) state=(\d+) origin=([\d.,-]+) velocity=([\d.,-]+) time=([\d.-]+) health=[\d.-]+ clip=(-?\d+) reload=(\d+) sequence=(\d+)',block)
        if row:
            p,state,origin,velocity,time,clip,reload,sequence=row.groups()
            cases[name]=dict(phase=int(p),state=int(state),origin=list(map(float,origin.split(','))),velocity=list(map(float,velocity.split(','))),time=float(time),clip=int(clip),reload=int(reload),sequence=int(sequence))
    poses=[dict(entity=int(e),gait=int(g),frame=float(f),side=float(s),roll=float(r),sole=float(d),sequence=seq)for e,g,f,s,r,d,seq in re.findall(r'VFWallRunPose entity=(\d+) gait=(\d+) frame=([\d.-]+) side=([\d.-]+) roll=([\d.-]+) sole=([\d.-]+) sequence=(\w+)',text)]
    report=dict(passed=False,cases=cases,pose_samples=len(poses),animated_frames=len({round(p['frame'],1)for p in poses}),run_gaits=sorted({p['gait']for p in poses}),combat_sequences=sorted({p['sequence']for p in poses}),sides=sorted({p['side']for p in poses}))
    (OUT/'native.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    assert process.returncode==0 and 'VFEngine: native extension v4 connected' in text
    for name in ('FIRST_ACTIVE','FIRE','RELOAD','LONG_ACTIVE','RESTORED','THIRD_RIGHT','THIRD_LEFT','TAKEOFF','CHAIN'):assert cases[name]['phase']==8,(name,cases)
    assert cases['FIRE']['clip']<cases['FIRST_ACTIVE']['clip'] and cases['RELOAD']['reload']==1
    assert cases['LONG_ACTIVE']['clip']>cases['FIRE']['clip'] and not cases['LONG_ACTIVE']['reload']
    assert cases['RELEASED']['phase']==0 and cases['RELEASED']['velocity'][2]<0
    assert cases['BOUNCE']['phase']==0 and cases['BOUNCE']['velocity'][2]>300
    assert cases['TOO_SLOW']['phase']==0
    for name in ['NO_JUMP','PARALLEL_JUMP','AWAY_JUMP','OVER_POS_90','OVER_NEG_90',
                 'OVER_POS_90_NO_REATTACH','OVER_NEG_90_NO_REATTACH']:assert cases[name]['phase']==0,(name,cases[name])
    for name in ['ENTRY_SQUARE','ENTRY_SHALLOW','ENTRY_DOWN','SKY_JUMP','FREE_POS_90','FREE_NEG_90','FREE_WRAP']:
        assert cases[name]['phase']==8 and cases[name]['velocity'][0]>280 and abs(cases[name]['velocity'][1])<25,(name,cases[name])
    for a,b in [('FREE_START','FREE_POS_90'),('FREE_POS_90','FREE_NEG_90'),('FREE_NEG_90','FREE_WRAP')]:
        assert cases[b]['origin'][0]>cases[a]['origin'][0]+40 and abs(cases[b]['origin'][1]-cases[a]['origin'][1])<1,(a,b,cases)
        assert abs(cases[b]['origin'][2]-cases[a]['origin'][2])<.01,(a,b,'pitch changed supported height')
    for name in ['OVER_POS_90','OVER_NEG_90']:assert cases[name]['velocity'][2]<0,(name,'view crossing must release immediately')
    assert len(poses)>60 and {p['side']for p in poses}=={-1,1} and all(p['gait']>0 for p in poses)
    assert len({round(p['frame'],1)for p in poses})>8,'Run cycle must animate'
    assert all(abs(p['sole']-3)<.01 for p in poses),'Running soles must stay at the supporting surface'
    from build_weapon_melee import digest
    report.update(passed=True,client_sha256=digest(mod/'cl_dlls/client.dll'),server_sha256=digest(mod/'dlls/hl.dll'),
                  renderer_sha256=digest(engine/'ref_gl.dll'),engine_sha256=digest(engine/'xash.dll'),
                  checks=['jump plus angular wall-facing entry without a narrow cone or pitch restriction','no incidental attachment','look-independent straight run',
                          'both inclusive 90 degree yaw limits','free vertical look','immediate drop beyond either limit',
                          'no reattachment without jump','ground takeoff','both walls and chained contacts','fire/reload/save/load'])
    (OUT/'native.json').write_text(json.dumps(report,indent=2))
    print('PASS native wall run, both sides, combat, release, aim impulse and chained wall contact',flush=True)
if __name__=='__main__':run()

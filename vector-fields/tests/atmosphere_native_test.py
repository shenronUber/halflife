"""Native atmosphere: all edges, camera modes, movement, weather, reload and map isolation."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import private_copy,port
from slide_feet_bundle import prepare_slide_feet
from build_modular_range import build
from build_atmosphere import deploy
OUT=ROOT/'docs/validation/atmosphere'
def run(client=None):
    live=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
    sdk=Path(os.environ.get('VF_RELEASE_SDK',ROOT/'build'))
    client=Path(client or sdk/'client/client.dll')
    engine,mod=prepare_slide_feet('atmosphere',server=sdk/'server/hl.dll',engine_binaries=live,client=client)
    private_copy(build(ensure=True),mod/'maps/vf_modular.bsp');deploy(mod)
    lines=['wait 150','gl_vsync 0','fps_max 120','host_framerate 0.0166667','developer 1','con_notifytime 0','scr_conspeed 10000','scr_drawversion 0',
        'sv_cheats 1','vf_atmosphere 1','vf_atmosphere_quality 2','vf_atmosphere_time 1',
        'cmd give item_suit','cmd give weapon_9mmAR','weapon_9mmAR','wait 40',
        'vf_reference 0','wait 20','vf_commit','wait 30','vf_character','vf_character',
        'wait 12','cmd vf_modular_info','cmd vf_modular_check']
    def add(*args):lines.extend(args)
    def snap(name):add('wait 6','echo SKY_'+name,'vf_atmosphere_info','screenshot scrshots/sky_'+name+'.png','wait 3')
    for name,x,y,yaw in [('west',-2184,-1536,180),('east',2184,-1536,0),('south',-1536,-2184,270),('north',-1536,2184,90)]:
        add(f'cmd vf_traversal_place {x} {y} 36.1 {yaw}','wait 4',f'vf_traversal_look {yaw} 65')
        snap(name)
    add('cmd vf_traversal_place -2184 -1536 36.1 180','wait 4','vf_traversal_look 180 82','vf_atmosphere_time 1','r_drawviewmodel 0','vf_first_person_body 0');snap('motion_a')
    add('vf_atmosphere_time 9');snap('motion_b')
    for mask in (1,2,4):
        add('vf_atmosphere_layers '+str(mask));snap('layer_'+str(mask))
    add('vf_atmosphere_layers 7')
    add('vf_atmosphere_time 1','vf_atmosphere 0');snap('sky_only')
    add('vf_atmosphere 1','vf_atmosphere_time -1','r_drawviewmodel 1','vf_first_person_body 1','vf_traversal_look 180 45','vf_atmosphere_bench','wait 195')
    add('vf_atmosphere_quality 1','vf_atmosphere_bench','wait 195','vf_atmosphere_quality 2')
    add('cmd vf_traversal_place 2184 1536 36.1 48','wait 4','vf_traversal_look 48 -9','vf_atmosphere_time 6.915');snap('lightning')
    add('vf_atmosphere_time 6.4');snap('calm')
    add('cmd vf_traversal_place -2184 1536 36.1 149','wait 4','vf_traversal_look 149 -8','vf_atmosphere_time 18');snap('funnel')
    add('cam_command 1','vf_traversal_look 180 35');snap('third_person')
    add('cam_command 2','save sky_review','wait 6','load sky_review','wait 140','vf_atmosphere_time 9');snap('restored')
    add('cmd vf_modular_check','noclip','cmd vf_traversal_place 0 0 2750 90','wait 4','vf_traversal_look 90 80',
        'default_fov 110','r_drawviewmodel 0','vf_first_person_body 0');snap('overview')
    add('vf_traversal_look 90 -89');snap('zenith')
    add('vf_atmosphere_time -1','map vf_range','wait 180');snap('other_map')
    add('map vf_modular','wait 180','cmd vf_modular_check','vf_atmosphere_time 9');snap('returned')
    add('vf_atmosphere_time -1','quit')
    for part,first in enumerate(range(0,len(lines),70)):
        chunk=lines[first:first+70]
        if first+70<len(lines):chunk.append(f'exec sky_review_{part+1:03}.cfg')
        (mod/f'sky_review_{part:03}.cfg').write_text('\n'.join(chunk)+'\n')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game',mod.name,'-windowed','-width','1280','-height','720','-nointro','-nowriteconfig','-dev','1',
        '-log','sky-review.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+map','vf_modular',
        '+vf_modular_seed','42','+map','vf_modular','+exec','sky_review_000.cfg'],cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:process.wait(timeout=150)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    OUT.mkdir(parents=True,exist_ok=True);log=(engine/'sky-review.log').read_text(errors='replace');shutil.copy2(engine/'sky-review.log',OUT/'native.log')
    for image in(mod/'scrshots').glob('sky_*.png'):shutil.copy2(image,OUT/image.name)
    assert process.returncode==0 and 'Host_Error'not in log and 'Crash:'not in log,log[-3000:]
    stats={name:dict(active=int(active),loaded=int(loaded),banks=int(banks),time=float(t),flash=float(f)) for name,active,loaded,banks,t,f in
        re.findall(r'SKY_(\w+)\s+VFAtmosphere active=(\d+).*?loaded=(\d+) banks=(\d+) time=([\d.]+).*?flash=([\d.]+)',log)}
    required=['west','east','south','north','motion_a','motion_b','lightning','calm','funnel','third_person','restored','overview','zenith','other_map','returned']
    assert all(name in stats for name in required),stats
    for name in required:
        if name!='other_map':assert stats[name]['active']==1 and stats[name]['loaded']>=2 and (stats[name]['banks']>0 or name=='zenith'),(name,stats[name])
    assert stats['other_map']['active']==0 and stats['other_map']['banks']==0,stats
    assert stats['lightning']['loaded']==3 and stats['lightning']['flash']>.5 and stats['calm']['flash']==0,stats
    checks=re.findall(r'VFModular check seed=42 candidates=102 mismatches=(\d+)',log)
    assert len(checks)>=3 and set(checks)=={'0'},checks
    a=np.asarray(Image.open(OUT/'sky_motion_a.png').convert('RGB'),dtype=float)
    b=np.asarray(Image.open(OUT/'sky_motion_b.png').convert('RGB'),dtype=float)
    # Central sky region avoids the weapon/body and the HUD. Only the cosmetic clock changed.
    crop=(slice(80,470),slice(250,930));difference=np.abs(a[crop]-b[crop]).mean()
    assert a[crop].mean()>120 and a[crop].std()>12,('Nadir capture must show textured bright clouds, not the platform floor',float(a[crop].mean()))
    assert difference>1.5,('Cloud motion invisible',difference)
    deck=np.asarray(Image.open(OUT/'sky_layer_1.png').convert('RGB'),dtype=float)
    sky=np.asarray(Image.open(OUT/'sky_sky_only.png').convert('RGB'),dtype=float)
    deck_difference=np.abs(deck[crop]-sky[crop])
    assert np.percentile(deck_difference,99)<64,('Haze deck must blend rather than produce an opaque cut',float(np.percentile(deck_difference,99)))
    bench=re.findall(r'VFAtmosphere bench: samples=180 banks=(\d+) cpu_mean_ms=([\d.]+) cpu_p95_ms=([\d.]+) frame_mean_ms=([\d.]+) frame_p95_ms=([\d.]+)',log)
    assert len(bench)==2 and all(float(row[2])<5 for row in bench),bench
    report=dict(passed=True,stats=stats,geometry_checks=checks,motion_mean_difference=difference,deck_difference_p99=float(np.percentile(deck_difference,99)),benchmarks=bench,
        checks=['four outward platform edges','vertical nadir and zenith','cloud motion at fixed camera','distant lightning pulses',
            'first and third person','save/load reloads textures','other map has no atmosphere','map return reloads resources',
            'same 102 BSP collision candidates','bounded scenery CPU cost'],
        visual_review='Review saved native screenshots for style and cloud/sky continuity; pixels do not prove full volumetric rendering.')
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native animated atmosphere, weather, resource lifecycle and geometry',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--client',type=Path);run(p.parse_args().client)


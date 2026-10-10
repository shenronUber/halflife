"""Native radial blood bursts, colour separation and bounded retained trails."""
import json,re,shutil,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import death_sounds_test as audio
OUT=audio.OUT

def run():
    e,m=audio.setup('death-blood');cases=[('neutral','head','standard'),('electro','left_arm','electro'),('corrosion','right_leg','corrosion'),('multiple','all','standard')]
    cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\ns_show 0\ncon_notifytime 0\nr_drawviewmodel 0\n'
    for name,region,effect in cases:
        cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_aim 0\ndefault_fov 55\nwait 14\necho BLOOD_BEGIN_{name}\ncmd vf_range_death 0 {region} {effect}\n'
        for i in range(10):cfg+=f'wait 8\nvf_death_client\nscreenshot scrshots/{name}_{i:02}.png\n'
        cfg+=f'wait 240\necho BLOOD_END_{name}\n'
    cfg+='cmd vf_death_clear\nwait 12\necho BLOOD_CLEAR\nvf_death_client\nquit\n'
    (m/'blood.cfg').write_text(cfg);started=time.monotonic();log=audio.launch(e,'blood.cfg','blood.log');(OUT/'blood-native.log').write_text(log)
    results=[]
    for name,region,effect in cases:
        part=log.split('BLOOD_BEGIN_'+name+' ')[1].split('BLOOD_END_'+name+' ')[0]
        counts=re.findall(r'VFBlood alpha_rgb=1 radial_burst=10 gravity=300 active=(\d+) invalid_color=(\d+)',part)
        assert counts and max(int(c[0]) for c in counts)>10 and all(c[1]=='0' for c in counts),(name,counts)
        assert all(int(n)<=384 for n in re.findall(r'pool active=(\d+)',part))
        assert 'frame=' in part and 'VFFragment client' in part
        # Fresh neutral blood is visible as red pixels rather than pale spray.
        images=[];red=[]
        for i in range(10):
            path=m/'scrshots'/f'{name}_{i:02}.png';im=Image.open(path).convert('RGB');images.append(im)
            a=np.asarray(im)[100:460,240:850].astype(float);mask=(a[:,:,0]>55)&(a[:,:,0]>a[:,:,1]*2.5)&(a[:,:,0]>a[:,:,2]*2.5)
            red.append(int(mask.sum()))
        assert max(red)>10,(name,red)
        results.append(dict(effect=effect,region=region,active_blood=max(int(c[0]) for c in counts),red_pixel_counts=red))
    assert re.search(r'VFBlood .*active=0 invalid_color=0',log.split('BLOOD_CLEAR ')[1])
    frames=[]
    for i in range(10):
        sheet=Image.new('RGB',(1280,504),(15,24,31));draw=ImageDraw.Draw(sheet)
        for j,(name,_,effect) in enumerate(cases):
            im=Image.open(m/'scrshots'/f'{name}_{i:02}.png').convert('RGB').crop((260,80,1120,670)).resize((320,440));sheet.paste(im,(j*320,48));draw.text((j*320+12,16),name.upper(),fill=(230,241,242))
        frames.append(sheet)
    frames[0].save(OUT/'blood-dispersion.gif',save_all=True,append_images=frames[1:],duration=80,loop=0);frames[4].save(OUT/'blood-dispersion.jpg')
    report=dict(seconds=round(time.monotonic()-started,2),cases=results,checks=['fresh detached whole pieces emit ten irregular blood droplets','explicit dark-red alpha-blended blood separated from additive elemental layers','blood and elemental trails share a 384-particle budget','native frames show red blood in neutral and elemental events','clearing deletes retained blood trails'])
    (OUT/'blood.json').write_text(json.dumps(report,indent=2));print('PASS native blood',json.dumps(report),flush=True)
if __name__=='__main__':run()

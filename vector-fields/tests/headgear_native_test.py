"""Isolated native review of six designs, with five worn/raised pose pairs."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from native_workspace import EVIDENCE
from headgear_preview import stage
from headgear_assets_test import run as assets
from studio_assets import Studio

CHOICES=[('riot',1,'Anti-emeute / fermee'),('riot-up',3,'Anti-emeute / levee'),
         ('spartan',2,'Spartiate'),('nvg-red',4,'Optique rouge / trois yeux'),
         ('nvg-red-up',6,'Optique rouge / relevee'),('nvg-green',5,'Optique verte'),
         ('nvg-green-up',7,'Optique verte / relevee'),('ballistic',8,'Casque blinde / ferme'),
         ('ballistic-up',9,'Casque blinde / releve'),('gas-mask',10,'Masque a gaz / porte'),
         ('gas-mask-up',11,'Masque a gaz / range au sommet')]


def run(heads_only=False):
    asset_report=assets()
    engine,mod=stage()
    model_hash=hashlib.sha256((mod/'models/vf_headgear/headgear.mdl').read_bytes()).hexdigest()
    assert model_hash==asset_report['source_sha256']
    manifest=json.loads((ROOT/'generated/personas/manifest.json').read_text())
    baseline=manifest['base_entry']; captures=[]
    sequences=Studio(ROOT/'generated/personas/persona_rig.mdl').sequences
    def snap(name):
        captures.append('helmet_'+name)
        return f'wait 16\nscreenshot scrshots/helmet_{name}.png\nwait 4\n'
    script=('wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nweapon_9mmAR\n'
            'cmd vf_appearance_mode 1\nwait 30\nvf_skins\nwait 35\nvf_skin_tab 0\nvf_skin_filter 7\n'
            f'vf_skin_all {baseline}\nvf_skin_commit\nwait 25\nvf_animation 0\nvf_animation_time 0\n'
            'vf_skin_isolate\nvf_ui_pointer 1850 1030 0\nvf_headgear_audit\ncmd vf_body_info\n')
    for key,_,_ in [('none',0,'Cagoule seule')]+CHOICES:
        script+=f'vf_headgear {key}\n'
        for view,turns in [('front',0),('right',2),('back',4),('left',3)]:
            script+='vf_rotate\n'*turns+snap(key+'_'+view)
        script+='vf_rotate\n'*3
    script+='vf_headgear invalid\n'+snap('invalid_keeps_stowed_mask')
    for key in ('riot','nvg-red','nvg-green','ballistic','gas-mask'):
        script+=f'vf_headgear {key}-down\n'+snap(key+'_down_alias')
    if not heads_only:
        for key in ('jade-symbiosis','amber-culture','miami-vice'):
            theme=next(t for t in manifest['themes'] if t['key']=='persona_'+key.replace('-','_'))
            script+=f'vf_skin_all {theme["id"]}\nvf_skin_commit\nwait 25\n'
            for helmet,_,_ in CHOICES:
                script+=f'vf_headgear {helmet}\nvf_animation 0\nvf_animation_time 0\n'+snap(key+'_'+helmet)
        script+=f'vf_skin_all {baseline}\nvf_skin_commit\nwait 25\nvf_skin_isolate\n'
        for helmet,_,_ in CHOICES:
            script+=f'vf_headgear {helmet}\n'
            for name,seq,seconds in [('standing',0,0),('running',sequences.index('run'),.25),('crouching',sequences.index('crouch_idle'),.15)]:
                script+=f'vf_animation {seq}\nvf_animation_time {seconds}\n'+snap(helmet+'_'+name)
        script+='vf_animation 0\nvf_animation_time 0\ncmd vf_body_info\nvf_skins\ncmd vf_skin_camera\nwait 35\nr_drawviewmodel 0\ndefault_fov 55\n'
        for key,_,_ in [('none',0,'')]+CHOICES:
            script+=f'vf_headgear {key}\n'+snap(key+'_world')+'cmd vf_body_info\n'
    else:
        script+='cmd vf_body_info\n'
    script+='vf_headgear none\ncmd vf_body_info\nwait 20\nvf_engine_stats\nquit\n'
    (mod/'review.cfg').write_text(script,encoding='ascii')
    started=time.time()
    command=[str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,
             '-borderless','-width','1920','-height','1080','-console','-nointro','-nowriteconfig',
             '-log','headgear.log','+exec','lab_controls.cfg','+developer','1','+map','vf_range','+exec','review.cfg']
    p=subprocess.Popen(command,cwd=engine)
    try:
        p.wait(timeout=210)
    finally:
        if p.poll() is None:
            p.terminate();p.wait(timeout=10)
    assert p.returncode==0,p.returncode
    log=(engine/'headgear.log').read_text(errors='replace')
    assert 'Spawn Server: vf_range' in log
    assert 'VFHeadgear audit: carriers=4 variants=12 passed=48 failed=0' in log
    assert 'rejected=0' in log and not any(x in log for x in ('Host_Error','SV_Error','Could not load'))
    for key,body,_ in CHOICES:
        assert f'VFHeadgear trial: {key} variant={body} bone=Bip01 Head local=1' in log
    assert 'Usage: vf_headgear none|riot|riot-down|riot-up|spartan|nvg-red|nvg-red-down|nvg-red-up' in log
    for name in captures:
        path=mod/'scrshots'/(name+'.png')
        assert path.stat().st_mtime>=started and Image.open(path).size==(1920,1080)
    crop=(620,315,1120,755)
    assert Image.open(mod/'scrshots/helmet_gas-mask-up_front.png').crop(crop).tobytes()==Image.open(mod/'scrshots/helmet_invalid_keeps_stowed_mask.png').crop(crop).tobytes()
    for key in ('riot','nvg-red','nvg-green','ballistic','gas-mask'):
        assert Image.open(mod/'scrshots'/f'helmet_{key}_front.png').crop(crop).tobytes()==Image.open(mod/'scrshots'/f'helmet_{key}_down_alias.png').crop(crop).tobytes(),key
    bounds=re.findall(r'VFBody player=\d+ mins=([^ ]+) maxs=([^ ]+)',log)
    assert len(bounds)>=(1 if heads_only else 4) and len(set(bounds))==1,bounds
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',25); previews=[]
    def shot(key,view): return Image.open(mod/'scrshots'/f'helmet_{key}_{view}.png').convert('RGB').crop(crop)
    def save(board,name):
        path=ROOT/'docs/images'/name;board.save(path,quality=95,subsampling=0);previews.append(str(path.relative_to(ROOT)))
    # Every pose has four native angles. The overview places each wearing pose
    # immediately over its raised/stowed counterpart; no composited 3D mockups.
    for choices,name in [(CHOICES[:3],'headgear-detail-in-game.jpg'),(CHOICES[3:7],'headgear-optics-in-game.jpg'),
                         (CHOICES[7:],'headgear-ballistic-gas-in-game.jpg')]:
        board=Image.new('RGB',(2000,len(choices)*500),'#131c24');d=ImageDraw.Draw(board)
        for row,(key,_,title) in enumerate(choices):
            d.text((16,row*500+12),title,font=font,fill='#e5f3ed')
            for col,view in enumerate(('front','right','back','left')):
                board.paste(shot(key,view),(col*500,row*500+55))
        save(board,name)
    board=Image.new('RGB',(2000,960),'#131c24');d=ImageDraw.Draw(board)
    for col,(low,high,title) in enumerate([('riot','riot-up','Anti-emeute'),('nvg-red','nvg-red-up','Optique rouge'),
                                        ('nvg-green','nvg-green-up','Optique verte'),('ballistic','ballistic-up','Casque blinde'),
                                        ('gas-mask','gas-mask-up','Masque a gaz')]):
        for row,key in enumerate((low,high)):
            d.text((col*400+12,row*450+12),title+(' / porte' if row==0 else ' / releve'),
                   font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',21),fill='#e5f3ed')
            board.paste(shot(key,'front').resize((400,352),Image.Resampling.LANCZOS),(col*400,row*450+55))
    save(board,'headgear-positions-in-game.jpg')
    if not heads_only:
        board=Image.new('RGB',(1500,len(CHOICES)*565),'#131c24');d=ImageDraw.Draw(board)
        for row,(key,_,title) in enumerate(CHOICES):
            for col,pose in enumerate(('standing','running','crouching')):
                d.text((col*500+14,row*565+12),title+' / '+pose,font=font,fill='#e5f3ed')
                im=Image.open(mod/'scrshots'/f'helmet_{key}_{pose}.png').convert('RGB')
                board.paste(im.crop((610,285,1110,780)),(col*500,row*565+55))
        save(board,'headgear-animations-in-game.jpg')
        board=Image.new('RGB',(1500,len(CHOICES)*500),'#131c24');d=ImageDraw.Draw(board)
        for col,(skin,title) in enumerate([('jade-symbiosis','Jade'),('amber-culture','Ambre'),('miami-vice','Miami Vice')]):
            for row,(key,_,label) in enumerate(CHOICES):
                d.text((col*500+14,row*500+12),title+' / '+label,font=font,fill='#e5f3ed')
                board.paste(Image.open(mod/'scrshots'/f'helmet_{skin}_{key}.png').convert('RGB').crop(crop),(col*500,row*500+55))
        save(board,'headgear-skins-in-game.jpg')
    report=dict(passed=True,headgear_designs=6,static_body_variants=11,paired_designs=5,assets=asset_report,captures=captures,previews=previews,
                renderer_assemblies=48,collider_bounds=bounds[0],tested_model_sha256=model_hash,isolated=True,
                evidence=str((EVIDENCE/engine.name).relative_to(ROOT)),heads_only=heads_only,
                preserved_persona_rig_sha256=hashlib.sha256((ROOT/'generated/personas/persona_rig.mdl').read_bytes()).hexdigest(),
                source_prompts='assets/headgear/provenance.json',
                scope='Local static visual trials; no interactive raising, vision effect or inventory replication')
    (ROOT/'docs/validation/headgear.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS isolated headgear native:',len(captures),'captures, 48 assemblies; proofs archived automatically',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--heads-only',action='store_true')
    run(parser.parse_args().heads_only)

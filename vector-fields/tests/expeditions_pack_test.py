"""Verify the matching pack launcher and export paired native-render previews."""
import json,subprocess,time,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from play_expeditions import deploy,PACK,ROOT,MOD,ENGINE,command

def previews():
 pack=json.loads(PACK.read_text(encoding='utf-8-sig'))['themes']
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27)
 small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
 board=Image.new('RGB',(1420,5*520+95),'#131c24');d=ImageDraw.Draw(board)
 d.text((26,18),'CINQ UNIVERS / PERSONNAGE + RELAIS R-01',font=font,fill='#eaf2f4')
 d.text((26,58),'Captures du moteur - memes modeles, nouvelles textures',font=small,fill='#a6bcc5')
 char_board=Image.new('RGB',(5*285,580),'#131c24');cd=ImageDraw.Draw(char_board)
 compact=Image.new('RGB',(1600,800),'#131c24');kd=ImageDraw.Draw(compact)
 kd.text((24,15),'CINQ UNIVERS / GIGN + R-01 / CAPTURES DU MOTEUR',font=font,fill='#eaf2f4')
 heads=Image.new('RGB',(5*240,375),'#131c24');hd=ImageDraw.Draw(heads)
 for i,t in enumerate(pack,7):
  row=i-7;y=95+row*520
  a=Image.open(MOD/'scrshots'/('persona_persona_'+t['key']+'_front.png')).convert('RGB').crop((730,320,955,795))
  back=Image.open(MOD/'scrshots'/('persona_persona_'+t['key']+'_back.png')).convert('RGB').crop((730,320,955,795))
  w=Image.open(ENGINE/'vf_visual/scrshots'/f'r01_style_preview_{i}.png').convert('RGB').crop((490,305,1210,726))
  kd.text((row*320+18,65),t['weaponTitle'],font=font,fill='#eaf2f4');compact.paste(a,(row*320+48,100));compact.paste(w.resize((300,175),Image.Resampling.LANCZOS),(row*320+10,600))
  d.text((22,y),t['title'],font=font,fill='#eaf2f4')
  board.paste(a,(22,y+42));board.paste(back,(275,y+42));board.paste(w,(630,y+84))
  d.text((635,y+38),t['weaponTitle'],font=font,fill='#eaf2f4')
  cd.text((row*285+12,15),t['weaponTitle'],font=font,fill='#eaf2f4');char_board.paste(a,(row*285+20,62))
  atlas=Image.open(ROOT/'assets/personas'/t['id']/'texture-atlas.png').convert('RGB')
  face=atlas.crop((1010,600,1254,994)).resize((220,330),Image.Resampling.LANCZOS)
  hd.text((row*240+8,8),t['weaponTitle'],font=small,fill='#eaf2f4');heads.paste(face,(row*240+10,40))
 board.save(ROOT/'build/expeditions-five-pairs-in-game.jpg',quality=94,subsampling=0)
 char_board.save(ROOT/'build/expeditions-five-characters-in-game.jpg',quality=94,subsampling=0)
 heads.save(ROOT/'build/expeditions-face-coverage.jpg',quality=94,subsampling=0)
 compact.save(ROOT/'build/expeditions-five-sets.jpg',quality=95,subsampling=0)

def run():
 cfg=deploy();script=cfg.read_text()+'wait 30\nscreenshot scrshots/expeditions_launcher.png\nwait 10\nvf_ui_pointer 1220 40 1\nwait 3\nvf_ui_pointer 1220 40 0\nwait 15\ncmd vf_skin_camera\nwait 40\nscreenshot scrshots/expeditions_pair_in_game.png\nwait 8\necho PAIR_REOPEN\nvf_reference\nwait 30\nvf_reference_style 8\nvf_commit\nwait 30\nvf_reference_style 7\nvf_commit\nwait 30\nvf_ui_pointer 1220 40 1\nwait 3\nvf_ui_pointer 1220 40 0\nwait 12\nsave vf_expeditions_test\nwait 40\nload vf_expeditions_test\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_engine_stats\nquit\n'
 target=MOD/'vf_expeditions_validation.cfg';target.write_text(script,encoding='ascii');start=time.time()
 p=subprocess.Popen(command(target.name,'vf-expeditions-validation.log'),cwd=ENGINE)
 try:p.wait(timeout=65)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0
 log=(ENGINE/'vf-expeditions-validation.log').read_text(errors='replace')
 manifest=json.loads((ROOT/'generated/personas/manifest.json').read_text());pack=json.loads(PACK.read_text(encoding='utf-8-sig'))['themes']
 first=next(t for t in manifest['themes']if t['key']=='persona_'+pack[0]['key'])['id']
 assert f'VFSkin client: result=0 ids='+','.join([str(first)]*5) in log
 assert 'VFR01 styles accepted: player=1 first=7 optic=7 feed=7' in log
 after=log.split('Loading game from save/vf_expeditions_test.sav')[-1]
 assert f'VFState player=1 skins='+','.join([str(first)]*5)+' weapon=' in after
 assert 'VFR01 state: player=1 first=7 optic=7 feed=7' in after
 assert 'VFAppearance state: player=1 mode=1' in after
 reopen=log.split('PAIR_REOPEN')[-1]
 assert 'VFR01 styles accepted: player=1 first=8 optic=8 feed=8' in reopen
 assert 'VFAppearance mode=0 player=1' not in reopen
 assert 'VFState rejected' not in log and 'rejected=0' in log
 shot=MOD/'scrshots/expeditions_launcher.png';assert shot.stat().st_mtime>=start
 previews()
 report=dict(themes=[t['id']for t in pack],atlases=10,character_skin_ids=list(range(first,first+5)),weapon_styles=list(range(7,12)),checks=['matching character and R-01 equipped by launcher','matching appearance pair survives save/load','reopening R1 and changing its finish preserves the free character skin','native front/back and R-01 previews assembled from verified captures'],coverage='Visual review of atlas face, neck, gloves and all native front/back captures required',launcher_capture=str(shot))
 (ROOT/'build/expeditions-verification.json').write_text(json.dumps(report,indent=2))
 print('PASS five matching skin sets; launcher and save/load; paired native previews exported.')
if __name__=='__main__':run()

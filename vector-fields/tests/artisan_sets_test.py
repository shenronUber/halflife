"""Craft-material outfits: inventory, native views, save/load and maximum fragment pair."""
import argparse,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from new_personas_test import assets as costume_assets,ROOT,SLOTS
from fragment_skins import FINISH_COUNT,pair_skin

KEYS=['jade_symbiosis','amber_culture','savage_butcher','miami_vice']

def assets():
    themes=costume_assets(KEYS)
    assert [t['skin']for t in themes]==[19,20,21,22]
    config=json.loads((ROOT/'data/gameplay-content.json').read_text())
    descriptions={c['key']:c['gear_descriptions']for c in config['operator_collections']if c['key']in KEYS}
    rows={r.split('|')[1]:r.split('|')for r in (ROOT/'data/equipment.txt').read_text().splitlines()if r and not r.startswith(('#','limits|'))}
    for key in KEYS:
        assert set(descriptions[key])==set(SLOTS)
        for slot in SLOTS:assert rows['gign_'+slot+'_'+key][12]==descriptions[key][slot]
    # Rare gold aviator rims must survive the engine's 256-color export.
    from studio_assets import Studio
    model=Studio(ROOT/'generated/personas/persona_scout.mdl')
    name,w,h,pixels,palette=next(t for t in model.textures if t[0]=='persona_miami_vice.bmp')
    compiled=Image.frombytes('P',(w,h),pixels);compiled.putpalette(palette)
    source=Image.open(ROOT/'generated/personas/corrected-atlases/miami_vice.png').convert('RGB')
    eye_band=(414,298,509,338)
    def gold_count(image):
        return sum(r>130 and g>100 and g>b*1.4 and r>g*1.05 and r<g*1.5 for r,g,b in image.convert('RGB').crop(eye_band).getdata())
    assert gold_count(source)>10 and gold_count(compiled)>=gold_count(source)*.5,'Aviator gold changed hue during indexed export'
    # costume_assets checks the versioned appearance identities and current
    # inventory/lootpool mapping, independent of ignored build baselines.
    return themes

def contact_sheet():
    from library_engine_test import MOD
    board=Image.new('RGB',(1800,1080),'#131c24');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
    small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    for i,(key,title)in enumerate([('porcelain','Opérateur de porcelaine'),('jade_symbiosis','Opérateur de jade'),('amber_culture',"Opérateur d'ambre"),('savage_butcher','Savage Butcher'),('miami_vice','Miami Vice')]):
        draw.text((i*360+12,14),title,font=font,fill='#e5f3ed')
        for j,view in enumerate(['front','back']):
            im=Image.open(MOD/'scrshots'/f'artisan_{key}_{view}.png').convert('RGB')
            board.paste(im.crop((630,280,930,732)),(i*360+30,j*520+75))
            draw.text((i*360+12,j*520+49),'Face'if j==0 else'Dos',font=small,fill='#a9bcc6')
    target=ROOT/'docs/images/artisan-sets-in-game.jpg'
    board.save(target,quality=95,subsampling=0)
    return target

def native():
    from library_engine_test import run_cfg,click
    themes=assets();captures=[]
    def snap(name):
        name='artisan_'+name;captures.append(name)
        return f'wait 16\nscreenshot scrshots/{name}.png\nwait 4\n'
    s='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nweapon_9mmAR\nvf_operator\nwait 35\nvf_animation_time 0\n'
    for key in ['porcelain']+KEYS:
        s+=f'echo ARTISAN_{key}\n'
        for slot in SLOTS:s+=f'vf_item gign_{slot}_{key}\n'
        s+='vf_commit\nwait 25\nvf_select_slot 3\nvf_animation_time 0\n'+snap(key+'_front')
        s+='vf_rotate\n'*6+snap(key+'_back')+'vf_rotate\n'*6
        s+=click(1220,40)+'wait 15\nvf_engine_stats\n'+snap(key+'_hands')+'vf_operator\nwait 25\n'
    # Every newly appended collection must be reachable through actual pointer input.
    s+='vf_select_slot 0\nwait 8\n'
    for key in reversed(KEYS):s+=click(854,223)+snap(key+'_filter')
    s+='vf_select_slot 3\n'
    for slot,key in zip(SLOTS,[KEYS[2],KEYS[3],KEYS[2],KEYS[3],KEYS[2]]):s+=f'vf_item gign_{slot}_{key}\n'
    s+='vf_commit\nwait 25\n'+snap('mixed')+click(1220,40)+'save vf_artisan_sets\nwait 35\nload vf_artisan_sets\nwait 180\ndeveloper 1\ncon_notifytime 0\necho ARTISAN_RESTORED\nvf_operator\nwait 35\nvf_animation_time 0\n'+snap('restored')
    s+=click(1220,40)+'cmd vf_death_test all standard legacy\nwait 15\nvf_death_client\nvf_engine_stats\n'+snap('mixed_death')+'quit\n'
    log=run_cfg('vf_artisan_sets_test',s,captures=captures,timeout=120)
    for key,t in zip(KEYS,themes):
        section=log.split('ARTISAN_'+key,1)[1].split('ARTISAN_',1)[0]
        assert 'skins='+','.join([str(t['id'])]*5)in section,key
        assert f'gloves={t["skin"]} sleeves={t["skin"]}'in section,key
    after=log.split('ARTISAN_RESTORED',1)[1]
    ids=[themes[i]['id']for i in [2,3,2,3,2]]
    assert 'skins='+','.join(map(str,ids))in after
    expected=[pair_skin(themes[2]['skin'],themes[2]['skin'])]+[pair_skin(themes[3]['skin'],themes[2]['skin'])]*4
    assert max(expected)==FINISH_COUNT**2-1
    spawned=re.findall(r'VFFragment spawn entity=(\d+) body=(\d+) effect=-1 whole=1[^\n]*skin=(\d+)',after)
    assert len(spawned)==5,spawned
    for entity,body,skin in spawned:
        assert int(skin)==expected[int(body)-15]
        assert re.search(fr'VFFragment client entity={entity} body={body} [^\n]*skin={skin}\b',after)
    assert 'rejected=0'in log and not any(e in log for e in ('VFState rejected','Host_Error','SV_Error','Could not load','not precached'))
    target=contact_sheet()
    report=dict(themes=KEYS,captures=captures,texture_families=FINISH_COUNT,fragment_pairs=FINISH_COUNT**2,
                maximum_fragment_skin_received=max(expected),historical_ids_preserved=True,
                checks=['four complete five-piece sets in inventory','native front/back and first-person renders',
                        'last four collections selectable through actual UI','mixed outfit survives save/load',
                        'mixed fragments reach client including highest skin index'],contact_sheet=str(target))
    (ROOT/'build/artisan-sets-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS artisan sets:',len(captures),'native captures; maximum fragment skin',max(expected))

def heads():
    from library_engine_test import run_cfg
    themes=assets();captures=[]
    s='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\nvf_skins\nwait 35\nvf_skin_tab 0\nvf_skin_filter 7\nvf_animation_time 0\nvf_skin_isolate\nvf_ui_pointer 1850 1030 0\nwait 2\n'
    for key,t in zip(KEYS,themes):
        s+=f'vf_skin_all {t["id"]}\nvf_skin_commit\nwait 25\nvf_animation_time 0\n'
        for view,turns in [('front',0),('right',2),('back',4),('left',3)]:
            s+='vf_rotate\n'*turns
            name=f'artisan_head_{key}_{view}';captures.append(name)
            s+=f'wait 16\nscreenshot scrshots/{name}.png\nwait 4\n'
        s+='vf_rotate\n'*3
    s+='vf_engine_stats\nquit\n'
    log=run_cfg('vf_artisan_heads_test',s,captures=captures,timeout=100)
    assert 'rejected=0'in log
    from library_engine_test import MOD
    board=Image.new('RGB',(2000,4*525),'#131c24');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
    for j,(key,t)in enumerate(zip(KEYS,themes)):
        draw.text((15,j*525+10),t['title'],font=font,fill='#e5f3ed')
        for i,view in enumerate(['front','right','back','left']):
            im=Image.open(MOD/'scrshots'/f'artisan_head_{key}_{view}.png').convert('RGB')
            board.paste(im.crop((620,335,1120,790)),(i*500,j*525+55))
    target=ROOT/'docs/images/artisan-heads-in-game.jpg'
    board.save(target,quality=95,subsampling=0)
    (ROOT/'build/artisan-heads-verification.json').write_text(json.dumps(dict(captures=captures,contact_sheet=str(target)),indent=2)+'\n')
    print('PASS artisan head capture:',len(captures),'native close-ups')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--assets',action='store_true');p.add_argument('--heads',action='store_true');a=p.parse_args()
    assets()if a.assets else heads()if a.heads else native()

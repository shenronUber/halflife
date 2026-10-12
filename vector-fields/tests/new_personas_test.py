"""New costumes resolve as equipment, render in the native game and survive a save."""
import argparse,json,re,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from studio_assets import Studio
from fragment_skins import FINISH_COUNT,pair_skin
KEYS=['red_son','selenite','masked_hero','rally_driver','penitent_soldier']
SLOTS=['head','torso','gloves','legs','boots']

def assets(keys=KEYS):
    manifest=json.loads((ROOT/'generated/personas/manifest.json').read_text())
    themes={t['key']:t for t in manifest['themes']}
    rows=[r.split('|')for r in (ROOT/'data/equipment.txt').read_text().splitlines()if r and not r.startswith(('#','limits|'))]
    items={r[1]:r for r in rows};pool=json.loads((ROOT/'data/lootpool.json').read_text())
    records={r['id']:r for r in pool['entries']};sets={r['id']:r for r in pool['operator_sets']}
    for key in keys:
        t=themes['persona_'+key];assert 14<=t['skin']<FINISH_COUNT
        collection=Path(t['atlas']).parent.name
        for slot in SLOTS:
            id='gign_'+slot+'_'+key;r=items[id];entry=records[id]
            assert r[14]==t['key'] and entry['appearance_index']==t['id']
            assert rows[entry['equipment_index']-1][1]==id
            assert entry['collection']==collection
        assert len(sets['operator_'+collection]['items'])==5
    assert len({r['name']for r in pool['entries']})==len(pool['entries'])
    models=['personas/persona_scout','r01/r01_fp_gloves','r01/r01_fp_sleeves','traversal/slide_legs','traversal/ledge_gloves','traversal/ledge_sleeves','deaths/persona_death']
    for name in models:assert Studio(ROOT/'generated'/(name+'.mdl')).numskinfamilies==FINISH_COUNT,name
    assert Studio(ROOT/'generated/deaths/persona_death_gibs.mdl').numskinfamilies==FINISH_COUNT**2
    audit=json.loads((ROOT/'generated/personas/head-join-audit.json').read_text())
    authored=json.loads((ROOT/'assets/personas/personas.json').read_text())
    shirt_collars={t['key']for t in authored['themes']if t.get('shirt_collar')}
    assert audit['skins_checked']==FINISH_COUNT and len(audit['skins'])==FINISH_COUNT
    for skin in audit['skins']:
        assert len(skin['joins'])==3 and (ROOT/skin['corrected_atlas']).is_file()
        assert skin['padding']['islands']==6 and skin['padding']['outer_margin_texels']==3
        continuity=skin['continuity']
        assert continuity['head_charts']==4 and continuity['seam_edges']==20
        assert continuity['matched_samples']>=1300 and continuity['gradient_samples']>=1300
        assert continuity['after']['mean_rgb']<1 and continuity['after']['p95_rgb']<2
        assert continuity['indexed_after']['colour']['mean_rgb']<2
        assert continuity['indexed_after']['colour']['p95_rgb']<8
        for join in skin['joins']:
            if join.get('material')=='shirt_collar':
                assert skin['key']in shirt_collars and join['island']=='curved_join'
                assert not join['corrected'] and join['pixels_changed']==0
                continue
            assert join['after_chroma_distance']<=.28 and join['after_brightness_ratio']<=1.65,(skin['key'],join)
    # Compare compiled UVs to the donor's real texels, rather than comparing
    # two exports produced by the same code. Texture cropping must be offset
    # exactly; otherwise the atlas background leaks into the head seams.
    import numpy as np
    from scipy.spatial import cKDTree
    from build_personas import donor
    source=Studio(donor(authored)['path']);body=Studio(ROOT/'generated/personas/persona_scout.mdl')
    vertices=[v for _,tri in source.mesh()for v in tri]
    points=np.array([v['p']for v in vertices]);texels=np.array([[v['uv'][0]*512,(1-v['uv'][1])*512]for v in vertices])
    offset=texels.min(0);tree=cKDTree(points);w,h=body.textures[0][1:3]
    for _,tri in body.mesh(choices={i:1 for i in range(5)}):
        for v in tri:
            distance,_=tree.query(v['p']);assert distance<.018
            candidates=tree.query_ball_point(v['p'],distance+.0001)
            actual=np.array([v['uv'][0]*w,(1-v['uv'][1])*h])+offset
            assert np.min(np.max(np.abs(texels[candidates]-actual),axis=1))<1e-5,'Compiled UV shifted off donor texel'
    header=(ROOT.parent/'game_shared/vf_death_visual.h').read_text()
    assert f'FinishCount={FINISH_COUNT},'in header
    delta=(ROOT.parent/'network/delta.lst').read_text()
    skin_bits=re.findall(r'DEFINE_DELTA\( skin, DT_SHORT \| DT_SIGNED, (\d+),',delta)
    assert len(skin_bits)==2 and all(FINISH_COUNT**2-1 < 2**(int(bits)-1)for bits in skin_bits),'Entity delta skin field clips mixed costume pairs'
    # An explicit, versioned identity contract replaces optional workshop
    # baselines. Equipment indices can change when the finish pool is curated;
    # save migration uses stable item keys, covered by architecture_test.cpp.
    legacy=json.loads((ROOT/'tests/fixtures/appearance-ids.json').read_text())
    skins={int(r.split('|')[0]):r.split('|')[1]for r in (ROOT/'generated/visual_skins/skins.txt').read_text().splitlines()if r and not r.startswith('#')}
    assert all(skins.get(int(i))==key for i,key in legacy.items()),'Historical appearance IDs changed'
    print('PASS new costumes:',5*len(keys),'equipment pieces,',len(keys),'complete sets, all body/view/death texture banks and historical appearance IDs')
    return [themes['persona_'+key]for key in keys]

def contact_sheet(themes):
    from library_engine_test import MOD
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
    board=Image.new('RGB',(1550,1080),'#131c24');draw=ImageDraw.Draw(board)
    for i,(key,t)in enumerate(zip(KEYS,themes)):
        for j,view in enumerate(['front','back']):
            im=Image.open(MOD/'scrshots'/f'new_costume_{key}_{view}.png').convert('RGB')
            board.paste(im.crop((630,280,930,732)),(i*310+5,j*540+65))
        draw.text((i*310+10,15),t['title'],font=font,fill='#e5f3ed')
    target=ROOT/'docs/images/new-costumes-in-game.jpg';board.save(target,quality=94,subsampling=0)
    return target

def native():
    from library_engine_test import run_cfg,click,MOD
    themes=assets();captures=[]
    def snap(name):
        captures.append('new_costume_'+name)
        return f'wait 16\nscreenshot scrshots/new_costume_{name}.png\nwait 4\n'
    s='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nweapon_9mmAR\nvf_operator\nwait 35\nvf_animation_time 0\n'
    for key,t in zip(KEYS,themes):
        s+=f'echo COSTUME_{key}\n'
        for slot in SLOTS:s+=f'vf_item gign_{slot}_{key}\n'
        s+='vf_commit\nwait 25\nvf_select_slot 3\nvf_animation_time 0\n'+snap(key+'_front')
        s+='vf_rotate\n'*6+snap(key+'_back')+'vf_rotate\n'*6
        s+=click(1220,40)+'wait 15\nvf_engine_stats\n'+snap(key+'_hands')+'vf_operator\nwait 25\n'
    # This collection stays reachable as subsequent costumes are appended.
    sets=json.loads((ROOT/'data/lootpool.json').read_text())['operator_sets']
    index=next(i for i,t in enumerate(sets)if t['collection']=='penitent-soldier')
    s+='vf_select_slot 0\nwait 8\n'+click(854,223)*(len(sets)-index)+snap('penitent_filter')
    s+='vf_select_slot 3\n'
    for slot,key in zip(SLOTS,KEYS):s+=f'vf_item gign_{slot}_{key}\n'
    s+='vf_commit\nwait 25\n'+snap('mixed')+click(1220,40)+'save vf_new_costumes\nwait 35\nload vf_new_costumes\nwait 180\ndeveloper 1\ncon_notifytime 0\necho COSTUME_RESTORED\nvf_operator\nwait 35\nvf_animation_time 0\n'+snap('restored')
    s+=click(1220,40)+'cmd vf_death_test all standard legacy\nwait 15\nvf_death_client\nvf_engine_stats\n'+snap('mixed_death')+'quit\n'
    log=run_cfg('vf_new_costumes_test',s,captures=captures,timeout=85)
    ids=[t['id']for t in themes]
    for key,t in zip(KEYS,themes):
        section=log.split('COSTUME_'+key,1)[1].split('COSTUME_',1)[0]
        assert 'skins='+','.join([str(t['id'])]*5)in section,key
        assert f'gloves={t["skin"]} sleeves={t["skin"]}'in section,key
    after=log.split('COSTUME_RESTORED',1)[1]
    assert 'skins='+','.join(map(str,ids))in after
    expected=[pair_skin(14,14),pair_skin(15,16),pair_skin(15,16),pair_skin(17,18),pair_skin(17,18)]
    spawned=re.findall(r'VFFragment spawn entity=(\d+) body=(\d+) effect=-1 whole=1[^\n]*skin=(\d+)',after)
    assert len(spawned)==5,spawned
    for entity,body,skin in spawned:
        assert int(skin)==expected[int(body)-15]
        assert re.search(fr'VFFragment client entity={entity} body={body} [^\n]*skin={skin}\b',after)
    assert 'rejected=0'in log and not any(e in log for e in ('VFState rejected','Host_Error','SV_Error','Could not load','not precached'))
    target=contact_sheet(themes)
    report=dict(themes=KEYS,captures=captures,texture_families=FINISH_COUNT,fragment_pairs=FINISH_COUNT**2,historical_ids_preserved=True,checks=['five complete costumes equipped in gameplay','native front/back and first-person captures','new costume collection filter via pointer','mixed zones survive save/load','five mixed corpse fragments keep new finishes on client'],contact_sheet=str(target))
    (ROOT/'build/new-costumes-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS five new costumes:',len(captures),'native captures, gameplay equipment, save/load and mixed new fragment skins')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--assets',action='store_true');a=p.parse_args()
    assets()if a.assets else native()

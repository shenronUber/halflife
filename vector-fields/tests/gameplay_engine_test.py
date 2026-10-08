"""Native gameplay/dev routing, GIGN equipment linkage and lootpool integrity."""
import json
from pathlib import Path
from library_engine_test import ROOT, MOD, run_cfg, click

def run():
    pool=json.loads((ROOT/'data/lootpool.json').read_text())
    entries=pool['entries'];assert len(entries)==396
    assert set(e['family']for e in entries)==set(pool['families'])
    assert len(set(e['id']for e in entries))==396
    assert len([e for e in entries if e['status']=='placeholder'])==24
    assert all(e['slot']in ['shoulders','belt','shield','special'] for e in entries if e['status']=='placeholder')
    assert not any('style_'in e['id']or 'skin_'in e['id']or 'standard'in e['id']and e['status']!='placeholder' for e in entries)
    assert json.loads((MOD/'vf/lootpool.json').read_text())==pool
    captures=[]
    def snap(name):
        name='gameplay_'+name;captures.append(name);return f'wait 25\nscreenshot scrshots/{name}.png\nwait 5\n'
    script='developer 1\n'+(MOD/'vf_start.cfg').read_text()+snap('operator')
    script+='vf_item gign_gloves_noir\nvf_commit\nwait 30\n'+snap('mixed_gloves')
    script+='vf_select_slot 7\n'+snap('placeholder_shield')
    script+=click(900,105)+'wait 30\nvf_reference_platform 2\nvf_reference_style 9\nvf_commit\nwait 30\n'+snap('weapon')
    script+=click(800,40)+'wait 30\n'+click(1130,105)+'wait 35\n'+snap('developer_arsenal')
    # Developer library and free skins remain usable, then the gameplay button restores linked equipment.
    script+='vf_library_select 0\nvf_library_equip\nwait 30\n'+click(635,105)+'wait 30\ncmd vf_appearance_mode 1\nwait 30\nvf_skin_all 0\nvf_skin_commit\nwait 30\n'+snap('developer_skin')
    script+=click(130,105)+'wait 25\nvf_item head_experimental\nvf_commit\nwait 30\n'
    script+='echo RETURN_FROM_DEV\n'+click(530,40)+'wait 40\n'+snap('returned_operator')
    script+=click(1220,40)+'cmd vf_skin_camera\nwait 35\n'+snap('world')
    script+='save vf_gameplay_test\nwait 40\nload vf_gameplay_test\nwait 180\ndeveloper 1\nvf_engine_stats\nquit\n'
    log=run_cfg('vf_gameplay_test',script,captures=captures,timeout=80)
    mixed='VFState player=1 skins=183,183,185,183,183 weapon='
    assert mixed in log,'glove item must change its linked GIGN zone'
    assert 'VFGameplay draft: gign_gloves_noir' in log
    assert 'VFUI mode: developer' in log and 'VFUI click: Arsenal' in log
    assert 'VFLibrary equipped:' in log
    assert 'VFSkin client: result=0 ids=0,0,0,0,0' in log
    returned=log.split('RETURN_FROM_DEV')[-1]
    assert 'VFUI mode: gameplay' in returned
    assert 'VFGameplay: restoring equipped loadout after developer trial' in returned
    assert mixed in returned and 'VFAppearance state: player=1 mode=0' in returned
    assert 'VFGameplay: active player=1 head=gign_head_trench receiver=r01_receiver_top' in returned
    restored=log.split('Loading game from save/vf_gameplay_test.sav')[-1]
    assert mixed in restored and 'VFR01 state: player=1 first=9 optic=9 feed=9' in restored
    assert 'VFAppearance state: player=1 mode=0' in restored
    assert 'rejected=0' in log and 'VFState rejected' not in log
    report=dict(version='0.14.0',loot_entries=len(entries),families=pool['families'],operator_sets=len(pool['operator_sets']),checks=['five GIGN body zones replace historical equipment appearances','nine operator slots retained with four provisional accessory categories','R1 top platform and cosmetic finish keep operator equipment','developer arsenal and historical skins remain usable','return to gameplay restores linked authored models and clears imported weapon overrides','mixed equipment and R1 finish survive save/load'],captures=captures)
    (ROOT/'build/gameplay-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS gameplay/dev separation, 396 loot entries, native navigation and save/load;',len(captures),'captures')
if __name__=='__main__':run()

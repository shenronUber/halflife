"""Player inventory clicks, immutable items, top receiver and real save migration."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from library_engine_test import run_cfg,click,ROOT,MOD


def main():
    pool=json.loads((ROOT/'data/lootpool.json').read_text());entries=pool['entries']
    assert len(entries)==948 and len({e['id']for e in entries})==948
    assert len({e['name']for e in entries})==948,'Every inventory object has a distinct name'
    rows=[r.split('|')for r in (ROOT/'data/equipment.txt').read_text().splitlines()if r and not r.startswith(('#','limits'))]
    for e in entries:
        row=rows[e['equipment_index']-1];assert row[1]==e['id'] and row[3]==e['name']
        if e['slot']in ('receiver','barrel','muzzle','feed','chamber','ammo','projectile','optic','underbarrel','grip','power','cooling'):
            assert len(row)==17 and e['model']=='models/vf_r01/'+row[15]+'.mdl'
    captures=[]
    def snap(name):
        captures.append('inventory_'+name)
        return f'wait 12\nscreenshot scrshots/inventory_{name}.png\nwait 4\n'
    s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_operator\nwait 35\nvf_animation_time 0\n'+snap('operator')
    # Reverse from all to Diesel, then Rome. The filter must not equip anything.
    s+='echo INVENTORY_FILTER_ONLY\n'+click(854,223)*2+'vf_commit\nwait 20\n'+snap('filter_roman')
    s+='echo INVENTORY_ONE_HEAD\n'+click(1000,271)+click(1160,698)+'wait 25\n'+snap('head_roman')
    for theme in ('roman_inventor','dieselpunk'):
        s+='echo INVENTORY_OUTFIT_'+theme+'\n'
        for slot in ('head','torso','gloves','legs','boots'):s+=f'vf_item gign_{slot}_{theme}\nwait 3\n'
        s+=click(1160,698)+'wait 25\nvf_select_slot 3\nvf_animation_time 0\n'+snap(theme)
    s+='vf_reference\nwait 25\necho INVENTORY_TOP_CLICK\n'+click(854,223)+click(1230,604)+click(1000,324)+click(1160,698)+'wait 25\nvf_animation_time 0\n'+snap('arch_top_diesel')
    # Every magazine is kept as its own object on this receiver, with actual firing/reload.
    for letter in 'abcd':
        s+=f'vf_item r01_feed_{letter}__medieval-forge\nvf_commit\nwait 25\n'+click(1220,40)+'wait 18\n+attack\nwait 14\n-attack\nwait 24\n+reload\nwait 58\n'+snap('top_reload_'+letter)+'wait 155\n-reload\nvf_reference\nwait 25\n'
    # Six optics, all attached to the offset mount.
    for key in ('a','b','c','d','inventor','diesel'):
        s+=f'vf_item r01_optic_{key}__roman-inventor\nwait 3\nvf_animation_time 0\n'+snap('optic_'+key)
    s+='vf_commit\nwait 25\n'+click(1220,40)+'save vf_inventory_019\nwait 35\nload vf_inventory_019\nwait 180\ndeveloper 1\necho INVENTORY_RESTORED\nvf_reference\nwait 35\nvf_animation_time 0\n'+snap('restored')
    # Commands which used to apply complete sets must have no effect in gameplay.
    s+='echo INVENTORY_BULK_BLOCKED\nvf_reference 4\nvf_reference_platform 0\nvf_reference_style 1\nvf_operator_set trench\nvf_commit\nwait 25\n'
    s+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\n'
    # Existing 0.18 save has base geometry IDs and independently saved finishes.
    fixture=MOD/'save/vf_themes_inventor.sav'
    if fixture.exists():
        s+='load vf_themes_inventor\nwait 180\ndeveloper 1\necho INVENTORY_LEGACY\nvf_reference\nwait 35\nvf_animation_time 0\n'+snap('legacy_migrated')
    s+='quit\n';log=run_cfg('vf_inventory_test',s,captures=captures,timeout=140)
    def section(key):return log.split(key,1)[1].split('INVENTORY_',1)[0]
    assert 'skins=182,182,182,182,182'in section('INVENTORY_FILTER_ONLY')
    assert 'skins=188,182,182,182,182'in section('INVENTORY_ONE_HEAD')
    for theme,index in [('roman_inventor',188),('dieselpunk',189)]:assert 'skins='+','.join([str(index)]*5)in section('INVENTORY_OUTFIT_'+theme)
    top=section('INVENTORY_TOP_CLICK');assert 'receiver=r01_receiver_arch_top__dieselpunk power=r01_power_a__original'in top
    restored=section('INVENTORY_RESTORED');assert 'receiver=r01_receiver_arch_top__dieselpunk'in restored
    assert 'first=13 optic=12 feed=2'in restored
    assert 'receiver=r01_receiver_arch_top__dieselpunk'in section('INVENTORY_BULK_BLOCKED')
    assert 'themed set:'not in section('INVENTORY_BULK_BLOCKED')
    assert 'VFR01 audit: checked=1753 failed=0 parts=12 combinations=191102976'in log
    assert 'VFEquipment audit: objects=1113 passed=1113 failed=0'in log
    assert 'VFState rejected'not in log and 'rejected=0'in log
    assert 'VF equipment: result=6'not in log
    if fixture.exists():
        after=section('INVENTORY_LEGACY');assert 'receiver=r01_receiver_arch__roman-inventor'in after
        assert 'first=12 optic=4 feed=12'in after
    (ROOT/'build/inventory-engine-verification.json').write_text(json.dumps(dict(objects=len(entries),captures=captures,checks=['unique names and exact catalogue IDs for all 948 player objects','collection filter leaves equipment unchanged','a real click changes only the chosen body zone','both new outfits render and equip in five zones','new top chassis selected through pagination and an item row','four magazines fire and reload on the new top chassis','six optics on the offset mount','high item indices and individual finishes survive save/load','bulk lab commands have no effect in gameplay','1753 pairwise assemblies and all 1113 catalog objects load','0.18 save migration when fixture is present']),indent=2))
    print('PASS player inventory:',len(captures),'native captures, 948 named objects, saves and top receiver')

if __name__=='__main__':main()

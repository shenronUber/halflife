"""Real native-engine regression: animation, sockets, save/load and validation."""
import json,re,subprocess,time
from PIL import Image,ImageChops
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT.parent/'runtime/vector-engine'
MOD=ENGINE/'vf_engine'
STEAM='F:/SteamLibrary/steamapps/common/Half-Life'

def fingerprint(path):
    n=2166136261
    for b in path.read_bytes():n=((n^b)*16777619)&0xffffffff
    return n

def run():
    captures=[]
    def capture(name):
        captures.append(name)
        return f'wait 60\nscreenshot scrshots/{name}.png\nwait 4\n'
    script='wait 220\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\nwait 90\nvf_engine_stats\ncmd vf_body_info\n+duck\nwait 100\ncmd vf_body_info\n-duck\nwait 100\n'
    script+=capture('engine_standard')+'vf_skins\nwait 90\nvf_engine_audit\n'
    script+='vf_skin_all 127\nvf_skin_set 2 9\nvf_skin_set 4 0\nvf_skin_commit\nwait 30\nvf_animation_time 0\n'+capture('engine_mixed_idle')
    script+='vf_animation 4\nvf_animation_time 0.2\n'+capture('engine_mixed_walk_a')
    script+='vf_animation_time 0.6\n'+capture('engine_mixed_walk_b')
    script+='vf_skin_set 2 9\nvf_skin_isolate\n'+capture('engine_gloves')+'vf_skin_isolate\n'
    script+='vf_arsenal_select 51\nwait 5\nvf_animation 3\nvf_animation_time 0.35\n'+capture('engine_tfc_animation')
    script+='vf_skins\ncmd vf_skin_camera\n'+capture('engine_mannequin')
    script+='vf_character\nwait 90\nvf_select_slot 12\nvf_next_item\nvf_select_slot 11\nvf_next_item\nvf_commit\nwait 60\nvf_animation 3\nvf_animation_time 0.4\n'+capture('engine_socket_menu')
    script+='vf_character\n'+capture('engine_socket_hand')+'vf_engine_stats\n'
    script+='+attack\nwait 30\n-attack\nwait 50\n+reload\nwait 35\nscreenshot scrshots/engine_socket_reload.png\nwait 4\n-reload\nwait 150\n'
    captures.append('engine_socket_reload')
    sh=fingerprint(ROOT/'generated/skins/skins.txt')
    script+=f'cmd vf_skin_apply {sh} 999 0 0 0 0\nwait 30\ncmd vf_skin_apply 0 0 0 0 0 0\nwait 30\n'
    script+='save vf_engine_smoke\nwait 100\nload vf_engine_smoke\nwait 200\nvf_skins\nwait 100\n'+capture('engine_restored')+'vf_engine_stats\nvf_skins\nwait 10\nquit\n'
    (MOD/'vf_native_test.cfg').write_text(script,encoding='ascii')
    command=[str(ENGINE/'xash3d.exe'),'-rodir',STEAM,'-game','vf_engine','-windowed','-width','1280','-height','720','-console','-nointro','-log','native-test.log','+exec','lab_controls.cfg','+map','vf_range','+exec','vf_native_test.cfg']
    start=time.time();p=subprocess.Popen(command,cwd=ENGINE)
    try:p.wait(timeout=130)
    except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
    assert p.returncode==0,p.returncode
    log=(ENGINE/'native-test.log').read_text(errors='replace')
    for expected in ['VFEngine audit: loaded=210 failed=0 valid=1 rejected_count=1 rejected_socket=1','VFState player=1 skins=127,127,9,127,0 weapon=3','Loading game from save/vf_engine_smoke.sav']:
        assert expected in log,expected
    restored=log.split('Loading game from save/vf_engine_smoke.sav')[-1]
    assert 'VFState player=1 skins=127,127,9,127,0 weapon=3' in restored
    assert 'VFSkin client: result=3 ids=127,127,9,127,0' in log
    assert 'VFSkin client: result=2 ids=127,127,9,127,0' in log
    assert 'VFBody player=1 mins=-16,-16,-36 maxs=16,16,36 rifle=1' in log
    assert 'VFBody player=1 mins=-16,-16,-18 maxs=16,16,18 rifle=1' in log
    stats=re.findall(r'VFEngine: assemblies=(\d+) parts=(\d+) models=(\d+) loads=(\d+) cache_hits=(\d+) poses=(\d+) merged=(\d+) sockets=(\d+) previews=(\d+) rejected=(\d+) textures=(\d+) texture_bytes=(\d+) preview_ms=([\d.]+)',log)
    assert stats and any(int(s[7])>0 and int(s[8])>0 for s in stats),stats
    assert int(stats[0][2])<15,'Model loading must be lazy before the exhaustive audit'
    for name in captures:
        image=MOD/'scrshots'/(name+'.png');assert image.stat().st_mtime>=start and image.stat().st_size>1000,name
    # Exclude labels and the faint world background: the posed character must move.
    a=Image.open(MOD/'scrshots/engine_mixed_walk_a.png').convert('RGB').crop((520,175,1240,575))
    b=Image.open(MOD/'scrshots/engine_mixed_walk_b.png').convert('RGB').crop((520,175,1240,575))
    changed=sum(max(pixel)>30 for pixel in ImageChops.difference(a,b).getdata())
    assert changed>500,('Animation did not advance visibly',changed)
    report={'test':'native-engine','checks':['210 MDL assets accepted by the native API','invalid assembly count and missing socket rejected','native idle/walk and TFC animation captured','single mannequin assembly and socket component rendered','shoot/reload exercised','invalid appearance rejected atomically','server loadout restored after save/load','lazy model loading before audit'],'stats':stats,'captures':captures}
    report['animation_changed_pixels']=changed
    report['checks'].append('SDK standing and crouching collision hulls preserved after changing the player model')
    (ROOT/'build/native-engine-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS: native engine regression; '+str(len(captures))+' screenshots',flush=True)

if __name__=='__main__':run()

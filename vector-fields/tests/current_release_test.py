"""Validate the canonical release deployment in the native runtime."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release import VERSION, startup,verify_deployment
from library_engine_test import ROOT, MOD, run_cfg, click


def run():
    assert json.loads((MOD/'vf/version.json').read_text(encoding='utf-8-sig')) == VERSION
    assert 'Vector Fields / '+VERSION['version'] in (MOD/'gameinfo.txt').read_text()
    deployed = (MOD/'vf_start.cfg').read_text()
    assert deployed == startup(), 'Main launcher must deploy the current inventory startup'
    verified=verify_deployment(MOD)
    compared=verified['models']
    script = 'developer 1\n'+deployed+'wait 30\nscreenshot scrshots/current_release_menu.png\n'+click(1220,40)
    script += 'cmd vf_skin_camera\nwait 40\nscreenshot scrshots/current_release_pair.png\nwait 10\necho CURRENT_RELEASE_REOPEN\nvf_reference\nwait 30\nvf_item r01_receiver_arch_top__dieselpunk\nvf_commit\nwait 30\n'+click(1220,40)
    script += 'save vf_current_release_test\nwait 40\nload vf_current_release_test\nwait 180\ndeveloper 1\nvf_engine_stats\nquit\n'
    log = run_cfg('vf_current_release_test', script, captures=['current_release_menu','current_release_pair'], timeout=65)
    assert 'VFState player=1 skins=182,182,182,182,182 weapon=' in log
    reopened = log.split('CURRENT_RELEASE_REOPEN')[-1]
    assert 'VFR01 styles accepted: player=1 first=13 optic=0 feed=0' in reopened
    assert 'Loading game from save/vf_current_release_test.sav' in log
    restored = log.split('Loading game from save/vf_current_release_test.sav')[-1]
    assert 'VFState player=1 skins=182,182,182,182,182 weapon=' in restored
    assert 'VFR01 state: player=1 first=13 optic=0 feed=0' in restored
    assert 'VFAppearance state: player=1 mode=0' in restored
    assert 'VFState rejected' not in log and 'rejected=0' in log
    report = dict(version=VERSION['version'], runtime=VERSION['runtime_mod'], models_hash_verified=compared, artifacts_hash_verified=verified['files'],
                  checks=['canonical startup and release metadata deployed', 'client/server, catalogs, effects and all character, R01 and third-person model hashes match runtime',
                          'startup opens the inventory without applying a preset', 'equipping a named top receiver preserves all other items',
                          'named receiver and fixed finish survive save/load'], captures=['current_release_menu.png','current_release_pair.png'])
    (ROOT/'build/current-release-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS current release',VERSION['version'],compared,'deployed model hashes; native startup, finish change and save/load')

if __name__ == '__main__':
    run()

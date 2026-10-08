"""Validate the canonical release deployment in the native runtime."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release import VERSION, startup
from library_engine_test import ROOT, MOD, run_cfg, click


def run():
    assert json.loads((MOD/'vf/version.json').read_text(encoding='utf-8-sig')) == VERSION
    assert 'Vector Fields / '+VERSION['version'] in (MOD/'gameinfo.txt').read_text()
    deployed = (MOD/'vf_start.cfg').read_text()
    assert deployed == startup(), 'Main launcher must deploy the current release preset'
    compared = 0
    for source_dir, destination in [('personas', 'vf_skins'), ('r01', 'vf_r01')]:
        for model in (ROOT/'generated'/source_dir).glob('*.mdl'):
            target = MOD/'models'/destination/model.name
            assert target.is_file(), target
            assert hashlib.sha256(model.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest(), model.name
            compared += 1
    assert compared > 25, compared
    script = 'developer 1\n'+deployed+'wait 30\nscreenshot scrshots/current_release_menu.png\n'+click(1220,40)
    script += 'cmd vf_skin_camera\nwait 40\nscreenshot scrshots/current_release_pair.png\nwait 10\necho CURRENT_RELEASE_REOPEN\nvf_reference\nwait 30\nvf_reference_style 8\nvf_commit\nwait 30\nvf_reference_style 7\nvf_commit\nwait 30\n'+click(1220,40)
    script += 'save vf_current_release_test\nwait 40\nload vf_current_release_test\nwait 180\ndeveloper 1\nvf_engine_stats\nquit\n'
    log = run_cfg('vf_current_release_test', script, captures=['current_release_menu','current_release_pair'], timeout=65)
    assert 'VFState player=1 skins=183,183,183,183,183 weapon=' in log
    reopened = log.split('CURRENT_RELEASE_REOPEN')[-1]
    assert 'VFR01 styles accepted: player=1 first=8 optic=8 feed=8' in reopened
    assert 'Loading game from save/vf_current_release_test.sav' in log
    restored = log.split('Loading game from save/vf_current_release_test.sav')[-1]
    assert 'VFState player=1 skins=183,183,183,183,183 weapon=' in restored
    assert 'VFR01 state: player=1 first=7 optic=7 feed=7' in restored
    assert 'VFAppearance state: player=1 mode=0' in restored
    assert 'VFState rejected' not in log and 'rejected=0' in log
    report = dict(version=VERSION['version'], runtime=VERSION['runtime_mod'], models_hash_verified=compared,
                  checks=['canonical startup and release metadata deployed', 'all generated character and R1 model hashes match runtime',
                          'new character and matching R1 equipped together', 'changing R1 finish preserves equipped GIGN pieces',
                          'matching pair survives save/load'], captures=['current_release_menu.png','current_release_pair.png'])
    (ROOT/'build/current-release-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS current release',VERSION['version'],compared,'deployed model hashes; native startup, finish change and save/load')

if __name__ == '__main__':
    run()

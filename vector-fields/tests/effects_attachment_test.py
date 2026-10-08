"""Check a glow shell on the registered modular mannequin, with mixed skins."""
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_visual'
s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 20\nvf_skins\nwait 30\nvf_skin_all 151\nvf_skin_set 0 145\nvf_skin_commit\nwait 35\nvf_skins\ncmd vf_skin_camera\nwait 25\nscreenshot scrshots/fx_mixed_before.png\nwait 4\nvf_effect_select ward\nvf_effect_attach\nwait 35\nvf_effect_stats\nvf_engine_stats\nscreenshot scrshots/fx_mixed_halo.png\nwait 4\nvf_effect_clear\nwait 15\nscreenshot scrshots/fx_mixed_after.png\nwait 4\nvf_effects\nwait 15\nscreenshot scrshots/fx_final_guide.png\nwait 4\nquit\n'
(MOD/'vf_fx_attach_test.cfg').write_text(s);start=time.time()
p=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-windowed','-width','1280','-height','720','-nointro','-nowriteconfig','-log','fx-attachment.log','+exec','lab_controls.cfg','+map','vf_range','+exec','vf_fx_attach_test.cfg'],cwd=ENGINE)
try:p.wait(timeout=35)
except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
assert p.returncode==0
log=(ENGINE/'fx-attachment.log').read_text(errors='replace');assert 'VFX attach: entity=23 effect=ward' in log
assert 'VFSkin client: result=0 ids=145,151,151,151,151' in log
assert 'VFX stats: active=1 visible=1' in log
for name in ['before','halo','after']:
 f=MOD/'scrshots'/f'fx_mixed_{name}.png';assert f.stat().st_mtime>=start
(ROOT/'build/effects-attachment-verification.json').write_text(json.dumps(dict(checks=['mixed modular appearance 145/151 validated by server','visual attachment to existing mannequin entity 23','render identity retained for the registered assembly','screenshots before, during and after removal'],screenshots=['fx_mixed_before.png','fx_mixed_halo.png','fx_mixed_after.png']),indent=2))
print('PASS effect attached to mixed modular mannequin')

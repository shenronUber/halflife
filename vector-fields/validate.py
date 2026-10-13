"""Run the maintained validation suites. Native suites require a deployed release."""
import argparse
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SUITES={
 'integration':[
  ['tests/release_integration_test.py','wallrun'],
  ['tests/release_integration_test.py','intent'],
  ['tests/release_integration_test.py','wallrun_network'],
  ['tests/release_integration_test.py','walljump'],
  ['tests/release_integration_test.py','reload'],
  ['tests/release_integration_test.py','walk'],
  ['tests/release_integration_test.py','pose_strike'],
  ['tests/release_integration_test.py','melee'],
  ['tests/release_integration_test.py','melee_network'],
  ['tests/release_integration_test.py','combat'],
  ['tests/test_room_native_test.py'],
  ['tests/combined_room_native_test.py'],
  ['tests/modular_native_test.py'],['tests/modular_multiplayer_test.py'],['tests/modular_launch_test.py'],
  ['tests/tile_laboratory_native_test.py'],
  ['tests/tile_laboratory_network_test.py'],
  ['tests/atmosphere_native_test.py'],
  ['tests/modular_ambience_test.py','--native'],
  ['tests/pose_cache_native_test.py'],
  ['tests/current_release_test.py']],
 'unit':[
  ['validate.py','--unit-worker'],
  ['model_contract.py','--check'],['contract_documentation.py','--check'],['tests/status_renderer_update_test.py']],
 'policy':[['cpp_tests.py']],
 'assets':[
  ['tests/tile_laboratory_assets_test.py'],
  ['tests/atmosphere_assets_test.py'],
  ['tests/modular_ambience_test.py'],
  ['tests/headgear_assets_test.py'],['tests/headgear_feedback_test.py'],
  ['tests/weapon_inspect_clearance_test.py'],
  ['tests/weapon_melee_geometry_test.py'],
  ['tests/new_personas_test.py','--assets'],
  ['tests/artisan_sets_test.py','--assets'],
  ['tests/test_room_assets_test.py'],['tests/fragment_finish_assets_test.py'],
  ['tests/death_sounds_test.py','--mode','assets'],
  ['tests/death_motion_test.py','--assets'],['tests/death_atlas_test.py','--assets'],['tests/external_death_animations_test.py','--assets'],['tests/death_visual_native_test.py','--assets'],['tests/wound_textures_test.py','--assets'],
  ['tests/death_voice_assets_test.py'],
  ['tests/status_decals_assets_test.py'],
  ['tests/model_contract_assets_test.py'],['tests/traversal_assets_test.py'],
  ['tests/first_person_test.py','--mode','assets'],['tests/operator_rig_test.py'],
  ['tests/reference_extensions_test.py','--mode','assets'],['tests/reference_chassis_test.py','--mode','assets'],
  ['tests/r01_fitted_assets_test.py'],
  ['tests/r01_finish_revision_test.py'],
  ['tests/reference_themes_test.py','--mode','assets'],['tests/reference_platform_test.py','--mode','assets'],
  ['tests/foregrip_assets_test.py'],['tests/third_person_assets_test.py'],['tests/weapon_fx_test.py','--mode','assets']],
 'native':[
  ['tests/modular_native_test.py'],['tests/modular_launch_test.py'],
  ['tests/combat_regression_native_test.py'],['tests/player_pose_native_test.py'],
  ['tests/weapon_inspect_native_test.py'],
  ['tests/weapon_melee_native_test.py'],
  ['tests/headgear_native_test.py'],['tests/headgear_action_native_test.py'],
  ['tests/headgear_body_regression_test.py'],['tests/headgear_feedback_test.py','--native'],
  ['tests/first_person_motion_native_test.py'],['tests/headgear_f4_native_test.py'],
  ['tests/new_personas_test.py'],
  ['tests/artisan_sets_test.py'],
  ['tests/traversal_native_test.py'],['tests/traversal_posture_native_test.py','--encode'],
  ['tests/traversal_slide_combat_native_test.py','--slide-feet'],['tests/slide_presentation_native_test.py'],
  ['tests/traversal_slide_feedback_test.py','--installed'],
  ['tests/traversal_save_native_test.py'],
  ['tests/test_room_native_test.py'],['tests/death_voice_native_test.py'],
  ['tests/fragment_finish_native_test.py'],
  ['tests/death_automatic_native_test.py'],['tests/death_sounds_test.py','--mode','native'],['tests/death_blood_native_test.py'],
  ['tests/death_motion_test.py'],['tests/death_atlas_test.py'],['tests/death_atlas_test.py','--manual'],['tests/external_death_animations_test.py'],['tests/death_visual_native_test.py'],['tests/death_ui_native_test.py'],['tests/wound_textures_test.py'],
  ['tests/current_release_test.py'],['tests/architecture_engine_test.py'],['tests/inventory_engine_test.py'],
  ['tests/reference_platform_test.py','--mode','native'],['tests/foregrip_native_test.py'],
  ['tests/status_feedback_test.py','--mode','native']],
 'multiplayer':[
  ['tests/modular_multiplayer_test.py'],
  ['tests/weapon_melee_network_test.py'],
  ['tests/headgear_action_network_test.py'],
  ['tests/traversal_multiplayer_test.py'],
  ['tests/death_visual_multiplayer_test.py'],
  ['tests/third_person_native_test.py'],['tests/r01_styles_multiplayer_test.py'],
  ['tests/weapon_fx_multiplayer_test.py'],['tests/status_voice_multiplayer_test.py'],
  ['tests/status_feedback_test.py','--mode','multiplayer']],
}


def run(suites):
 results=[]
 for suite in suites:
  for arguments in SUITES[suite]:
   command=[sys.executable]+([str(ROOT/arguments[0])]+arguments[1:] if arguments[0].endswith('.py') else arguments)
   print(f'[{suite}] '+ ' '.join(arguments),flush=True);started=time.monotonic()
   result=subprocess.run(command,cwd=ROOT.parent)
   results.append(dict(suite=suite,test=arguments[0],passed=result.returncode==0,seconds=round(time.monotonic()-started,2)))
   # Stop at the failing contract; downstream native results would be misleading.
   if result.returncode:break
  if results and not results[-1]['passed']:break
 report=dict(suites=suites,passed=all(r['passed'] for r in results),results=results)
 path=ROOT/'build'/('validation-'+'-'.join(suites)+'.json');path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(report,indent=2),encoding='utf-8')
 return 0 if report['passed'] else 1


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--suite',choices=list(SUITES)+['all'],action='append');p.add_argument('--list',action='store_true');p.add_argument('--unit-worker',action='store_true',help=argparse.SUPPRESS);args=p.parse_args()
 if args.unit_worker:
  tests=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='*_unit_test.py')
  if not tests.countTestCases():raise RuntimeError('Unit discovery found no tests')
  sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(tests).wasSuccessful() else 1)
 if args.list:print(json.dumps(SUITES,indent=2));sys.exit(0)
 selected=args.suite or ['unit','policy','assets','integration']
 if 'all' in selected:selected=['unit','policy','assets','integration','native','multiplayer']
 sys.exit(run(list(dict.fromkeys(selected))))

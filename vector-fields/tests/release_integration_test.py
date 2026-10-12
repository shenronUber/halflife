"""Focused release gates always consume the same complete candidate bundle."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
def run(case):
 import integration_native_test as audit
 if os.environ.get('VF_RELEASE_BUNDLE'):
  audit.SNAP=Path(os.environ['VF_RELEASE_BUNDLE'])
 else:
  receipt=json.loads((ROOT.parent/'runtime/vector-engine/vf_visual/vf/release-bundle.json').read_text())
  audit.SNAP=Path(receipt['candidate'])/'fixture'
  from build_release import inputs,identity
  assert receipt['source_identity']==identity(inputs()),'Build a current candidate before validating changed sources'
 audit.OUT=Path(os.environ.get('VF_RELEASE_CANDIDATE',ROOT/'build/release-integration'))/'integration'
 if case=='reload':
  import reload_transition_native_test
  reload_transition_native_test.run(audit.SNAP,audit.OUT/'reload')
 elif case=='intent':
  import wallrun_intent_native_test
  wallrun_intent_native_test.run()
 else:audit.run(case)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('case');run(p.parse_args().case)

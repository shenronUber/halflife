"""Compatibility launcher: the modular map now runs in the main game."""
import argparse,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LIVE=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
MOD_NAME='vf_visual'
SERVER=Path(os.environ.get('VF_RELEASE_SDK',ROOT/'build'))/'server/hl.dll'
CLIENT=LIVE/MOD_NAME/'cl_dlls/client.dll'
def prepare():
 if not os.environ.get('VF_TEST_ENGINE'):
  from build_release import ensure_published
  ensure_published()
 mod=LIVE/MOD_NAME
 for p in [mod/'dlls/hl.dll',mod/'cl_dlls/client.dll',mod/'maps/vf_modular.bsp']:
  if not p.exists():raise FileNotFoundError(p)
 return mod
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');p.add_argument('--seed',type=int,default=0);a=p.parse_args()
 if not 0<=a.seed<=2147483647:p.error('seed must be 0..2147483647')
 prepare()
 if not a.prepare_only:
  from build_release import launch
  return launch('vf_modular',seed=a.seed)
 return 0
if __name__=='__main__':raise SystemExit(main())

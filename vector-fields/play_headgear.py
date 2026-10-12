"""Open six headgear designs and their static wearing/stowage poses in the workshop."""
import argparse
import json
import subprocess

from build_headgear import build, ROOT
from headgear_preview import stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helmet', choices=('none','riot','riot-down','riot-up','spartan',
                                            'nvg-red','nvg-red-down','nvg-red-up',
                                            'nvg-green','nvg-green-down','nvg-green-up',
                                            'ballistic','ballistic-down','ballistic-up',
                                            'gas-mask','gas-mask-down','gas-mask-up'), default='riot')
    parser.add_argument('--devtest',action='store_true',help='Use marked palm/back/arm diagnostic textures')
    args = parser.parse_args(); build(ensure=True)
    engine,mod=stage('headgear-preview')
    if args.devtest:
        from headgear_devtest import install
        install(mod)
    if b'gas-mask-up' not in (mod / 'cl_dlls/client.dll').read_bytes():
        raise RuntimeError('Build the current client first; all twelve headgear choices are required')
    baseline = json.loads((ROOT / 'generated/personas/manifest.json').read_text())['base_entry']
    cfg = mod / 'vf_headgear_start.cfg'
    cfg.write_text('wait 180\ndeveloper 1\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\n'
                   f'vf_skins\nwait 35\nvf_skin_tab 0\nvf_skin_filter 7\nvf_skin_all {baseline}\n'
                   'vf_skin_commit\nwait 25\nvf_skin_isolate\nvf_animation_time 0\n'
                   f'vf_headgear {args.helmet}\n', encoding='ascii')
    if args.devtest and args.helmet not in ('none','spartan'):
        item = 'helmet_riot' if args.helmet.startswith('riot') else 'helmet_ballistic' if args.helmet.startswith('ballistic') else 'helmet_nvg_red' if args.helmet.startswith('nvg-red') else 'helmet_nvg_green' if args.helmet.startswith('nvg-green') else 'helmet_gas_mask'
        cfg.write_text('wait 180\ndeveloper 1\nweapon_9mmAR\nwait 45\n'
                       f'vf_operator\nwait 25\nvf_item {item}\nvf_commit\nwait 25\nvf_operator\nwait 10\n'
                       + ('vf_headgear_toggle\nwait 90\n' if args.helmet.endswith('-up') else '')
                       + 'firstperson\nbind h "vf_headgear_toggle"\nbind F9 "thirdperson"\nbind F10 "firstperson"\n'
                       'cam_snapto 1\ncam_idealdist 42\ncam_idealyaw 225\ncam_idealpitch 0\n'
                       'echo DEVTEST: orange=paume bleu=dos jaune=pouce; H=geste F9=troisieme F10=premiere\n',encoding='ascii')
    # Keep the parent alive: native_workspace archives/cleans only after the
    # interactive engine closes, never while DLLs/media are in use.
    result=subprocess.run([str(engine / 'xash3d.exe'),'-ip','127.0.0.1','-noip6', '-rodir', 'F:/SteamLibrary/steamapps/common/Half-Life',
                      '-game', mod.name, '-borderless', '-width', '1920', '-height', '1080',
                      '-console', '-nointro', '-nowriteconfig', '-log', 'headgear-preview.log',
                      '+exec', 'lab_controls.cfg', '+map', 'vf_range', '+exec', cfg.name], cwd=engine)
    if result.returncode:
        raise RuntimeError(f'Headgear preview exited with code {result.returncode}')


if __name__ == '__main__':
    main()

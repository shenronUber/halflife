"""Single release identity and startup preset used by the normal launcher."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VERSION=json.loads((ROOT/'version.json').read_text(encoding='utf-8-sig'))

def startup(theme=None):
 theme=theme or VERSION['default_theme']
 pack=json.loads((ROOT/'data/gameplay-content.json').read_text())['collections']
 entry=next(t for t in pack if t['id']==theme)
 styles=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))['styles']
 style=next(t['skin']for t in styles if t['id']==theme)
 return (f'wait 180\ncon_notifytime 0\nweapon_9mmAR\nvf_operator\nwait 30\n'
         f'vf_operator_set {entry["key"]}\nvf_commit\nwait 30\n'
         f'vf_reference\nwait 30\nvf_reference_style {style}\nvf_commit\nwait 30\n'
         'vf_operator\nwait 30\nvf_animation_time 0\n')

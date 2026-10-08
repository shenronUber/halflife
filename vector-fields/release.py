"""Single release identity and startup preset used by the normal launcher."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VERSION=json.loads((ROOT/'version.json').read_text(encoding='utf-8-sig'))

def startup(theme=None):
 theme=theme or VERSION['default_theme']
 pack=json.loads((ROOT/'assets/expeditions-01.json').read_text(encoding='utf-8-sig'))['themes']
 entry=next(t for t in pack if t['id']==theme)
 personas=json.loads((ROOT/'generated/personas/manifest.json').read_text(encoding='utf-8'))
 persona=next(t for t in personas['themes']if t['key']=='persona_'+entry['key'])['id']
 styles=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))['styles']
 style=next(t['skin']for t in styles if t['id']==theme)
 return (f'wait 180\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\n'
         f'vf_reference 0\nwait 30\nvf_reference_style {style}\nvf_commit\nwait 30\n'
         f'vf_skins\nwait 30\nvf_skin_tab 0\nvf_skin_filter 7\nvf_skin_all {persona}\n'
         'vf_skin_commit\nwait 30\nvf_animation_time 0\nvf_ui_pointer 1220 590 1\nwait 3\n'
         'vf_ui_pointer 1220 590 0\nwait 12\n'+'vf_rotate\n'*6)

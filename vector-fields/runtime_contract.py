"""Read the equipment contract directly from the declarations used by both DLLs."""
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def equipment_contract():
    header = (PROJECT / 'game_shared/vf_loadout.h').read_text()
    source = (PROJECT / 'game_shared/vf_loadout.cpp').read_text()
    values = {key: int(re.search(r'\b' + key + r'\s*=\s*(\d+)', header)[1])
              for key in ('SlotCount', 'WeaponEnd', 'HelmetSlot', 'Protocol',
                          'BuildMessageSize', 'StateMessageSize')}
    declaration = re.search(r'SlotKeys\[SlotCount\]\s*=\s*\{(.*?)\}', source, re.S)
    values['slots'] = re.findall(r'"([a-z_]+)"', declaration[1])
    if len(values['slots']) != values['SlotCount']:
        raise ValueError('Slot names and SlotCount disagree')
    return values

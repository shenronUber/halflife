"""Shared serialization for the weapon finish catalog, used by both generators."""
def weapon_style_catalog(styles,content):
    collections={c['id']:c for c in content['collections']+content.get('weapon_collections',[])}
    if {s['id'] for s in styles}!=set(collections):
        raise ValueError('Weapon finishes and cosmetic collections must match')
    return ''.join(f"{s['skin']}|{s['id'].replace('-', '_')}|{collections[s['id']]['name']}|0|r01|{s['skin']}\n" for s in styles)

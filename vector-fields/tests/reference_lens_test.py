"""Lens regression: original image on glass, no added yellow cross, native render."""
import sys,struct,json,hashlib
from pathlib import Path
from library_engine_test import run_cfg,click,ROOT
sys.path.insert(0,str(ROOT))
from studio_assets import Studio
import build_modular as base
s=Studio(ROOT/'generated/r01/r01_optic_a.mdl');n,idx=struct.unpack_from('<ii',s.data,180)
flags={t[0]:struct.unpack_from('<i',s.data,idx+i*80+64)[0]for i,t in enumerate(s.textures)}
assert flags['r01_t11.bmp']&32 and all(v&32 for k,v in flags.items()if k.endswith('_t11.bmp'))
lens=[tri for mat,tri in s.mesh()if s.textures[mat][0]=='r01_t11.bmp'];assert len(lens)==12
# StudioMDL crops unused texels and remaps compiled UVs to [0,1]. Check source UVs.
_,_,triangles=base.read_smd(ROOT/'generated/r01/r01_optic_a.smd')
uv=[float(v)for mat,rows in triangles if mat=='r01_t11.bmp'for row in rows for v in row.split()[-2:]]
assert len(uv)==72 and min(uv)>=.249 and max(uv)<=.751
assert all(0<t[1]<=256 and 0<t[2]<=256 for t in s.textures)
yellow=[v['p'][2]for mat,tri in s.mesh()if s.textures[mat][0]=='r01_t02.bmp'for v in tri];assert max(yellow)<4.4
script='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\nvf_reference 0\nwait 35\nvf_select_slot 16\nvf_animation_time 0\n'+click(1000,602)+'wait 20\nscreenshot scrshots/r01_lens_final_isolated.png\nwait 5\n'
script+=click(1000,602)+click(1110,690)+'wait 25\n'+click(1220,40)+'wait 20\n+forward\nwait 20\n-forward\nwait 20\nscreenshot scrshots/r01_lens_final_hand.png\nwait 5\nvf_reference_audit\nvf_engine_stats\nquit\n'
log=run_cfg('vf_r01_lens_final',script,captures=['r01_lens_final_isolated','r01_lens_final_hand'],timeout=55)
assert 'VFR01 audit: combinations=8192 failed=0 parts=12'in log and 'rejected=0'in log
report=dict(checks=['original lens image embedded in MDL','source UVs use the glass region of the image','all lens skin variants use additive glass','12 lens triangles form the two faces of the window','yellow geometry confined to lower frame; no overlaid cross','8192 native assemblies accepted'],captures=['r01_lens_final_isolated','r01_lens_final_hand'],resolution=[1920,1080],lens_materials={k:v for k,v in flags.items()if k.endswith('_t11.bmp')},model_sha256=hashlib.sha256(s.data).hexdigest())
(ROOT/'build/reference-lens-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS final lens: image retained, additive glass, no yellow cross; 8192 assemblies')

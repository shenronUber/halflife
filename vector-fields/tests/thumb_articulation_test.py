"""Prove the appended thumb joint preserves legacy clips and rest geometry."""
import json,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_info
from thumb_articulation import NAME,rle
from build_weapon_melee import PROJECT,digest
OUT=ROOT/'build/fist-refinement';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine/vf_visual'

def run():
    records=json.loads((OUT/'articulated-models.json').read_text());results=[]
    for record in records:
        old=Studio(LIVE/record['relative']);new=Studio(CANDIDATE/record['relative'])
        assert old.names==new.names[:-1] and new.names[-1]==NAME
        n=len(old.names);assert old.parents==new.parents[:-1]
        ob=struct.unpack_from('<i',old.data,144)[0];nb=struct.unpack_from('<i',new.data,144)[0]
        assert old.data[ob:ob+112*n]==new.data[nb:nb+112*n]
        assert old.sequences==new.sequences
        _,os=struct.unpack_from('<ii',old.data,164);_,ns=struct.unpack_from('<ii',new.data,164)
        for i in range(len(old.sequences)):
            od=old.data[os+176*i:os+176*(i+1)];nd=new.data[ns+176*i:ns+176*(i+1)]
            assert od[:124]+od[128:]==nd[:124]+nd[128:]
            a=sequence_info(old,i);b=sequence_info(new,i)
            for blend in range(a['blends']):
                for bone in range(n):
                    oa=a['animation']+(blend*n+bone)*12;na=b['animation']+(blend*(n+1)+bone)*12
                    for x,y in zip(struct.unpack_from('<6H',old.data,oa),struct.unpack_from('<6H',new.data,na)):
                        assert bool(x)==bool(y)
                        if x:assert rle(old.data,oa+x,a['frames'])==rle(new.data,na+y,b['frames'])
                tip=b['animation']+(blend*(n+1)+n)*12
                assert new.data[tip:tip+12]==bytes(12)
        maximum=0.;normals=0.;triangles=0
        for part,(_,count,_) in enumerate(old.parts):
            for sub in range(count):
                choices={p:-1 for p in range(len(old.parts))};choices[part]=sub
                om=old.mesh(choices);nm=new.mesh(choices);assert len(om)==len(nm)
                for (ot,ov),(nt,nv) in zip(om,nm):
                    assert ot==nt
                    for x,y in zip(ov,nv):
                        maximum=max(maximum,float(np.max(np.abs(x['p']-y['p']))))
                        normals=max(normals,float(np.max(np.abs(x['n']-y['n']))))
                        assert np.array_equal(x['uv'],y['uv'])
                    triangles+=1
        assert maximum<1e-5 and normals<1e-6
        results.append(dict(file=record['relative'],sha256=digest(new.path),legacy_sequences=len(old.sequences),
                            triangles=triangles,rest_position_error=maximum,normal_error=normals))
    assert len(results)>=4
    report=dict(passed=True,models=results,checks=['all original bone records identical','every original sequence descriptor/event unchanged',
                'every original RLE animation channel identical across every blend','new joint static on legacy clips',
                'all body submodels retain rest geometry, normals, UVs and textures'])
    (OUT/'thumb-preservation.json').write_text(json.dumps(report,indent=2))
    print('PASS thumb articulation:',len(results),'models; every legacy channel identical; all rest meshes preserved',flush=True)
    return report
if __name__=='__main__':run()

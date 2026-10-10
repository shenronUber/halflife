"""Check fitted animation seams, anatomical hitboxes and the visible corpse fallback."""
import itertools,json,struct,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_personas import ASSETS,OUT,donor
from studio_assets import Studio,canonical
from personas_engine_test import geometry


def boxes(studio):
    count,offset=struct.unpack_from('<ii',studio.data,156)
    result=[]
    for i in range(count):
        bone,group,*bounds=struct.unpack_from('<ii6f',studio.data,offset+i*32)
        corners=np.array([(studio.bind[bone]@np.r_[p,1])[:3]for p in itertools.product(*zip(bounds[:3],bounds[3:]))])
        result.append((canonical(studio.names[bone]),group,corners.min(0),corners.max(0)))
    return result


def main():
    report=geometry()
    config=json.loads((ASSETS/'personas.json').read_text())
    source=Studio(donor(config)['path']);rig=Studio(OUT/'persona_rig.mdl')
    expected,actual=[b for b in boxes(source) if b[1]!=8],boxes(rig)
    assert len(expected)==len(actual)==20
    assert set(b[1] for b in actual)==set(range(1,8)),'only the seven anatomical groups; no invisible donor shield'
    for (bone,group,lo,hi),(other,hitgroup,minimum,maximum) in zip(expected,actual):
        assert bone==other and group==hitgroup,(bone,other,group,hitgroup)
        assert np.allclose(lo,minimum,atol=.02)and np.allclose(hi,maximum,atol=.02),(bone,lo,minimum,hi,maximum)
    assert any(b=='head'and g==1 for b,g,_,_ in actual),'head damage group preserved'
    # A hidden carrier is also the server corpse model: it must contain a body.
    mesh=rig.mesh();points=np.array([v['p']for _,tri in mesh for v in tri])
    assert len(mesh)>=740 and np.ptp(points,axis=0)[2]>60
    report.update(anatomical_hitboxes=len(actual),head_hitgroup=1,corpse_body_triangles=len(mesh))
    (OUT.parents[1]/'build/operator-rig-verification.json').write_text(json.dumps(report,indent=2))
    print('PASS operator rig:',len(actual),'donor hitboxes, visible body,',report['skin_zone_checks'],'skin zones and',report['animation_samples'],'animation poses')

if __name__=='__main__':main()

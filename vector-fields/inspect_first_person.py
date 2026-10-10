"""Export the compiled FP meshes to a self-contained orbit/UV inspection page."""
import base64, io, json
from pathlib import Path
import numpy as np
from PIL import Image
from studio_assets import Studio
import build_modular as base
import build_reference_platforms as pf
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/r01'


def png(tex):
    _,w,h,pix,pal=tex
    im=Image.frombytes('P',(w,h),pix);im.putpalette(pal)
    b=io.BytesIO();im.convert('RGB').save(b,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()


def export():
    names,parents,bind=base.skeleton(OUT/'mp40_hands.smd')
    parts={kind:Studio(OUT/f'r01_fp_{kind}.mdl')for kind in ('gloves','sleeves')}
    poses={}
    for side in ('left','right'):
        inv=np.linalg.inv(bind[12 if side=='left'else 6]);groups=[]
        for kind,model in parts.items():
            vertices=[]
            for _,rows in model.mesh():
                if (np.mean([r['p'][0]for r in rows])>0)!=(side=='left'):continue
                for r in rows:
                    p=(inv@np.r_[r['p'],1])[:3];n=inv[:3,:3]@r['n']
                    vertices.append([*p,*n,*r['uv']])
            groups.append(dict(kind=kind,vertices=vertices))
        poses[side]=groups
    for label,file,frame in [('side_idle','side_idle',0),('side_reload','side_reload',70),('top_reload','top_reload',70),('top_extract','top_reload',34),('top_exchange','top_reload',44),('top_insert','top_reload',83)]:
        _,frames=pf.read_frames(OUT/(file+'.smd'));g=pf.globals_of(frames[frame],parents);groups=[]
        for kind,model in parts.items():
            vertices=[]
            for _,rows in model.mesh():
                for r in rows:
                    bone=next(i for i,n in names.items()if n==model.names[r['b']]);m=g[bone]@np.linalg.inv(model.bind[r['b']])
                    p=(m@np.r_[r['p'],1])[:3];n=m[:3,:3]@r['n']
                    vertices.append([*p,*n,*r['uv']])
            groups.append(dict(kind=kind,vertices=vertices))
        poses[label]=groups
    data=dict(poses=poses,textures={k:[png(m.textures[m.skin[i]])for i in range(14)]for k,m in parts.items()},themes=json.loads((OUT/'first-person.json').read_text())['themes'])
    template=(ROOT/'first_person_inspector.template.html').read_text(encoding='utf-8-sig')
    path=ROOT/'build/first-person-inspector.html'
    path.write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'))),encoding='utf-8')
    print(path)
    return data


if __name__=='__main__':export()

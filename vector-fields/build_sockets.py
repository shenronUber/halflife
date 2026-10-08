"""Compile the HK416 muzzle as an independent, bone-local socket component."""
import json,shutil
from pathlib import Path
import numpy as np
from build_modular import OUT,ROOT,read_smd,skeleton,write_smd,compile_model
from studio_assets import Studio

def main():
    source=OUT/'muzzle_suppressor.smd'
    _,names,triangles=read_smd(source)
    _,_,bind=skeleton(source)
    bone=next(i for i,name in names.items() if name=='M16A2')
    inv=np.linalg.inv(bind[bone]);result=[]
    destination=ROOT/'generated/sockets';destination.mkdir(parents=True,exist_ok=True)
    header=['version 1','nodes','0 "module_root" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end']
    for material,rows in triangles:
        out=[]
        for row in rows:
            f=row.split();assert int(f[0])==bone
            p=inv@np.array([*map(float,f[1:4]),1]);n=inv[:3,:3]@np.array(list(map(float,f[4:7])))
            out.append('0 '+' '.join(f'{v:.7f}' for v in [*p[:3],*n,float(f[7]),float(f[8])]))
        result.append((material,out));shutil.copy2(OUT/material,destination/material)
    write_smd(destination/'suppressor.smd',header,result)
    (destination/'idle.smd').write_text('\n'.join(header)+'\n')
    qc=destination/'suppressor.qc'
    qc.write_text('$modelname "suppressor.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body "module" "suppressor"\n$sequence "idle" "idle" fps 1\n')
    model=compile_model(qc);compiled=Studio(model)
    assert len(compiled.names)==1 and np.allclose(compiled.bind[0],np.eye(4),atol=1e-5)
    (destination/'socket-contract.json').write_text(json.dumps({'version':1,'weapon':'models/v_9mmar.mdl','socket':'muzzle','bone':'M16A2','component':'models/vf_modules/suppressor.mdl','offset':[0,0,0],'angles':[0,0,0],'triangles':len(result)},indent=2))
    print('PASS: independent suppressor, identity root, original weapon animation preserved')

if __name__=='__main__':main()

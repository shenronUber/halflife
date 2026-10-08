"""Local kitbash: HK416 receiver/hands/animations with LR-300 magazines.

Inputs are decompiled with the official Xash3D mdldec tool. No animation is
regenerated. Bone indices are mapped by name and the recipient bind pose is kept.
These third-party derivatives are local experiments; author permission is
required before redistribution (see catalog/selection.json).
"""
import collections
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GEN=ROOT/'generated'

def read_smd(path):
    lines=path.read_text().splitlines()
    boundary=lines.index('triangles')
    header=lines[:boundary]
    nodes={}
    for line in lines[lines.index('nodes')+1:]:
        if line=='end': break
        match=re.fullmatch(r'\s*(\d+) "([^"]+)" (-?\d+)',line)
        assert match,line
        nodes[int(match[1])]=match[2]
    triangles=[]
    for i in range(boundary+1,len(lines)-1,4):
        triangles.append((lines[i],lines[i+1:i+4]))
    return header,nodes,triangles

def main():
    recipient=GEN/'hk416'
    donor=GEN/'lr300'
    output=GEN/'hybrid'
    output.mkdir(exist_ok=True)
    for p in recipient.iterdir():
        if p.is_file(): shutil.copy2(p,output/p.name)
    header,hk_nodes,hk_triangles=read_smd(recipient/'HK416_3.smd')
    _,lr_nodes,lr_triangles=read_smd(donor/'LR300_1.smd')
    target_bones={name:i for i,name in hk_nodes.items()}
    kept=[t for t in hk_triangles if t[0]!='mag.bmp']
    removed=len(hk_triangles)-len(kept)
    added=[]
    used_bones=set()
    for material,rows in lr_triangles:
        if material!='F5.bmp': continue
        remapped=[]
        for row in rows:
            fields=row.split()
            name=lr_nodes[int(fields[0])]
            used_bones.add(name)
            fields[0]=str(target_bones[name])
            remapped.append(' '.join(fields))
        added.append(('lr300_mag.bmp',remapped))
    assert removed>0 and added
    for name,triangles in [('HK416_3',kept),('LR300_magazine',added)]:
        text='\n'.join(header+['triangles']+[line for m,rows in triangles for line in [m,*rows]]+['end'])+'\n'
        (output/(name+'.smd')).write_text(text,encoding='ascii')
    shutil.copy2(donor/'F5.bmp',output/'lr300_mag.bmp')
    qc=(recipient/'v_9mmar.qc').read_text()
    qc=qc.replace('$body "studio" "HK416_3"', '$body "studio" "HK416_3"\n$body "magazine" "LR300_magazine"')
    # The classic Valve compiler derives chrome from texture names and does not
    # recognize the extended flag commands emitted by the Xash decompiler.
    qc='\n'.join(line for line in qc.splitlines() if not line.startswith(('$cliptotextures','$flags','$texrendermode')))+'\n'
    (output/'v_9mmar.qc').write_text(qc,encoding='ascii')
    exe=ROOT.parent/'asset-probe'/'tools'/'studiomdl.exe'
    result=subprocess.run([str(exe),'v_9mmar.qc'],cwd=output,capture_output=True,text=True)
    (output/'compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    data=(output/'v_9mmar.mdl').read_bytes()
    assert data[:4]==b'IDST' and struct.unpack_from('<i',data,4)[0]==10
    assert struct.unpack_from('<i',data,164)[0]==9
    report={'recipient':'https://gamebanana.com/mods/640445','donor':'https://gamebanana.com/mods/640447',
            'operation':'Replace HK416 magazine triangles with LR-300 magazine triangles; preserve HK416 animations and HEV hands.',
            'triangles_removed':removed,'triangles_added':len(added),'remapped_bones':sorted(used_bones),
            'animation_sequences':9,'compiled_bytes':len(data),'in_game_verified':False,
            'distribution':'Local experiment. Author permission required before redistribution.'}
    (ROOT/'catalog'/'hybrid.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()

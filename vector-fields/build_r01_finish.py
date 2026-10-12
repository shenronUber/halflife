"""Scoped, reviewed R1 mesh/atlas revisions. Animated carriers are never inputs."""
import hashlib,json,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WORKSHOP=ROOT/'weapon-workshop/polish-2026-10-11'
PREVIOUS=ROOT/'weapon-workshop/finish-2026-10-11'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def approved():
    path=WORKSHOP/'manifest.json'
    return {r['id']:r for r in json.loads(path.read_text())['assets']} if path.exists() else {}
def inputs():
    return [Path(__file__),WORKSHOP/'manifest.json',PREVIOUS/'manifest.json']+[WORKSHOP/ident/'export'/(ident+'.mdl') for ident in approved()]
def is_current(path):
    p=Path(path);r=approved().get(p.stem)
    if not r or not p.is_file():return False
    known={r['sha256'],*r.get('reviewed_previous_sha256',[])}
    # Recognize the previous reviewed files while publishing or rebuilding;
    # both revisions keep the same two physical texture families.
    prior=PREVIOUS/'manifest.json'
    if prior.exists():known.update(v['sha256'] for v in json.loads(prior.read_text())['assets'] if v['id']==p.stem)
    return digest(p) in known
def source(ident):return WORKSHOP/ident/'export'/(ident+'.mdl')

def apply_modules(folder,records=None):
    from studio_assets import Studio
    folder=Path(folder);byid={r['id']:r for r in records or []};audit=[]
    for ident,record in approved().items():
        src=source(ident);dst=folder/(ident+'.mdl');assert digest(src)==record['sha256']
        before=digest(dst)
        if before not in (*record.get('accepted_source_sha256',[]),record['source_sha256'],record['sha256']):
            raise ValueError('R1 model changed since review; revision must be rebased: '+str(dst))
        if before!=record['sha256']:
            # Atomic publication also detaches a previous immutable snapshot.
            tmp=dst.with_suffix('.finish-'+str(os.getpid())+'.tmp');shutil.copy2(src,tmp)
            if digest(dst)!=before:tmp.unlink();raise RuntimeError('Concurrent R1 edit: '+str(dst))
            tmp.replace(dst)
        s=Studio(dst)
        if ident in byid:
            byid[ident].update(triangles=len(s.mesh()),bytes=len(s.data),sha256=record['sha256'],skin_families=14,intrinsic_texture=True,
                              fitted_skin_families=2,geometry_revision='polish-2026-10-11',uv_mapping='unique-atlas-v2')
        audit.append(dict(id=ident,before=before,after=record['sha256'],changed=before!=record['sha256']))
    return audit

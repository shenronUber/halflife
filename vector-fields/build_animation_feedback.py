"""Stage current main, compile body-facing fix and replace only reviewed tracks."""
import json,shutil,struct
from pathlib import Path
import numpy as np
from build_weapon_melee import ROOT,PROJECT,digest,sources
import build_wall_jump_native as sdk
from build_weapon_melee_assets import append_tracks
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of
from traversal_editor import read
from build_reference_platforms import blend
OUT=ROOT/'build/animation-feedback';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'
GESTURES=('vf_wall_jump','vf_wall_jump_turn')

def build():
    CANDIDATE.mkdir(parents=True,exist_ok=True)
    before=sources();live_files=[p for p in LIVE.iterdir()if p.is_file()and(p.suffix.lower()in('.dll','.exe')or p.name=='vector-engine-build.json')]
    live_files += [LIVE/'vf_visual'/p for p in ['dlls/hl.dll','cl_dlls/client.dll','delta.lst']]
    live_files += list((LIVE/'vf_visual/models').rglob('*.mdl'))+[LIVE/'vf_visual/maps/vf_traversal.bsp']
    guard={str(p.relative_to(PROJECT)):digest(p)for p in live_files}
    (OUT/'runtime-before.json').write_text(json.dumps(guard,indent=2))
    sdk.OUT=CANDIDATE;sdk.refresh_game(CANDIDATE/'source')
    assert sources()==before
    for folder in ['models','maps','vf']:shutil.copytree(LIVE/'vf_visual'/folder,CANDIDATE/folder,dirs_exist_ok=True)
    for p in LIVE.iterdir():
        if p.is_file()and(p.suffix.lower()in('.dll','.exe')or p.name=='vector-engine-build.json'):
            target=CANDIDATE/'engine'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.copy2(LIVE/'vf_visual/delta.lst',CANDIDATE/'delta.lst')
    previous=ROOT/'build/crouch-reload/candidate'
    shutil.copytree(previous/'generated',CANDIDATE/'generated',dirs_exist_ok=True)
    shutil.copy2(previous/'assets.json',CANDIDATE/'assets.json')
    for path in (ROOT/'generated/weapon-melee').glob('*.mdl'):shutil.copy2(path,CANDIDATE/'models/vf_melee'/path.name)
    records=[]
    for folder in ['vf_r01','vf_melee']:
        for path in sorted((CANDIDATE/'models'/folder).glob('r01_tp*.mdl')):
            old=Studio(path);tracks=[]
            for name in GESTURES:
                frames=read(ROOT/'assets/animations/traversal-edits/third-person'/(name+'_0.smd'),old)
                held=sequence_frames(old,'vf_hang_idle')[0]
                for i in range(3):
                    t=i/3;t=t*t*(3-2*t)
                    frames[i]=np.array([blend(a,b,t)for a,b in zip(held,frames[i])])
                neutral=sequence_frames(old,'ref_aim_mp5')[0]
                # Rejoin each mount's equipped pose instead of the workshop donor.
                for i in range(16,21):
                    t=(i-16)/4;t=t*t*(3-2*t)
                    frames[i]=np.array([blend(a,b,t)for a,b in zip(frames[i],neutral)])
                frames[:,29:]=sequence_frames(old,name)[:,29:]
                tracks.append((name,frames))
            data=bytearray(append_tracks(old,tracks));n=len(old.sequences);seqoff=struct.unpack_from('<i',data,168)[0]
            for index,(name,frames)in enumerate(tracks):
                entry=seqoff+176*old.sequences.index(name);new=seqoff+176*(n+index)
                data[entry:entry+176]=data[new:new+176];struct.pack_into('<f',data,entry+32,20/.65)
            struct.pack_into('<i',data,164,n);path.write_bytes(data);new=Studio(path)
            assert new.sequences==old.sequences
            error=0
            for name in old.sequences:
                if name in GESTURES:continue
                for b in range(sequence_info(old,name)['blends']):
                    error=max(error,float(np.max(np.abs(sequence_frames(old,name,blend=b)-sequence_frames(new,name,blend=b)))))
            assert error<.001,(path,error)
            for name,frames in tracks:
                actual=sequence_frames(new,name)
                assert np.max(np.abs(actual-frames))<.002
                assert np.max(np.abs(actual[0]-sequence_frames(old,'vf_hang_idle')[0]))<.002,(path,'push-off must begin at held pose')
            records.append(dict(relative=str(path.relative_to(CANDIDATE)),sha256=digest(path),preserved_animation_error=error,replaced=list(GESTURES)))
    (OUT/'tracks.json').write_text(json.dumps(dict(passed=True,models=records),indent=2))
    assets=json.loads((CANDIDATE/'assets.json').read_text())
    for record in assets:
        path=CANDIDATE/record['relative'];record['candidate']=str(path);record['sha256']=digest(path)
        folder='traversal'if record['view']=='first-person'else'third-person'
        shutil.copy2(path,CANDIDATE/'generated'/folder/path.name)
    (CANDIDATE/'assets.json').write_text(json.dumps(assets,indent=2))
    (CANDIDATE/'source-hashes.json').write_text(json.dumps(before,indent=2))
    assert all(digest(PROJECT/p)==h for p,h in guard.items()),'Concurrent main delivery'
    print('PASS current SDK and six dynamic rebound carriers; all other tracks preserved',flush=True)

if __name__=='__main__':build()

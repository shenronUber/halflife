"""Check the firing limb against the actual skinned chest, not an aim formula."""
import re
import numpy as np
from scipy.spatial import ConvexHull
from studio_assets import Studio


class TorsoGuard:
    def __init__(self,path,names):
        skin=Studio(path)
        self.groups={}
        torso=('Bip01 Spine','Bip01 Spine1','Bip01 Spine2','Bip01 Spine3','Bip01 L Arm','Bip01 R Arm')
        for _,triangle in skin.mesh(choices={i:1 for i in range(len(skin.parts))}):
            for vertex in triangle:
                name=skin.names[vertex['b']]
                if name not in torso:continue
                local=np.linalg.inv(skin.bind[vertex['b']])@np.r_[vertex['source'],1]
                self.groups.setdefault(names.index(name),[]).append(local)
        self.groups={bone:np.unique(np.round(points,6),axis=0)for bone,points in self.groups.items()}
        assert 4<=len(self.groups)<=6 and names.index('Bip01 Spine3')in self.groups

    def inspect(self,transforms,shoulder,elbow,wrist):
        points=np.concatenate([(transforms[bone]@local.T).T[:,:3]for bone,local in self.groups.items()])
        planes=ConvexHull(points).equations
        def outside(points):return (points@planes[:,:3].T+planes[:,3]).max(axis=1)
        # The shoulder joint is embedded in the deltoid. Exclude its first
        # four units; the rest of the humerus and the entire forearm must
        # remain outside the torso. Forearm clearance includes its thickness.
        start=min(.5,4/np.linalg.norm(elbow-shoulder))
        upper=np.array([shoulder+t*(elbow-shoulder)for t in np.linspace(start,1,81)])
        fore=np.linspace(elbow,wrist,101)
        return float(outside(upper).min()),float(outside(fore).min())


def native_clearance(text,skin,carrier):
    model=Studio(carrier);guard=TorsoGuard(skin,model.names)
    pattern=(r'VFTraversalArm [^\n]+route=([\d.-]+)\s+'
             r'VFTraversalEnvelope s=([\d.,-]+) e=([\d.,-]+) w=([\d.,-]+) torso=([\d.,-]+)')
    checked=[];bends=[]
    for route,s,e,w,encoded in re.findall(pattern,text):
        if float(route)<.25:continue
        shoulder,elbow,wrist=[np.array([float(v)for v in point.split(',')])for point in (s,e,w)]
        matrices=np.array([float(v)for v in encoded.rstrip(',').split(',')]).reshape(6,3,4)
        transforms={bone:matrix for bone,matrix in zip((8,9,10,11,14,21),matrices)}
        clear=guard.inspect(transforms,shoulder,elbow,wrist)
        assert clear[0]>-.08 and clear[1]>1.5,('firing limb intersects skinned torso',route,clear,shoulder,elbow,wrist)
        checked.append(clear)
        if float(route)>.999:
            a=shoulder-elbow;b=wrist-elbow
            bend=float(np.degrees(np.arccos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))))
            assert 75<bend<95,('left crossing elbow must bend near a right angle',bend)
            bends.append(bend)
    assert len(checked)>20 and bends,('missing live chest clearance samples',len(checked))
    return dict(samples=len(checked),minimum_upper_axis_clearance=min(p[0]for p in checked),
                minimum_forearm_clearance=min(p[1]for p in checked),minimum_left_elbow_angle=min(bends),maximum_left_elbow_angle=max(bends))

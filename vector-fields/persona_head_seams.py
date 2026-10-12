"""Match GIGN joining islands to their authored head or shirt material.

The curved neck island normally continues the hood. A costume can explicitly
use it as a shirt collar; the two actual head joins still follow the hood.
Masks come from the donor's connected UV triangles. Authored PNGs stay intact.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt

ANCHORS={'curved_join':(.67,.047),'rectangular_join':(.57,.03),'side_join':(.77,.74),'hood':(.68,.36)}
JOINS=tuple(name for name in ANCHORS if name!='hood')
LUMA=np.array([.2126,.7152,.0722])


def layout(triangles,size=512):
    uv=[np.array([[v['uv'][0],1-v['uv'][1]]for v in tri])for _,tri in triangles]
    parents=list(range(len(uv)));seen={}
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,tri in enumerate(uv):
        for vertex in tri:
            key=tuple(np.round(vertex,6))
            if key in seen:parents[root(i)]=root(seen[key])
            seen[key]=i
    masks={};bounds={};groups=[]
    for name,point in ANCHORS.items():
        found=set()
        for i,tri in enumerate(uv):
            matrix=np.vstack([tri.T,np.ones(3)])
            if abs(np.linalg.det(matrix))>1e-9 and np.min(np.linalg.solve(matrix,[*point,1]))>=-1e-6:found.add(root(i))
        if len(found)!=1:raise ValueError(f'{name}: expected one connected GIGN UV island, got {found}')
        group=found.pop();groups.append(group)
        mask=Image.new('L',(size,size));draw=ImageDraw.Draw(mask)
        selected=[tri for i,tri in enumerate(uv)if root(i)==group]
        for tri in selected:draw.polygon([tuple(vertex*size)for vertex in tri],fill=255)
        masks[name]=np.array(mask.filter(ImageFilter.MinFilter(3)))>0
        points=np.concatenate(selected);bounds[name]=[points.min(0).tolist(),points.max(0).tolist()]
    if len(set(groups))!=len(ANCHORS):raise ValueError('Head joins must be distinct from the hood reference island')
    for name in ('curved_join','rectangular_join'):
        lo,hi=bounds[name]
        if not(.52<=lo[0]<hi[0]<=.75 and 0<=lo[1]<hi[1]<=.27):raise ValueError(f'{name}: unexpected donor layout {bounds[name]}')
    lo,hi=bounds['side_join']
    if not(.70<=lo[0]<hi[0]<=.85 and .65<=lo[1]<hi[1]<=.94):raise ValueError(f'Side head join: unexpected donor layout {bounds["side_join"]}')
    # Filtered edges must sample their own material instead of the atlas grey.
    # Protect all adjacent clothing islands where the UV packing is tight.
    components={}
    for i,(_,tri) in enumerate(triangles):components.setdefault(root(i),[]).append((uv[i],tri))
    occupied=np.zeros((size,size),dtype=bool);head=[]
    for group,faces in components.items():
        mask=Image.new('L',(size,size));draw=ImageDraw.Draw(mask)
        for chart,_ in faces:draw.polygon([tuple(p*size)for p in chart],fill=255)
        occupied|=np.array(mask)>0
        positions=np.array([v['source']for _,tri in faces for v in tri])
        if np.max(np.abs(positions[:,0]))<5 and positions[:,2].min()>56:
            inset=4 if group==groups[2] else 3 if group==groups[3] else 2
            head.append((mask,inset))
    padding=[]
    for mask,inset in head:
        inside=np.array(mask)>0
        core=np.array(mask.filter(ImageFilter.MinFilter(inset*2+1)))>0
        if not core.any():raise ValueError('Head UV island has no safe interior for filtered extrusion')
        rim=(np.array(mask.filter(ImageFilter.MaxFilter(7)))>0)&(~occupied|inside)&~core
        _,nearest=distance_transform_edt(~core,return_indices=True)
        padding.append(dict(rim=rim,nearest=nearest))
    return dict(masks=masks,bounds=bounds,padding=padding)


def pad_head_edges(image,uv_layout):
    """Extend existing texels across a narrow UV rim and its filtering gutter."""
    original=np.array(image.convert('RGB'));result=original.copy()
    for part in uv_layout.get('padding',[]):
        rim=part['rim'];nearest=part['nearest']
        result[rim]=original[nearest[0][rim],nearest[1][rim]]
    changed=int(np.any(result!=original,axis=2).sum())
    return Image.fromarray(result),dict(islands=len(uv_layout.get('padding',[])),outer_margin_texels=3,pixels_changed=changed)


def representative(pixels):
    values=pixels.astype(float);light=values@LUMA
    lo,hi=np.quantile(light,[.2,.85]);middle=values[(light>=lo)&(light<=hi)]
    return np.median(middle if len(middle)else values,axis=0)


def difference(a,b):
    la,lb=max(1.,float(a@LUMA)),max(1.,float(b@LUMA))
    return float(np.max(np.abs(a/la-b/lb))),max(la/lb,lb/la)


def normalize(image,uv_layout,shirt_collar=False):
    original=np.array(image.convert('RGB'));result=original.copy();masks=uv_layout['masks']
    if original.shape[:2]!=masks['hood'].shape:raise ValueError('Head normalization requires the reference atlas dimensions')
    hood=representative(original[masks['hood']]);records=[]
    for name in JOINS:
        # One-pixel extrusion covers UV edge filtering, without touching another island.
        core=masks[name]
        mask=np.array(Image.fromarray(core.astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0
        before=representative(original[core]);chroma,brightness=difference(before,hood)
        collar=shirt_collar and name=='curved_join'
        changed=not collar and (chroma>.28 or brightness>1.65)
        if changed:
            light=original[mask].astype(float)@LUMA
            base_light=float(before@LUMA)
            shade=np.clip(light/base_light,.12,1.65)if base_light>1 else np.ones(len(light))
            result[mask]=np.clip(np.rint(shade[:,None]*hood),0,255).astype('uint8')
        after=representative(result[core]);after_chroma,after_brightness=difference(after,hood)
        records.append(dict(island=name,material='shirt_collar'if collar else'hood',corrected=bool(changed),hood_rgb=np.rint(hood).astype(int).tolist(),before_rgb=np.rint(before).astype(int).tolist(),after_rgb=np.rint(after).astype(int).tolist(),chroma_distance=round(chroma,4),brightness_ratio=round(brightness,4),after_chroma_distance=round(after_chroma,4),after_brightness_ratio=round(after_brightness,4),pixels_changed=int(np.any(result[mask]!=original[mask],axis=1).sum())))
    return Image.fromarray(result),records

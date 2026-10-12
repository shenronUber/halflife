"""Fit shared colour and cross-edge shading on the actual GIGN head surface.

This is a compile-time material sampler, not a mesh/UV change. The face interior,
neck, clothing and source atlases remain intact. AI-authored head layers replace
only the crown, rear shell and side chart; matching mesh edges constrain their
filtered samples and first derivatives before indexed-texture compilation.
"""
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import factorized
from scipy.spatial import cKDTree


def layout(triangles, size=512, band=10):
    # UV-connected components, with the 3D seam topology kept separately.
    charts=[np.array([[v['uv'][0]*size,(1-v['uv'][1])*size]for v in tri])for _,tri in triangles]
    parents=list(range(len(charts)));seen={}
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,chart in enumerate(charts):
        for uv in chart:
            key=tuple(np.round(uv,6))
            if key in seen:parents[root(i)]=root(seen[key])
            seen[key]=i
    groups=defaultdict(list)
    for i in range(len(charts)):groups[root(i)].append(i)
    selected={};head_mask=np.zeros((size,size),bool);retouch=np.zeros_like(head_mask)
    occupied=np.zeros_like(head_mask)
    for group,indices in groups.items():
        mask=Image.new('L',(size,size));draw=ImageDraw.Draw(mask)
        for i in indices:draw.polygon([tuple(p)for p in charts[i]],fill=255)
        mask=np.array(mask)>0;occupied|=mask
        positions=np.array([v['source']for i in indices for v in triangles[i][1]])
        if np.max(np.abs(positions[:,0]))<5 and positions[:,2].min()>58 and positions[:,2].max()>68:
            selected[group]=mask;head_mask|=mask
            # Exact approved face stays the source of its full front chart.
            if np.concatenate([charts[i]for i in indices])[:,0].mean()<.8*size:
                shell=mask.copy()
                # The rear chart includes a lower neck skirt. Preserve it,
                # especially the approved pink dress-shirt collar of Miami.
                if positions[:,2].min()<60:shell[int(.445*size):]=False
                retouch|=shell
    edges=defaultdict(list)
    for i,(_,tri)in enumerate(triangles):
        group=root(i)
        if group not in selected:continue
        for a,b in [(0,1),(1,2),(2,0)]:
            ka,kb=[tuple(np.round(tri[k]['source'],4))for k in (a,b)]
            a,b=(a,b)if ka<kb else(b,a)
            key=tuple(sorted((ka,kb)))
            edge=charts[i][[a,b]];other=charts[i][3-a-b]
            direction=edge[1]-edge[0];length=np.linalg.norm(direction)
            if length<1e-6:continue
            inward=np.array([-direction[1],direction[0]])/length
            if np.dot(inward,other-edge[0])<0:inward=-inward
            edges[key].append(dict(group=group,uv=edge,inward=inward))
    seams=[]
    for positions,sides in edges.items():
        if len(sides)!=2 or sides[0]['group']==sides[1]['group']:continue
        if max(p[2]for p in positions)<62:continue
        if np.max(np.abs(sides[0]['uv']-sides[1]['uv']))<1e-6:continue
        seams.append(dict(positions=positions,sides=sides))
    # A narrow surface band, with safe filtering gutters. UV neighbours such
    # as boots must never be edited even when they sit next to a head chart.
    safe=(np.array(Image.fromarray(head_mask.astype('uint8')*255).filter(ImageFilter.MaxFilter(7)))>0)&(~occupied|head_mask)
    yy,xx=np.indices((size,size));pixels=np.stack([xx+.5,yy+.5],axis=-1)
    distance=np.full((size,size),np.inf)
    for seam in seams:
        for side in seam['sides']:
            edge=side['uv'];direction=edge[1]-edge[0]
            t=np.clip(((pixels-edge[0])*direction).sum(-1)/np.dot(direction,direction),0,1)
            distance=np.minimum(distance,np.linalg.norm(pixels-(edge[0]+t[...,None]*direction),axis=-1))
    active=safe&(distance<=band)
    ids=np.full((size,size),-1,dtype=int);ids[active]=np.arange(active.sum())
    rows=[];cols=[];values=[];nr=0
    def equation(samples, weight=1):
        nonlocal nr
        coefficients=defaultdict(float)
        for point,multiplier in samples:
            # GoldSrc's integer UV coordinates land between texel centres.
            p=point-.5;x,y=np.floor(p).astype(int);fx,fy=p-[x,y]
            for dx,dy,w in [(0,0,(1-fx)*(1-fy)),(1,0,fx*(1-fy)),(0,1,(1-fx)*fy),(1,1,fx*fy)]:
                if w<1e-8:continue
                px,py=x+dx,y+dy
                if not(0<=px<size and 0<=py<size and ids[py,px]>=0):return False
                coefficients[ids[py,px]]+=w*multiplier
        for col,value in coefficients.items():
            rows.append(nr);cols.append(col);values.append(value*weight)
        nr+=1;return True
    equality_rows=[];gradient_rows=[]
    for seam in seams:
        a,b=seam['sides'];length=max(np.linalg.norm(s['uv'][1]-s['uv'][0])for s in (a,b))
        for t in np.linspace(0,1,max(3,int(length*2)+1)):
            pa=(1-t)*a['uv'][0]+t*a['uv'][1];pb=(1-t)*b['uv'][0]+t*b['uv'][1]
            # Avoid samples occupied by another atlas island at packed tips.
            row=nr
            if equation([(pa,1),(pb,-1)],weight=40):equality_rows.append(row)
            row=nr
            # Gradients use a common physical (not UV) step. Correct for the
            # very different texel densities of the front and the side strip.
            world_length=np.linalg.norm(np.array(seam['positions'][1])-seam['positions'][0])
            da=np.clip(np.linalg.norm(a['uv'][1]-a['uv'][0])/world_length*.08,.4,2)
            db=np.clip(np.linalg.norm(b['uv'][1]-b['uv'][0])/world_length*.08,.4,2)
            if equation([(pa+a['inward']*da,1),(pa,-1),(pb+b['inward']*db,1),(pb,-1)],weight=4):gradient_rows.append(row)
    constraints=coo_matrix((values,(rows,cols)),shape=(nr,active.sum())).tocsr()
    # Smooth the correction, keeping existing material detail instead of
    # blurring the source image. At the band's outer edge the correction fades.
    y,x=np.nonzero(active);lr=[];lc=[];lv=[];diagonal=np.zeros(len(y))
    for dy,dx in [(0,1),(1,0)]:
        py,px=y+dy,x+dx;valid=(py<size)&(px<size)
        src=np.flatnonzero(valid);dest=ids[py[valid],px[valid]];keep=dest>=0
        src,dest=src[keep],dest[keep]
        lr.extend(np.r_[src,dest]);lc.extend(np.r_[dest,src]);lv.extend(np.full(2*len(src),-1.))
        np.add.at(diagonal,src,1);np.add.at(diagonal,dest,1)
    fidelity=.015+1.5*np.clip(distance[active]/band,0,1)**4
    matrix=coo_matrix((lv,(lr,lc)),shape=(len(y),len(y))).tocsr()+diags(diagonal+fidelity)+constraints.T@constraints
    return dict(size=size,head_mask=head_mask,retouch_mask=retouch,safe=safe,active=active,
                constraints=constraints,equality_rows=np.array(equality_rows),gradient_rows=np.array(gradient_rows),
                solve=factorized(matrix.tocsc()),seams=seams,band_texels=band,chart_count=len(selected))


def apply_head_layer(original, layer, uv_layout):
    """Select AI-authored head charts; discard every unrelated generated pixel."""
    source=np.array(original.convert('RGB'));edited=np.array(layer.convert('RGB').resize(original.size,Image.Resampling.LANCZOS))
    mask=uv_layout['retouch_mask'];result=source.copy();result[mask]=edited[mask]
    return Image.fromarray(result),dict(selected_charts=3,pixels_selected=int(mask.sum()),face_preserved_exactly=True,clothing_preserved_exactly=True)


def align(image, uv_layout):
    original=np.array(image.convert('RGB'));result=original.copy();active=uv_layout['active']
    colour=original[active].astype(float);constraints=uv_layout['constraints']
    before=constraints@colour
    correction=uv_layout['solve'](-constraints.T@before)
    fitted=np.clip(colour+correction,0,255);result[active]=np.rint(fitted).astype('uint8')
    after=constraints@result[active].astype(float)
    return Image.fromarray(result),dict(seam_edges=len(uv_layout['seams']),head_charts=uv_layout['chart_count'],band_texels=uv_layout['band_texels'],
                                      matched_samples=len(uv_layout['equality_rows']),gradient_samples=len(uv_layout['gradient_rows']),
                                      pixels_changed=int(np.any(result!=original,axis=2).sum()),before=error(before,uv_layout),after=error(after,uv_layout),
                                      gradient_before=error(before,uv_layout,True),gradient_after=error(after,uv_layout,True))


def error(residual, uv_layout, gradient=False):
    rows=uv_layout['gradient_rows']if gradient else uv_layout['equality_rows']
    samples=np.abs(residual[rows]/(4 if gradient else 40))
    return dict(mean_rgb=round(float(samples.mean()),4),p95_rgb=round(float(np.quantile(samples,.95)),4),maximum_rgb=round(float(samples.max()),4))


def measure(image, uv_layout):
    """Measure the shared boundary after real indexed palette conversion."""
    colour=np.array(image.convert('RGB'))[uv_layout['active']].astype(float)
    residual=uv_layout['constraints']@colour
    return dict(colour=error(residual,uv_layout),gradient=error(residual,uv_layout,True))


def fit_indexed_edges(indexed, uv_layout, iterations=4):
    """Keep the chosen palette and improve only its head-band index assignment.

    Palette conversion can reintroduce a small jump on an otherwise matched
    seam. Alternate the surface fit with exact nearest existing palette entries,
    retaining the best result. Non-head pixels and the palette stay identical.
    """
    if indexed.mode!='P':raise ValueError('Indexed continuity needs a palette image')
    palette=indexed.getpalette();colours=np.array(palette,dtype=float).reshape(-1,3)
    nearest=cKDTree(colours);active=uv_layout['active'];current=indexed.copy();best=current
    before=measure(current,uv_layout)
    score=lambda r:r['colour']['mean_rgb']+.03*r['colour']['p95_rgb']
    best_error=before;accepted=0
    for _ in range(iterations):
        fitted,_=align(current,uv_layout)
        indices=np.array(current);_,values=nearest.query(np.array(fitted)[active].astype(float))
        indices[active]=values.astype('uint8')
        current=Image.fromarray(indices).convert('P');current.putpalette(palette)
        candidate=measure(current,uv_layout)
        if score(candidate)<score(best_error):best=current.copy();best_error=candidate;accepted+=1
    return best,dict(iterations=iterations,improvements=accepted,before=before,after=best_error,palette_preserved_exactly=True,non_head_indices_preserved_exactly=True)

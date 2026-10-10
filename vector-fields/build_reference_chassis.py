"""Arche and Gyre: open receivers retaining the R-01 underside interfaces.

Coordinates use the shared Bone76 frame. These are shells and structural ribs,
not a hidden rectangular core; all visible surfaces reuse the existing tiles.
"""
import math
import numpy as np
from model_contract import load as model_contract

CHASSIS={
 'arch':dict(name='R-01 / Arche',description='Double arche ajouree, branches effilees et mecanique suspendue.',family='Rogue'),
 'arch_top':dict(name='R-01 / Arche superieure',description='Arche ajouree, collier superieur et viseur deporte.',family='Rogue',mount=2),
 'gyre':dict(name='R-01 / Gyre',description='Noyau cylindrique, cerclages ouverts et cage helicoidale.',family='Engine'),
}


for key,spec in CHASSIS.items():
 spec['mount']=['bottom','side','top'].index(model_contract()['receivers']['r01_receiver_'+key]['feed_mount'])

def rib(m,x,path,width,thickness,material):
    """Sweep a rectangular rib along a faceted curve in the YZ plane."""
    points=np.asarray(path,float);rings=[]
    for i,p in enumerate(points):
        tangent=points[min(i+1,len(points)-1)]-points[max(0,i-1)]
        normal=np.array([-tangent[1],tangent[0]])/np.linalg.norm(tangent)
        half=thickness[i]/2 if isinstance(thickness,(tuple,list)) else thickness/2
        rings.append([np.array([x+dx,*(p+normal*dz*half)])for dx,dz in
                      [(-width/2,-1),(width/2,-1),(width/2,1),(-width/2,1)]])
    for a,b in zip(rings,rings[1:]):
        centre=np.mean(a+b,axis=0)
        for i in range(4):
            j=(i+1)%4;m.face([a[i],a[j],b[j],b[i]],material,centre)
    m.face(rings[0],material,np.mean(rings[1],axis=0))
    m.face(rings[-1],material,np.mean(rings[-2],axis=0))


def curved_rod(m,points,r,material=5,sides=8):
    for a,b in zip(points,points[1:]):m.cyl(a,b,r,material,sides,cap=False)


def interfaces(m,mount=0):
    # The stock and handgrip meet the same rear shoe as the existing receivers.
    m.box([0,-6,0],[3.9,1,3.7],5,.3)
    m.box([0,-1.8,-1.75],[2.25,3.3,.65],0,.22)
    # Open insertion collar: no solid box across the magazine's neck.
    z=2.45 if mount==2 else -1.6
    for x in (-1.22,1.22):m.box([x,15.25,z],[.48,3.3,1.8],0,.16)
    for y in (13.8,16.7):m.box([0,y,z],[2.9,.4,1.8],5,.1)
    # Barrel seat shares the bore axis (0, y, 1.3).
    m.tube([0,16.2,1.3],[0,17.1,1.3],1.25,.76,5,12)
    # Local attachment shoes, separated by real empty space.
    for x,y,z,size in [(1.72,-2,-.4,[.55,4,2.3]),
                        (-1.72,5,-.2,[.55,4.6,3.8]),
                        (1.72,5,.6,[.55,7,1.7]),
                        (-1.72,12,-.1,[.55,3.3,2.8])]:
        m.box([x,y,z],size,0,.12)
    # Rounded guard keeps the original finger/trigger working volume clear.
    rib(m,0,[(.2,-1.8),(.2,-4.8),(1,-6),(4.6,-6),(5.8,-4.8),(5.8,-1.8)],.65,.45,5)
    m.cyl([0,2.2,-1.8],[0,3,-4.6],.2,5,8)


def part(key,Mesh):
    top=key=='arch_top'
    m=Mesh();interfaces(m,2 if top else 0)
    if key in ('arch','arch_top'):
        # Two swept upper arms and two lower tendons, with tapered shoulders.
        upper=[(-6,.55),(-4,2.3),(-1,3.55),(3,3.7),(7,3.45),(10.5,2.95),(14,2.25),(16.45,1.3)]
        lower=[(-6,-.55),(-3.5,-1.55),(0,-2.15),(5,-2.3),(9,-1.8),(12,-.9),(15.3,.3),(16.45,1.3)]
        for side in (-1,1):
            rib(m,side*1.12,upper,.62,[.8,.9,.75,.65,.65,.75,.95,.85],2)
            rib(m,side*1.12,lower,.48,[.8,.7,.55,.5,.5,.55,.65,.8],5)
            # A silver inlay follows the curvature instead of planar side panels.
            curved_rod(m,[[side*1.46,y,z+.16]for y,z in upper],.085)
        for y,z in [(-3.5,2.55),(0,3.55),(6,3.45),(13,2.3)]:
            m.cyl([-1.45,y,z],[1.45,y,z],.18,5,8)
        # A narrow inner mechanism leaves a large visible opening at the front.
        m.cyl([0,-5.4,.8],[0,16.3,1.3],.32,5,10)
        for y in (-3.2,8.4,12.8):
            m.tube([0,y,.95],[0,y+.6,.95],.8,.35,0,10)
        # Optic pedestal sits between the arches at the original attachment height.
        if top:
            m.box([1.7,3,3.05],[5.2,3,.55],0,.14)
            m.box([3.4,3,3.35],[1.8,4,.45],5,.1)
            for y in (1.6,2.3,3,3.7,4.4):m.box([3.4,y,3.65],[2,.3,.2],5,.05)
            for x in (-.52,.52):m.cyl([x,3,.8],[x,3,3.05],.17,5,8)
        else:
            m.box([0,3,2.45],[1.2,4,.65],0,.14);m.rail(1,5,2.7)
            for x in (-.52,.52):m.cyl([x,3,.8],[x,3,2.45],.17,5,8)
        for side in (-1,1):
            m.cyl([side*1.12,11,2.9],[side*1.12,13.8,-.9],.24,0,8)
            m.cyl([side*1.1,-3.5,-1.5],[side*1.1,-3.5,2.5],.2,0,8)
    elif key=='gyre':
        # Rounded axial pressure vessel, capped by tapered ends, with a separate cage.
        m.cyl([0,-4.9,.25],[0,-2.9,.25],.72,2,12,r2=1.35)
        m.cyl([0,-2.9,.25],[0,9.7,.25],1.35,2,12)
        m.cyl([0,9.7,.25],[0,13,.65],1.35,2,12,r2=.7)
        m.cyl([0,13,.65],[0,16.4,1.3],.7,5,12,r2=.76)
        # The unique identity tile belongs on one small plaque, never tiled on a cylinder.
        m.box([0,-1.4,1.55],[1.28,2.6,.28],5,.06)
        m.face([[-.55,-2.5,1.695],[.55,-2.5,1.695],[.55,-.3,1.695],[-.55,-.3,1.695]],3,
               uv=[(.25,0),(.75,0),(.75,1),(.25,1)])
        for y in (-4.2,9.5,12.5):
            z=.25 if y<10 else .6
            m.tube([0,y-.26,z],[0,y+.26,z],2.28,1.91,5,12)
            for angle in (45,135,225,315):
                a=math.radians(angle)
                m.cyl([1.3*math.cos(a),y,z+1.3*math.sin(a)],
                      [2.12*math.cos(a),y,z+2.12*math.sin(a)],.14,0,8)
        # Four open helical members. Twisting changes the silhouette in 3/4 view.
        for phase in (35,125,215,305):
            points=[]
            for i in range(9):
                y=-4.2+i*16.7/8;a=math.radians(phase+i*80/8)
                points.append([2.18*math.cos(a),y,.25+max(0,y-9.5)*.35/3+2.18*math.sin(a)])
            curved_rod(m,points,.17,7,6)
        # Forked tail and forward yoke connect the cage to existing interfaces.
        for side in (-1,1):
            m.cyl([side*1.2,-6,0],[side*1.4,-4.2,.25],.38,5,10)
            m.cyl([side*1.35,12.5,-.3],[side*1.22,14.8,-1.2],.26,5,8)
        m.box([0,3,2.55],[1.4,4,.45],0,.12);m.rail(1,5,2.7)
        for y in (1.4,4.6):m.cyl([0,y,1.5],[0,y,2.5],.28,5,8)
    else:raise ValueError(key)
    return m.tris

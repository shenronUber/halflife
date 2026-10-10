"""Inventor and dieselpunk silhouettes using the shared sixteen-material atlas.

All parts keep the original socket frame; chamber pieces ride R01_Bolt.
The decorative gears, cams and indicators have no independent animation.
"""
import math

PARTS={
 'chamber':(
  dict(key='inventor',name='Culasse a manivelle',description='Chariot ouvert, roue dentee et manivelle decalee.',family='Rogue'),
  dict(key='diesel',name='Culasse a cames',description='Arbre a cames, ressort apparent et levier de rappel.',family='Engine')),
 'optic':(
  dict(key='inventor',name='Dioptre astrolabe',description='Anneaux de visee, graduations en relief et molette laterale.',family='Predator'),
  dict(key='diesel',name='Viseur periscopique',description='Colonne etagee, capot profile et reglage lateral.',family='Engine')),
 'power':(
  dict(key='inventor',name='Accumulateur a ressort',description='Deux tambours de remontage et courroies sous un arceau ouvert.',family='Rogue'),
  dict(key='diesel',name='Reservoir a huile',description='Deux colonnes d huile, conduites et manometre mecanique.',family='Engine')),
 'cooling':(
  dict(key='inventor',name='Eventails a lamelles',description='Deux bouquets de lamelles deployees sur leurs pivots.',family='Baseline'),
  dict(key='diesel',name='Radiateur a faisceau',description='Collecteurs arrondis, tubes paralleles et ailettes exterieures.',family='Fortress')),
}


def rod(m,points,r,mat=5,n=6):
    for a,b in zip(points,points[1:]):m.cyl(a,b,r,mat,n,cap=False)


def wheel(m,x,y,z,r,teeth=12):
    """Open spoked wheel with actual teeth, on the X axis."""
    m.tube([x-.1,y,z],[x+.1,y,z],r*.86,r*.64,5,16)
    m.cyl([x-.17,y,z],[x+.17,y,z],r*.22,5,8)
    for i in range(6):
        a=i*math.tau/6
        m.cyl([x,y,z],[x,y+math.cos(a)*r*.69,z+math.sin(a)*r*.69],r*.075,0,6)
    for i in range(teeth):
        a=i*math.tau/teeth
        m.cyl([x,y+math.cos(a)*r*.79,z+math.sin(a)*r*.79],
              [x,y+math.cos(a)*r,z+math.sin(a)*r],r*.12,0,6)


def lens(m,y,z,r,n=16):
    points=[[r*math.cos(i*math.tau/n),y,z+r*math.sin(i*math.tau/n)]for i in range(n)]
    uv=[(.5+.25*math.cos(i*math.tau/n),.5+.25*math.sin(i*math.tau/n))for i in range(n)]
    m.face(points,11,uv=uv);m.face(points[::-1],11,uv=uv[::-1])


def petal(m,x,y,z,a,side):
    """A real tapered blade in the YZ plane, extruded across X."""
    outline=[]
    for radius,angle in [(.42,a-.1),(2.45,a-.095),(2.62,a),(2.45,a+.095),(.42,a+.1)]:
        outline.append([y+radius*math.cos(angle),z+radius*math.sin(angle)])
    rings=[[[x+dx,*p]for p in outline]for dx in (-.09,.09)]
    center=[x,y+1.3*math.cos(a),z+1.3*math.sin(a)]
    for ring in rings:m.face(ring,6,center)
    for i in range(len(outline)):
        j=(i+1)%len(outline);m.face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],5,center)
    m.cyl([x+side*.12,y+.5*math.cos(a),z+.5*math.sin(a)],
          [x+side*.12,y+2.4*math.cos(a),z+2.4*math.sin(a)],.045,5,5)


def part(slot,key,Mesh):
    assert slot in PARTS and key in ('inventor','diesel')
    inventor=key=='inventor';m=Mesh()
    if slot=='chamber':
        # The short shoe and the empty centre fit every receiver's bolt saddle.
        for z in (-.08,1.28):m.box([2.12,5,z],[.38,6.8,.32],5,.07)
        for y in (1.8,8.2):m.box([2.12,y,.6],[.38,.38,1.7],0,.07)
        if inventor:
            wheel(m,2.67,5.9,.62,1.12)
            m.cyl([2.14,5.9,.62],[3.05,5.9,.62],.19,5,8)
            m.cyl([3.03,5.9,.62],[3.03,6.7,1.36],.14,5,8)
            m.cyl([3.03,6.7,1.36],[3.68,6.7,1.36],.23,4,8)
            m.box([2.47,2.9,.6],[.5,1.45,1.3],0,.18)
            m.panel(2.73,2.9,.6,1.25,1.05,15,repeat=1)
            for z in (.3,.9):m.cyl([2.42,3.55,z],[2.42,5.05,z],.075,7,6)
        else:
            m.cyl([2.66,2.2,.6],[2.66,7.95,.6],.18,5,8)
            for y,z in ((3.5,.78),(4.5,.4),(5.5,.78)):
                m.cyl([2.72,y-.23,z],[2.72,y+.23,z],.56,0,10)
            for y in (2.2,7.9):m.box([2.6,y,.6],[1,.4,1.5],2,.18)
            spring=[[2.7+.3*math.cos(t),6.05+t/(math.tau*4)*1.25,.6+.3*math.sin(t)]for t in [i*math.tau/8 for i in range(33)]]
            rod(m,spring,.065,5,5)
            m.cyl([2.8,7.35,.6],[3.18,7.35,1.2],.17,5,8)
            m.box([3.2,7.35,1.35],[.75,1.2,.45],4,.14)
            m.box([2.38,5,-.3],[.5,2.8,.32],2,.1)
    elif slot=='optic':
        m.box([0,3,3.55],[1.8,4,.9],0,.14)
        if inventor:
            for x in (-.7,.7):m.cyl([x,3,3.85],[x,3,4.65],.16,5,8)
            m.tube([0,2.68,5.35],[0,3.32,5.35],1.45,1.03,5,20)
            for i in range(12):
                a=i*math.tau/12
                m.cyl([1.3*math.cos(a),2.62,5.35+1.3*math.sin(a)],
                      [1.5*math.cos(a),2.62,5.35+1.5*math.sin(a)],.055,0,5)
            m.tube([0,1.75,5.35],[0,2.05,5.35],1.15,.91,5,16)
            for x in (-1.04,1.04):m.cyl([x,1.9,5.35],[x,3.02,5.35],.08,0,6)
            wheel(m,1.67,3,4.5,.55,10)
            m.cyl([.6,3,4.5],[1.7,3,4.5],.13,5,8)
            lens(m,2.9,5.35,1.02)
        else:
            m.box([0,3.7,4.5],[1.7,2.1,1.8],2,.28)
            m.tube([0,1.1,5.9],[0,5.4,5.9],1.02,.76,2,8)
            for y in (1.1,5.1):m.tube([0,y,5.9],[0,y+.32,5.9],1.14,.76,5,8)
            m.box([0,3.2,7.05],[1.55,4.4,.24],0,.08)
            m.cyl([.94,3.8,5.9],[1.43,3.8,5.9],.45,5,10)
            m.panel(1.44,3.8,5.9,.64,.64,10,repeat=1)
            lens(m,1.42,5.9,.75)
    elif slot=='power':
        m.box([-2.02,5,-.2],[.7,4.6,3.8],5,.2)
        if inventor:
            for y in (3.9,6.1):
                m.cyl([-2.4,y,-.35],[-3.35,y,-.35],.78,7,12)
                wheel(m,-3.5,y,-.35,.88,10)
            for z in (-1.03,.34):m.cyl([-3.3,3.9,z],[-3.3,6.1,z],.105,7,6)
            for y in (2.9,7.1):m.box([-2.8,y,-.3],[1.65,.35,3.2],0,.1)
            rod(m,[[-3.4,2.9,.1],[-3.4,3.4,1.55],[-3.4,5,1.95],[-3.4,6.6,1.55],[-3.4,7.1,.1]],.18,0,8)
            m.cyl([-3.65,6.1,-.35],[-4,6.1,-.35],.17,5,8)
            m.cyl([-4,6.1,-.35],[-4,6.85,.12],.11,5,8)
            m.cyl([-3.9,6.85,.12],[-4.25,6.85,.12],.19,4,8)
        else:
            for y in (3.9,6.1):
                m.cyl([-3,y,-1.55],[-3,y,1.25],.68,8,12)
                for z in (-1.5,1.2):m.cyl([-3,y,z-.14],[-3,y,z+.14],.8,5,12)
                for x in (-3.65,-2.35):m.cyl([x,y,-1.35],[x,y,1.2],.075,0,6)
            rod(m,[[-3,3.9,1.45],[-3,3.9,1.95],[-3,6.1,1.95],[-3,6.1,1.45]],.16,7,8)
            m.cyl([-3.15,5,.45],[-3.99,5,.45],.72,5,12)
            m.panel(-4,5,.45,1.12,1.12,10,-1,repeat=1)
            m.box([-3,5,-1.9],[1.6,4.1,.45],0,.14)
    elif slot=='cooling':
        for side in (-1,1):
            m.box([side*1.4,25,1.2],[.3,4,1.7],0,.1)
            if inventor:
                m.cyl([side*1.55,25,.25],[side*2.18,25,.25],.38,5,10)
                for i in range(7):petal(m,side*2.02,25,.25,math.radians(20+i*140/6),side)
                m.cyl([side*2.15,25,.25],[side*2.3,25,.25],.42,0,10)
            else:
                for y in (22.9,27.1):m.cyl([side*1.97,y,.05],[side*1.97,y,2.35],.43,2,10)
                for z in (.25,.85,1.45,2.05):m.cyl([side*2.02,23,z],[side*2.02,27,z],.17,7,8)
                for y in (23.5,24.25,25,25.75,26.5):m.box([side*2.12,y,1.2],[.63,.16,2.3],5,.04)
                for z in (-.1,2.5):m.box([side*1.95,25,z],[.5,4.8,.2],0,.05)
    return m.tris

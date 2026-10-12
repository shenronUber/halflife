"""Rigid head accessories and paired static wearing/stowage poses."""
import math
import numpy as np
from headgear_geometry import Mesh, CENTER, unit, shell_point, spartan as spartan_core

RIOT_CENTER = np.array([CENTER[0], -.35, 64.85])
RIOT_RADII = np.array([4.65, 6.05, 6.3])
VISOR_PIVOT = np.array([CENTER[0], -1.9, 66.8])
OPTICS_PIVOT = np.array([CENTER[0], -3.8, 67.85])
OPTICS_ANGLE = -80


def rotation_x(degrees):
    angle=math.radians(degrees); c,s=math.cos(angle),math.sin(angle)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])


def rotated(mesh, pivot, degrees, offset=(0,0,0)):
    """Move one rigid package, preserving normals, topology, UVs and materials."""
    rotation=rotation_x(degrees)
    pivot=np.asarray(pivot); offset=np.asarray(offset)
    for _,triangle in mesh.triangles:
        for vertex in triangle:
            vertex['p']=pivot+rotation@(vertex['p']-pivot)+offset
            vertex['n']=rotation@vertex['n']
    return mesh


def riot_bottom(t):
    return 64.0 + 3.0 * max(0, math.cos(t)) ** 2


def riot_surface(t, fraction, offset=0):
    phi = fraction * math.acos((riot_bottom(t)-RIOT_CENTER[2])/RIOT_RADII[2])
    p = RIOT_CENTER + RIOT_RADII * [math.sin(phi)*math.sin(t), -math.sin(phi)*math.cos(t), math.cos(phi)]
    n = unit((p-RIOT_CENTER)/(RIOT_RADII**2))
    return p + n*offset, n


def closed_shield(t, fraction):
    # The upper shield seats directly against the brow. Side portions overlap
    # the solid shell, so there is no exposed forehead strip in the closed pose.
    phi = math.acos((66.9-RIOT_CENTER[2])/RIOT_RADII[2])
    upper = RIOT_CENTER + (RIOT_RADII+[.15,.15,0]) * [math.sin(phi)*math.sin(t), -math.sin(phi)*math.cos(t), math.cos(phi)]
    lower = np.array([CENTER[0]+4.87*math.sin(t), -.35-6.20*math.cos(t), 60.55+.35*abs(math.sin(t))])
    p = upper*(1-fraction)+lower*fraction
    p += [math.sin(t)*.12*math.sin(math.pi*fraction), -math.cos(t)*.12*math.sin(math.pi*fraction), 0]
    return p


def raised_shield(mesh):
    # Rotate the SAME rigid shield around the real transverse hinge axis.
    angle=math.radians(-112); c,s=math.cos(angle),math.sin(angle)
    rotation=np.array([[1,0,0],[0,c,-s],[0,s,c]])
    for _,triangle in mesh.triangles:
        for v in triangle:
            v['p']=VISOR_PIVOT+rotation@(v['p']-VISOR_PIVOT)
            v['n']=rotation@v['n']
    return mesh


def riot(raised=False):
    mesh=Mesh(); segments,bands=20,6
    # Fewer broad planar panels, larger volume: intentionally heavy/blocky.
    for i in range(segments):
        a,b=i*2*math.pi/segments,(i+1)*2*math.pi/segments
        for j in range(bands):
            samples=[riot_surface(t,v) for t,v in [(a,j/bands),(b,j/bands),(b,(j+1)/bands),(a,(j+1)/bands)]]
            mesh.face([p for p,n in samples],'riot_shell',sum(n for p,n in samples),
                      uv=[(i%10/10,j/bands),((i%10+1)/10,j/bands),((i%10+1)/10,(j+1)/bands),(i%10/10,(j+1)/bands)])
        p0,n0=riot_surface(a,1); p1,n1=riot_surface(b,1)
        mesh.face([p0,p1,p1-n1*.38,p0-n0*.38],'rim',[0,0,-1])
    mesh.tube([riot_surface(t,1,.04)[0] for t in np.linspace(-math.pi,math.pi,21)],.17,'rim',6)
    # Broad armour segments make the silhouette recognisable rather than a hood.
    for theta in (-.55,.55,2.55,3.73):
        samples=[riot_surface(t,v,.075) for t,v in [(theta-.18,.40),(theta+.18,.40),(theta+.23,.80),(theta-.23,.80)]]
        mesh.panel([p for p,n in samples],sum(n for p,n in samples),'riot_shell','hardware',.10,.22)
    # Brow plate and heavy central clamp are attached to the solid shell.
    for i in range(12):
        a,b=-1.3+2.6*i/12,-1.3+2.6*(i+1)/12
        upper=[closed_shield(t,0)+[0,0,.48] for t in (a,b)]
        lower=[closed_shield(t,0)+[0,0,-.10] for t in (a,b)]
        mesh.face([upper[0],upper[1],lower[1],lower[0]],'rim',[0,-1,.2],
                  uv=[(i/12,1),((i+1)/12,1),((i+1)/12,0),(i/12,0)])
        mesh.face([upper[0],upper[1],upper[1]+[0,.26,.15],upper[0]+[0,.26,.15]],'hardware',[0,0,1])
    mesh.panel([[CENTER[0]-.62,-6.24,67.0],[CENTER[0]+.62,-6.24,67.0],
                [CENTER[0]+.48,-6.06,67.7],[CENTER[0]-.48,-6.06,67.7]],[0,-1,.1],'hardware','rim',.10,.15)
    # Shield assembly: glass, continuous seals, and thick side/lower frames.
    shield=Mesh()
    for i in range(16):
        a,b=-1.3+2.6*i/16,-1.3+2.6*(i+1)/16
        for j in range(3):
            shield.face([closed_shield(a,j/3),closed_shield(b,j/3),closed_shield(b,(j+1)/3),closed_shield(a,(j+1)/3)],
                        'visor',[0,-1,0],uv=[(i/16,1-j/3),((i+1)/16,1-j/3),((i+1)/16,1-(j+1)/3),(i/16,1-(j+1)/3)])
    for fraction,radius in ((0,.16),(1,.13)):
        shield.tube([closed_shield(t,fraction) for t in np.linspace(-1.3,1.3,17)],radius,'rim',6)
    for side in (-1,1):
        shield.tube([closed_shield(side*1.3,f) for f in np.linspace(0,1,5)],.16,'hardware',6)
        shield.tube([closed_shield(side*1.3,0),[CENTER[0]+side*4.55,-1.9,66.8]],.16,'hardware',6)
    shield.articulate()
    mesh.triangles.extend((raised_shield(shield) if raised else shield).triangles)
    for side in (-1,1):
        x=CENTER[0]+side*4.6; n=np.array([side,0,0])
        # Thick temple housing and large ratchet lock, not a floating square.
        mesh.panel([(x,-3.0,65.7),(x,-3.05,67.45),(x,-2.3,68.05),
                    (x,-.72,67.9),(x,-.48,66.15),(x,-1.25,65.55)],n,'riot_shell','hardware',.18,.30)
        mesh.pin([x+side*.32,-1.9,66.8],n,.65,.20,'rim',12)
        mesh.pin([x+side*.54,-1.9,66.8],n,.43,.12,'hardware',12)
        for y,z in ((-2.65,67.3),(-.86,66.25)):
            mesh.pin([x+side*.33,y,z],n,.13,.08,'hardware',8)
        # Solid jaw/ear armour, with an angular silhouette and embedded vents.
        mesh.panel([(x,-1.55,64.9),(x,.7,65.1),(x,1.8,63.95),(x,1.4,61.9),
                    (x,.2,60.5),(x,-1.5,61.25)],n,'riot_shell','hardware',.18,.32)
        mesh.panel([(x+side*.35,-.72,64.2),(x+side*.35,.75,64.2),
                    (x+side*.35,.7,62.1),(x+side*.35,-.75,62.1)],n,'vents','rim',.13,.10)
        # Lower jaw frame anchors the face shield and gives it a closed perimeter.
        chin=[[CENTER[0]+side*4.45,-1.65,61.5],[CENTER[0]+side*3.30,-4.82,60.25],
              [CENTER[0]+side*2.45,-6.0,60.20],[CENTER[0]+side*2.65,-5.75,61.10],
              [CENTER[0]+side*3.55,-4.25,61.7],[CENTER[0]+side*4.5,-1.55,62.15]]
        mesh.panel(chin,[side*.6,-.6,-.12],'riot_shell','hardware',.12,.17)
        # Short conformal side rail; no distant horn behind the helmet.
        points=[riot_surface(t,v,.10)[0] for t,v in
                [(side*1.7,.74),(side*2.30,.74),(side*2.30,.87),(side*1.7,.87)]]
        mesh.panel(points,riot_surface(side*2,.8)[1],'hardware','rim',.08,.13)
    mesh.panel([[CENTER[0]-2.50,-6.11,60.23],[CENTER[0]+2.50,-6.11,60.23],
                [CENTER[0]+2.60,-6.2,60.92],[CENTER[0]-2.60,-6.2,60.92]],[0,-1,-.1],'hardware','rim',.12,.17)
    return mesh


def spartan():
    mesh=spartan_core()
    # Armour scales from the existing fitting, retaining the usable eye opening.
    scale=np.array([1.13,1.09,1.04]); pivot=np.array([CENTER[0],CENTER[1],61.0])
    for _,triangle in mesh.triangles:
        for v in triangle:
            v['p']=pivot+(v['p']-pivot)*scale
            v['n']=unit(v['n']/scale)
    def fitted(p): return pivot+(np.asarray(p)-pivot)*scale
    # Layered temple plates and thick brow wings, each with visible thickness.
    for side in (-1,1):
        n=unit([side*.88,-.35,.1])
        points=[fitted([CENTER[0]+side*x,y,z]) for x,y,z in
                [(.66,-6.64,66.02),(3.17,-4.56,66.08),(3.54,-3.60,66.75),
                 (3.20,-4.20,67.65),(.80,-6.25,67.08)]]
        mesh.panel(points,unit([side*.40,-.85,.12]),'engraving','bronze_edge',.14,.25)
        for x,y,z in ((3.30,-3.98,66.78),(2.62,-4.78,66.90)):
            mesh.pin(fitted([CENTER[0]+side*x,y,z])+n*.27,n,.16,.09,'bronze_edge',8)
        # A second shallow shoulder of bronze makes cheek armour less wafer thin.
        points=[fitted([CENTER[0]+side*x,y,z]) for x,y,z in
                [(3.54,-3.19,63.65),(2.72,-4.31,63.35),(2.47,-4.65,60.20),
                 (3.21,-3.65,60.74),(3.62,-3.0,62.10)]]
        mesh.panel(points,unit([side*.78,-.62,0]),'ornament','bronze_edge',.14,.22)
    # A substantial central brow boss, visually continuing into the nasal.
    mesh.panel([fitted([CENTER[0]-.59,-6.74,65.96]),fitted([CENTER[0]+.59,-6.74,65.96]),
                fitted([CENTER[0]+.50,-5.70,67.92]),fitted([CENTER[0]-.50,-5.70,67.92])],
               [0,-1,.1],'bronze','bronze_edge',.10,.19)
    return mesh


def cylinder(mesh, center, axis, radius, length, material='optics_metal', segments=12):
    center=np.asarray(center,dtype=float); axis=unit(axis)
    u=unit(np.cross(axis,[0,0,1] if abs(axis[2])<.9 else [0,1,0])); v=np.cross(axis,u)
    for i in range(segments):
        a,b=i*2*math.pi/segments,(i+1)*2*math.pi/segments
        r0=u*math.cos(a)+v*math.sin(a); r1=u*math.cos(b)+v*math.sin(b)
        mesh.face([center+r0*radius,center+r1*radius,center+axis*length+r1*radius,center+axis*length+r0*radius],
                  material,r0+r1,uv=[(i/segments,0),((i+1)/segments,0),((i+1)/segments,1),(i/segments,1)])


def optical_pod(mesh, center, radius, depth, color):
    # Align tubes to the actual head's forward axis in the tilted bind pose.
    center=np.asarray(center,dtype=float); axis=unit([0,-.983218,-.182435])
    u=np.array([1,0,0]); v=np.cross(axis,u)
    cylinder(mesh,center,axis,radius,depth)
    # Ribbed, stacked barrels; thick hexagonal housings around round glass.
    for distance in (.12,depth*.55,depth-.09):
        cylinder(mesh,center+axis*distance,axis,radius*1.13,.14,'rim',12)
    front=center+axis*(depth+.10)
    for i in range(16):
        a,b=i*2*math.pi/16,(i+1)*2*math.pi/16
        r=lambda t: u*math.cos(t)+v*math.sin(t)
        outer=[front+r(t)*radius*1.12 for t in (a,b)]
        inner=[front+axis*.05+r(t)*radius*.79 for t in (a,b)]
        mesh.face([outer[0],outer[1],inner[1],inner[0]],'hardware',axis)
        mesh.face([front+axis*.045,inner[0],inner[1]],'lens_'+color,axis,
                  uv=[(.5,.5),(.5+.50*math.cos(a),.5+.50*math.sin(a)),(.5+.50*math.cos(b),.5+.50*math.sin(b))])


def harness(mesh, green=False):
    # A separate cloth harness on the balaclava, no hidden rigid helmet shell.
    def strap(t,z):
        return np.array([CENTER[0]+3.67*math.sin(t),-.8-4.60*math.cos(t),z])
    for i in range(28):
        a,b=.62+i*(2*math.pi-1.24)/28,.62+(i+1)*(2*math.pi-1.24)/28
        mesh.face([strap(a,65.3),strap(b,65.3),strap(b,66.05),strap(a,66.05)],'rim',
                  [math.sin((a+b)/2),-math.cos((a+b)/2),0])
    # Wide crown strap, following the head surface into the rear battery cradle.
    for i in range(14):
        a,b=-.78+i*2.25/14,-.78+(i+1)*2.25/14
        p=lambda t,x: [CENTER[0]+x,-.6+4.33*math.sin(t),64.2+5.25*math.cos(t)]
        mesh.face([p(a,-.38),p(b,-.38),p(b,.38),p(a,.38)],'rim',[0,math.sin((a+b)/2),math.cos((a+b)/2)],
                  uv=[(0,i/14),(0,(i+1)/14),(1,(i+1)/14),(1,i/14)])
    # Visible rear power pack and adjustment buckle.
    mesh.panel([[CENTER[0]-1.35,3.86,64.55],[CENTER[0]+1.35,3.86,64.55],
                [CENTER[0]+1.5,3.65,66.30],[CENTER[0]-1.5,3.65,66.30]],
               [0,1,.1],'optics_metal','hardware',.16,.38)
    mesh.panel([[CENTER[0]-.64,4.27,64.9],[CENTER[0]+.64,4.27,64.9],
                [CENTER[0]+.64,4.18,65.6],[CENTER[0]-.64,4.18,65.6]],
               [0,1,0],'vents','rim',.08,.08)
    for x in (-1.04,1.04):
        mesh.pin([CENTER[0]+x,4.09,65.85],[0,1,0],.14,.08,'hardware',8)
    for side in (-1,1):
        mesh.panel([[CENTER[0]+side*3.6,-1.05,65.1],[CENTER[0]+side*3.6,.12,65.1],
                    [CENTER[0]+side*3.6,.12,66.25],[CENTER[0]+side*3.6,-1.05,66.25]],
                   [side,0,0],'hardware','rim',.12,.16)
        mesh.tube([[CENTER[0]+side*2.9,-5.35,65.9],[CENTER[0]+side*3.72,-3.0,66.3],
                   [CENTER[0]+side*3.78,.1,66.25],[CENTER[0]+side*2.7,2.58,66.20],
                   [CENTER[0]+side*1.25,3.90,65.9]],.105 if green else .13,'rim',6)


def goggles(green=False, raised=False):
    # Keep straps, battery and hinge mounts on the head; only the optical
    # package folds upwards. The same lens geometry is used in both positions.
    support=Mesh(); harness(support,green)
    for side in (-1,1):
        support.tube([[CENTER[0]+side*3.6,-1.05,66.1],
                      [CENTER[0]+side*3.38,-2.8,67.0],
                      [CENTER[0]+side*2.75,-3.8,67.85]],.15,'optics_metal',6)
        support.pin([CENTER[0]+side*2.75,-3.8,67.85],[side,0,0],.30,.17,'hardware',10)
    mesh=Mesh()
    normal=[0,-1,0]
    if not green:
        # Triangular tri-ocular package; one high sensor, two deep lower tubes.
        mesh.panel([[CENTER[0]-2.7,-5.68,64.1],[CENTER[0]+2.7,-5.68,64.1],
                    [CENTER[0]+2.7,-5.45,65.6],[CENTER[0]+.85,-5.0,67.3],
                    [CENTER[0]-.85,-5.0,67.3],[CENTER[0]-2.7,-5.45,65.6]],
                   normal,'red_housing','optics_metal',.15,.25)
        for x,z,r,depth in ((-1.58,64.65,.86,2.30),(1.58,64.65,.86,2.30),(0,66.6,.71,1.9)):
            optical_pod(mesh,[CENTER[0]+x,-5.9,z],r,depth,'red')
        # Off-centre processor, cable loops and a raised top actuator.
        mesh.panel([[CENTER[0]+2.58,-6.8,65.2],[CENTER[0]+2.58,-5.6,65.2],
                    [CENTER[0]+2.58,-5.6,66.7],[CENTER[0]+2.58,-6.8,66.7]],
                   [1,0,0],'vents','red_housing',.10,.25)
        mesh.tube([[CENTER[0]-2.4,-6.9,65.6],[CENTER[0]-2.7,-5.8,66.8],
                   [CENTER[0]-.4,-5.3,67.45],[CENTER[0]+.25,-6.0,67.1]],.13,'rim',6)
        mesh.panel([[CENTER[0]-.72,-5.2,67.05],[CENTER[0]+.72,-5.2,67.05],
                    [CENTER[0]+.72,-3.8,67.85],[CENTER[0]-.72,-3.8,67.85]],
                   [0,-.3,1],'optics_metal','hardware',.10,.19)
    else:
        # Broad binocular instrument: different profile, square cages, large glass.
        mesh.panel([[CENTER[0]-3.0,-5.9,64.2],[CENTER[0]+3.0,-5.9,64.2],
                    [CENTER[0]+3.0,-5.6,66.6],[CENTER[0]+2.3,-5.25,67.0],
                    [CENTER[0]-2.3,-5.25,67.0],[CENTER[0]-3.0,-5.6,66.6]],
                   normal,'optics_metal','hardware',.19,.28)
        for side in (-1,1):
            x=CENTER[0]+side*1.5
            mesh.panel([[x-1.22,-6.4,64.2],[x+1.22,-6.4,64.2],
                        [x+1.22,-6.4,66.6],[x-1.22,-6.4,66.6]],normal,'hardware','rim',.24,.32)
            optical_pod(mesh,[x,-6.72,65.0],1.0,1.4,'green')
            mesh.pin([x,-5.6,67.15],[0,0,1],.26,.28,'hardware',10)
        # Offset rangefinder and a left-side tracking arm give it its own identity.
        optical_pod(mesh,[CENTER[0]+3.03,-5.55,66.3],.38,1.0,'green')
        lead=np.array([CENTER[0]-2.9,-7.0,64.65])
        if raised:
            lead=OPTICS_PIVOT+rotation_x(OPTICS_ANGLE)@(lead-OPTICS_PIVOT)
        support.tube([lead,[CENTER[0]-3.5,-4.2,68.35] if raised else [CENTER[0]-3.25,-5.0,64.85],
                      [CENTER[0]-3.55,-2.1,65.7]],.13,'hardware',6,bones=[28,29,13])
        mesh.panel([[CENTER[0]-.55,-6.25,66.6],[CENTER[0]+.55,-6.25,66.6],
                    [CENTER[0]+.45,-5.0,67.85],[CENTER[0]-.45,-5.0,67.85]],
                   [0,-.4,1],'vents','hardware',.12,.18)
    # Rigid folding arms meet the fixed transverse pivots in either pose.
    for side in (-1,1):
        mesh.tube([[CENTER[0]+side*2.75,-3.8,67.85],
                   [CENTER[0]+side*2.55,-5.5,66.45]],.16,'optics_metal',6)
    mesh.articulate()
    support.triangles.extend((rotated(mesh,OPTICS_PIVOT,OPTICS_ANGLE) if raised else mesh).triangles)
    return support


def variants():
    # Existing body IDs remain stable; new poses/accessories append to the group.
    from headgear_extra_designs import ballistic, gas_mask
    return [('riot',riot()),('spartan',spartan()),('riot_up',riot(True)),
            ('nvg_red',goggles()),('nvg_green',goggles(True)),
            ('nvg_red_up',goggles(raised=True)),('nvg_green_up',goggles(True,True)),
            ('ballistic',ballistic()),('ballistic_up',ballistic(True)),
            ('gas_mask',gas_mask()),('gas_mask_up',gas_mask(True))]

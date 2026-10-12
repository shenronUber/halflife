"""Black ballistic shield and panoramic respirator, fitted to the GIGN head.

The user photographs define silhouettes. These are editable native meshes;
materials are diffuse atlas crops, and glass uses the existing additive mode.
"""
import math
import numpy as np
from headgear_geometry import Mesh, CENTER, unit
from headgear_designs import cylinder, rotated

BALLISTIC_PIVOT=np.array([CENTER[0],-1.8,66.85])
BALLISTIC_ANGLE=-110
GAS_PIVOT=np.array([CENTER[0],-6.7,64.0])
GAS_ANGLE=-45
GAS_OFFSET=np.array([0,6.4,7.6])


def ballistic(raised=False):
    mesh=Mesh(); center=np.array([CENTER[0],-.35,64.9]); radii=np.array([4.55,5.85,6.5])
    def surface(t,f):
        bottom=61.9+5.2*max(0,math.cos(t))**2
        phi=f*math.acos((bottom-center[2])/radii[2])
        p=center+radii*[math.sin(phi)*math.sin(t),-math.sin(phi)*math.cos(t),math.cos(phi)]
        return p,unit((p-center)/(radii*radii))
    # Deep ear/nape coverage and a broad dome, distinct from the blue riot model.
    for i in range(24):
        a,b=i*2*math.pi/24,(i+1)*2*math.pi/24
        for j in range(7):
            samples=[surface(t,f) for t,f in [(a,j/7),(b,j/7),(b,(j+1)/7),(a,(j+1)/7)]]
            mesh.face([p for p,n in samples],'ballistic_paint',sum(n for p,n in samples),
                      normals=[n for p,n in samples],
                      uv=[(i%12/12,j/7),((i%12+1)/12,j/7),((i%12+1)/12,(j+1)/7),(i%12/12,(j+1)/7)])
        p,n=surface(a,1); q,m=surface(b,1)
        mesh.face([p,q,q-m*.32,p-n*.32],'gas_rubber',[0,0,-1])
    mesh.tube([surface(t,1)[0] for t in np.linspace(-math.pi,math.pi,25)],.14,'gas_rubber',6)
    # The complete face shield is hinged: upper fascia, narrow viewport and chin.
    shield=Mesh()
    def front(t,z):
        depth=np.interp(z,[60.1,64.22,65.85,67.12],[6.4,6.5,6.3,5.80])
        return np.array([CENTER[0]+4.68*math.sin(t),-.4-depth*math.cos(t),z])
    for i in range(20):
        a,b=-1.22+i*2.44/20,-1.22+(i+1)*2.44/20
        # Outside the eye window, solid armour continues around the temples.
        for low,high in ((60.1,62.1),(62.1,64.22),(65.85,67.12)):
            shield.face([front(a,low),front(b,low),front(b,high),front(a,high)],
                        'ballistic_paint',[math.sin((a+b)/2),-math.cos((a+b)/2),.02],
                        uv=[(i/20,(low-60.1)/7.02),((i+1)/20,(low-60.1)/7.02),
                            ((i+1)/20,(high-60.1)/7.02),(i/20,(high-60.1)/7.02)])
        mat='visor' if abs((a+b)/2)<.84 else 'ballistic_paint'
        shield.face([front(a,64.22),front(b,64.22),front(b,65.85),front(a,65.85)],mat,[0,-1,0],
                    uv=[(i/20,0),((i+1)/20,0),((i+1)/20,1),(i/20,1)])
    for z in (60.1,64.22,65.85,67.12):
        shield.tube([front(t,z)+[0,-.06,0] for t in np.linspace(-1.22,1.22,21)],
                    .14 if z in (64.22,65.85) else .12,'gas_rubber',6)
    for side in (-1,1):
        shield.tube([front(side*1.22,z) for z in (60.1,62.1,64.22,65.85,67.12)],.15,'gas_rubber',6)
        shield.tube([front(side*1.22,66.1),[CENTER[0]+side*4.45,-1.8,66.85]],.22,'ballistic_paint',8)
        shield.tube([front(side*.84,z)+[0,-.07,0] for z in (64.22,65.85)],.15,'gas_rubber',6)
        # Shallow reinforcements and shield locks echo the reference hardware.
        x=CENTER[0]+side*4.45
        shield.panel([[x,-3.3,62.3],[x,-2.7,62.3],[x,-2.7,64.3],[x,-3.3,64.3]],
                     [side,0,0],'ballistic_paint','gas_rubber',.08,.14)
    shield.articulate()
    mesh.triangles.extend((rotated(shield,BALLISTIC_PIVOT,BALLISTIC_ANGLE) if raised else shield).triangles)
    for side in (-1,1):
        x=CENTER[0]+side*4.52
        mesh.pin([x,-1.8,66.85],[side,0,0],.57,.18,'gas_rubber',16)
        mesh.pin([x+side*.19,-1.8,66.85],[side,0,0],.36,.12,'hardware',16)
        # Low-profile reinforced rear panels, with two fastening screws.
        mesh.panel([[x,-.2,62.5],[x,1.1,62.3],[x,1.45,64.45],[x,-.2,64.5]],
                   [side,.12,0],'ballistic_paint','gas_rubber',.12,.15)
        for y,z in ((.1,63.0),(.95,64.0)):
            mesh.pin([x+side*.16,y,z],[side,0,0],.105,.06,'hardware',8)
    return mesh


def gas_glass(t,f):
    upper=np.array([CENTER[0]+3.67*math.sin(t),-.65-5.82*math.cos(t),67.0-.20*abs(math.sin(t))])
    lower=np.array([CENTER[0]+3.35*math.sin(t),-.65-6.65*math.cos(t),62.50+.15*abs(math.sin(t))])
    return upper*(1-f)+lower*f


def gas_support(mesh,raised=False):
    # Five-point elastic harness; the stowed pose tightens to the crown anchors.
    def ring(t,z): return [CENTER[0]+3.78*math.sin(t),-.62-4.73*math.cos(t),z]
    for low in (63.85,66.1):
        for i in range(20):
            a=.91+i*(2*math.pi-1.82)/20; b=.91+(i+1)*(2*math.pi-1.82)/20
            mesh.face([ring(a,low),ring(b,low),ring(b,low+.48),ring(a,low+.48)],'gas_rubber',
                      [math.sin((a+b)/2),-math.cos((a+b)/2),0])
    # Split crown straps converge at the compact rear tensioning yoke.
    for side in (-1,1):
        points=[]
        for t in np.linspace(-.70,1.51,13):
            points.append([CENTER[0]+side*(.75+.75*math.sin(t)**2),-.65+4.75*math.sin(t),64.5+5.0*math.cos(t)])
        for i in range(len(points)-1):
            p,q=np.array(points[i]),np.array(points[i+1]); n=unit([side*.15,p[1]+.65,p[2]-64.5])
            mesh.face([p+[-.21,0,0],q+[-.21,0,0],q+[.21,0,0],p+[.21,0,0]],'gas_rubber',n)
        x=CENTER[0]+side*3.55
        mesh.panel([[x,-1.9,64.5],[x,-.85,64.5],[x,-.85,65.55],[x,-1.9,65.55]],
                   [side,0,0],'hardware','gas_rubber',.08,.12)
        end=np.array([CENTER[0]+side*3.35,-2.6,65.15])
        if raised:
            angle=math.radians(GAS_ANGLE); c,s=math.cos(angle),math.sin(angle)
            end=GAS_PIVOT+np.array([[1,0,0],[0,c,-s],[0,s,c]])@(end-GAS_PIVOT)+GAS_OFFSET
        mesh.tube([[x,-1.4,65.1],[CENTER[0]+side*3.7,-.4,67.1] if raised else [x,-2.0,65.15],end],
                  .115,'gas_rubber',6,bones=[13,29,28])
    mesh.panel([[CENTER[0]-.75,4.15,64.6],[CENTER[0]+.75,4.15,64.6],
                [CENTER[0]+.75,4.07,66.3],[CENTER[0]-.75,4.07,66.3]],
               [0,1,0],'gas_rubber','hardware',.12,.18)


def gas_mask(raised=False):
    support=Mesh(); gas_support(support,raised)
    mask=Mesh()
    # A real panoramic window with continuous thick rubber seals.
    for i in range(16):
        a,b=-1.18+i*2.36/16,-1.18+(i+1)*2.36/16
        for j in range(3):
            mask.face([gas_glass(a,j/3),gas_glass(b,j/3),gas_glass(b,(j+1)/3),gas_glass(a,(j+1)/3)],
                      'visor',[0,-1,0],uv=[(i/16,1-j/3),((i+1)/16,1-j/3),((i+1)/16,1-(j+1)/3),(i/16,1-(j+1)/3)])
    for f in (0,1):
        mask.tube([gas_glass(t,f) for t in np.linspace(-1.18,1.18,17)],.23,'gas_rubber',8)
    for side in (-1,1):
        mask.tube([gas_glass(side*1.18,f) for f in np.linspace(0,1,5)],.25,'gas_rubber',8)
        # Molded side cheeks taper into the lower facepiece, closing the seal.
        mask.panel([[CENTER[0]+side*3.25,-3.16,65.4],[CENTER[0]+side*3.22,-3.30,62.5],
                    [CENTER[0]+side*1.3,-6.8,60.8],[CENTER[0]+side*.8,-7.6,61.5],
                    [CENTER[0]+side*2.1,-6.05,63.1]],
                   [side*.65,-.65,-.1],'gas_rubber','gas_rubber',.16,.24)
        mask.pin([CENTER[0]+side*3.34,-2.7,65.15],[side,.1,0],.20,.13,'hardware',10)
    # Raised nose cup inside the window and the substantial lower valve housing.
    mask.panel([[CENTER[0]-1.75,-7.04,61.7],[CENTER[0]+1.75,-7.04,61.7],
                [CENTER[0]+1.24,-7.34,63.7],[CENTER[0]+.45,-7.15,64.8],
                [CENTER[0]-.45,-7.15,64.8],[CENTER[0]-1.24,-7.34,63.7]],
               [0,-1,0],'gas_rubber','gas_rubber',.14,.26)
    mask.panel([[CENTER[0]-1.65,-6.85,60.4],[CENTER[0]+1.65,-6.85,60.4],
                [CENTER[0]+2.0,-6.65,62.5],[CENTER[0]-2.0,-6.65,62.5]],
               [0,-.98,-.1],'gas_rubber','gas_rubber',.16,.22)
    mask.pin([CENTER[0],-7.66,62.25],[0,-1,-.12],.82,.32,'gas_rubber',16)
    mask.pin([CENTER[0],-8.0,62.25],[0,-1,-.12],.59,.10,'optics_metal',16)
    for z in (62.05,62.25,62.45):
        mask.tube([[CENTER[0]-.36,-8.13,z],[CENTER[0]+.36,-8.13,z]],.045,'gas_rubber',4)
    # Large screw-on filter: angled down/forward, metal end grille and seal rings.
    axis=unit([0,-.90,-.435]); start=np.array([CENTER[0],-7.3,60.85])
    cylinder(mask,start,axis,.76,.62,'gas_rubber',16)
    base=start+axis*.57
    cylinder(mask,base,axis,1.57,1.72,'filter_side',20)
    for distance in (0,.20,1.49,1.69):
        cylinder(mask,base+axis*distance,axis,1.63,.13,'hardware' if distance in (0,1.69) else 'gas_rubber',20)
    front=base+axis*1.83; u=np.array([1,0,0]); v=np.cross(axis,u)
    for i in range(20):
        a,b=i*2*math.pi/20,(i+1)*2*math.pi/20
        p=lambda t: front+1.51*(u*math.cos(t)+v*math.sin(t))
        mask.face([front,p(a),p(b)],'filter_front',axis,
                  uv=[(.5,.5),(.5+.5*math.cos(a),.5+.5*math.sin(a)),(.5+.5*math.cos(b),.5+.5*math.sin(b))])
    mask.pin(front+axis*.01,axis,.24,.08,'hardware',12)
    mask.articulate()
    support.triangles.extend((rotated(mask,GAS_PIVOT,GAS_ANGLE,GAS_OFFSET) if raised else mask).triangles)
    return support

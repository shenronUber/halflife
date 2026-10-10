"""Nomade / Bastion: two authored silhouettes per R-01 socket, using existing tiles."""
import math

# Slot order and model identifiers remain defined by build_reference_weapon.
VARIANTS={
 'receiver':(('R-01 / Chassis Nomade','Ossature ajouree, flancs nervures et capot etroit.'),('R-01 / Chassis Bastion','Carter polygonal renforce, longerons et verrou de service.')),
 'barrel':(('Canon a longerons','Trois longerons protegent le tube dans une chemise ouverte.'),('Canon a caisson','Caisson ceramique, brides massives et ouies laterales.')),
 'muzzle':(('Cache-flamme a griffes','Couronne ouverte a six griffes autour du passage central.'),('Compensateur hexagonal','Deux chambres hexagonales et bague frontale renforcee.')),
 'feed':(('Chargeur coude','Corps nervure termine par un sabot coude. Col et prise communs.'),('Chargeur a tambour bas','Tambour sous une prise etroite. Col et prise communs.')),
 'chamber':(('Culasse a anneau','Anneau de traction ouvert sur le chariot mobile.'),('Culasse a double piston','Deux tiges de guidage et un capot de protection mobile.')),
 'ammo':(('Cassette bi-tube','Deux tubes horizontaux retenus par un etrier ouvert.'),('Bloc triple chambre','Trois chambres hexagonales avec leur cerclage frontal.')),
 'projectile':(('Berceau monodard','Un dard large retenu par deux attaches et une pointe conique.'),('Rack a disques','Quatre capsules circulaires dans un casier ouvert.')),
 'optic':(('Dioptre annulaire','Anneau metallique et verre existant dans une monture ouverte.'),('Viseur prismatique','Corps octogonal court, verre en retrait et bloc de reglage.')),
 'underbarrel':(('Stabilisateur replie','Deux branches repliees sous le canon et patins articules.'),('Garde-main carene','Deux joues laterales et un sabot protegent la prise inferieure.')),
 'grip':(('Crosse triangulee','Prise commune et crosse ouverte a deux diagonales.'),('Crosse a joue reglable','Cadre ferme, appui-joue sureleve et plaque amortissante.')),
 'power':(('Reserve toroidale','Reserve annulaire ouverte et connecteurs sur un support plat.'),('Batterie a trois cartouches','Trois cartouches verticales retenues sous un capot commun.')),
 'cooling':(('Dissipateur a pointes','Deux plaques portant chacune neuf picots metalliques.'),('Ventilateurs doubles','Deux petits ventilateurs carenes de chaque cote du canon.')),
}


def part(slot,variant,Mesh):
    assert variant in (2,3)
    heavy=variant==3;m=Mesh();paint=3 if heavy else 2
    if slot=='receiver':
        m.box([0,5,0],[3.5 if heavy else 2.95,24,3.8 if heavy else 3.2],0,.5)
        if heavy:
            m.box([0,3,1.85],[3.9,20,1.5],3,.55)
            for side in (-1,1):
                for y in (-4,1,6,11):m.box([side*1.82,y,1.3],[.55,1.25,2.6],5,.2)
                m.panel(side*1.97,4,1.9,10,.9,1,side)
                m.box([side*1.79,13,.1],[.38,4.2,2.1],0,.25)
                m.panel(side*2,13,.1,3.5,1.2,6,side)
        else:
            m.box([0,3,1.65],[2.1,18,.9],2,.28)
            for side in (-1,1):
                # Open spaces between structural strips retain a lighter profile.
                for y in (-4,0,4,8,12):m.box([side*1.7,y,.2],[.38,.7,2.5],5,.1)
                for z in (-1.25,1.5):m.cyl([side*1.7,-5,z],[side*1.7,14,z],.17,5,8)
                m.panel(side*1.49,5,0,7,1.5,1,side)
                m.box([side*1.7,5,.1],[.65,6,1.8],0,.12)
        m.box([0,15,-1.6],[3,5,2],0,.3)
        m.rail(-4,12,2.7)
        m.box([0,3,-6],[.65,6,.45],5,.12)
        for y in (.2,5.8):m.box([0,y,-4],[.65,.45,4],0,.1)
        m.cyl([0,2.2,-1.8],[0,3,-4.6],.2,5,8)
        m.box([0,-6,0],[3.9,1,3.7],5,.3)
    elif slot=='barrel':
        m.tube([0,17,1.3],[0,31,1.3],.75,.35,5)
        for y in (17.5,28.5,30):m.tube([0,y,1.3],[0,y+.55,1.3],1.15,.78,0)
        if heavy:
            m.box([0,23,1.3],[2.5,9.2,2.55],13,.42)
            for side in (-1,1):m.panel(side*1.26,23,1.3,8,1.7,6,side)
            for y in (19,22,25,27):
                m.box([0,y,2.65],[2.7,.55,.32],5,.1)
                m.box([0,y,-.05],[2.7,.55,.32],0,.1)
        else:
            for angle in (30,150,270):
                a=math.radians(angle);x=1.13*math.cos(a);z=1.3+1.13*math.sin(a)
                m.cyl([x,18.6,z],[x,28.2,z],.22,5,8)
            for y in (19,27):m.tube([0,y,1.3],[0,y+.45,1.3],1.38,.78,2)
        m.rail(17.7,20,2.6)
    elif slot=='muzzle':
        m.tube([0,30.8,1.3],[0,31.7,1.3],1.08,.4,5)
        if heavy:
            for y in (31.7,34):m.tube([0,y,1.3],[0,y+1.6,1.3],1.65,.58,0,6)
            for y in (31.7,33,35.3):m.tube([0,y,1.3],[0,y+.4,1.3],1.76,.58,5,6)
        else:
            m.tube([0,31.7,1.3],[0,32.4,1.3],1.14,.5,0)
            for i in range(6):
                a=2*math.pi*i/6;x=math.cos(a)*.97;z=1.3+math.sin(a)*.97
                m.cyl([x,32.2,z],[x,35.6,z],.19,5,6)
    elif slot=='feed':
        # Every magazine keeps the original insertion neck and hand contact area.
        m.box([-.15,15.25,-2.3],[1.65,1.75,3],5,.12)
        m.box([-.15,15.25,-7],[1.85,2.05,7.9],0,.22)
        for side in (-1,1):m.panel(-.15+side*.935,15.25,-7,1.8,7.2,14,side,rotate=True)
        m.box([-.15,15.25,-3.1],[2,2.2,.4],5,.1)
        if heavy:
            m.cyl([-1.55,15.25,-12.4],[1.25,15.25,-12.4],2.45,0,16)
            for side in (-1,1):
                x=-.15+side*1.42
                m.tube([x,15.25,-12.4],[x+side*.18,15.25,-12.4],2.46,1.87,5,16)
                m.cyl([x,15.25,-12.4],[x+side*.22,15.25,-12.4],.58,5,8)
                m.panel(x+side*.23,15.25,-12.4,2.3,2.3,14,side,repeat=1)
        else:
            for y,z in ((15.5,-10.7),(16,-12),(16.7,-13.1)):
                m.box([-.15,y,z],[1.85,2.15,1.8],0,.28)
                for side in (-1,1):m.panel(-.15+side*.94,y,z,1.8,1.35,14,side)
            m.box([-.15,17,-14],[2.1,2.4,.6],4,.16)
    elif slot=='chamber':
        m.box([2.02,5,.6],[.45,7,1.7],0,.15)
        m.panel(2.27,5,.6,6,1.4,15)
        if heavy:
            for z in (0,1.2):m.cyl([2.65,2.4,z],[2.65,7.6,z],.22,5,8)
            for y in (2.3,7.7):m.box([2.62,y,.6],[.8,.55,1.85],0,.15)
            m.box([2.85,5,.6],[.5,2.2,1.3],3,.22)
        else:
            m.cyl([2.25,6,.6],[2.9,6,.6],.25,5,8)
            m.tube([2.9,6,.6],[3.3,6,.6],.78,.46,5,12)
    elif slot=='ammo':
        m.box([2.05,-2,-.4],[.55,4,2.3],0,.12)
        if heavy:
            for y in (-3.2,-2,-.8):
                m.tube([2.3,y,-.4],[3.35,y,-.4],.58,.37,5,6)
                m.cyl([3.1,y,-.4],[3.17,y,-.4],.36,9,8)
        else:
            for z in (-.92,.25):m.cyl([2.6,-3.8,z],[2.6,-.2,z],.4,7,10)
            for y in (-3.5,-.5):m.box([2.85,y,-.35],[.35,.35,2.25],5,.08)
        m.box([2.08,-4,-.4],[.7,.35,2.7],paint,.1)
    elif slot=='projectile':
        m.box([-2.03,12,-.1],[.4,3.3,2.8],0,.12)
        if heavy:
            for y in (11.15,12.85):
                for z in (-.8,.65):
                    m.cyl([-2.2,y,z],[-2.9,y,z],.58,9,10)
                    m.tube([-2.9,y,z],[-3.06,y,z],.6,.37,5,10)
            for y in (10.45,13.55):m.box([-2.65,y,-.05],[.8,.25,2.9],3,.06)
        else:
            m.cyl([-2.52,12,-1.45],[-2.52,12,.35],.52,5,6)
            m.cyl([-2.52,12,.35],[-2.52,12,1.3],.52,7,6,r2=.02)
            for z in (-1.05,.15):m.box([-2.62,12,z],[.95,2.6,.26],2,.06)
    elif slot=='optic':
        m.box([0,3,3.55],[1.8,4,.9],0,.14)
        radius=1.18 if heavy else 1.12
        if heavy:
            m.box([0,3,4.3],[1.5,3.3,.85],5,.15)
            m.tube([0,.3,5.3],[0,5.7,5.3],radius,.76,0,8)
            for y in (.3,5.2):m.tube([0,y,5.3],[0,y+.5,5.3],1.29,.76,5,8)
            m.box([1.27,3.6,5.3],[.7,2.1,1.15],3,.22)
            glass_y=.62
        else:
            m.box([0,3,4.25],[.65,.9,1.3],5,.12)
            m.tube([0,2.55,5.4],[0,3.45,5.4],radius,.81,5,16)
            m.cyl([1.02,3,5.4],[1.48,3,5.4],.22,0,8)
            glass_y=2.7
        center_z=5.3 if heavy else 5.4;r=.75 if heavy else .8
        glass=[[r*math.cos(i*math.tau/16),glass_y,center_z+r*math.sin(i*math.tau/16)]for i in range(16)]
        uv=[(.5+.25*math.cos(i*math.tau/16),.5+.25*math.sin(i*math.tau/16))for i in range(16)]
        m.face(glass,11,uv=uv);m.face(list(reversed(glass)),11,uv=list(reversed(uv)))
    elif slot=='underbarrel':
        m.box([0,23,-.55],[1.55,4,.4],5,.1)
        if heavy:
            for side in (-1,1):
                m.box([side*.92,23,-1.95],[.4,5.8,2.4],0,.26)
                m.panel(side*1.13,23,-1.95,5.1,1.6,13,side)
            m.box([0,23,-3.15],[2.3,5.3,.55],4,.2)
            for y in (21,25):m.box([0,y,-3.5],[2.5,.6,.4],5,.12)
        else:
            for side in (-1,1):
                m.cyl([side*.7,20.9,-1.05],[side*1.65,26,-2.8],.28,5,8)
                m.cyl([side*.8,21,-1],[side*.8,21,-1.55],.52,0,8)
                m.box([side*1.65,26,-2.9],[.85,1.4,.5],4,.12)
    elif slot=='grip':
        m.box([0,-1.8,-5.2],[2.3,3.3,7],4,.45)
        m.box([0,-1.8,-8.8],[2.6,3.65,.5],0,.15)
        for side in (-1,1):m.panel(side*1.16,-1.8,-5.2,2.7,5.5,4,side)
        if heavy:
            for z in (1.5,-1.6):m.box([0,-11,z],[2.65,10,1.1],0,.28)
            m.box([0,-12,2.65],[3,5.4,1.2],3,.32)
            for x in (-.8,.8):m.cyl([x,-10,1.8],[x,-10,2.6],.2,5,8)
            m.box([0,-16,0],[3.2,1.4,5.6],4,.5)
        else:
            for side in (-1,1):
                m.cyl([side,-6,1],[side,-15,1.5],.28,5,8)
                m.cyl([side,-6,-1],[side,-15,1.5],.24,5,8)
                m.cyl([side,-8,.8],[side,-15,-1.6],.22,0,8)
            m.box([0,-15.5,0],[2.75,.9,5],4,.35)
    elif slot=='power':
        m.box([-2.02,5,-.2],[.7,4.6,3.8],5,.2)
        if heavy:
            for y in (3.6,5,6.4):m.cyl([-3,y,-1.7],[-3,y,1.45],.59,9,10)
            for z in (-1.8,1.65):m.box([-3,5,z],[1.7,4.75,.4],0,.12)
            m.panel(-3.87,5,-.1,3.7,1.3,9,-1)
            m.box([-3.02,5,1.95],[1.65,4.5,.25],3,.06)
        else:
            m.tube([-2.45,5,-.2],[-3.65,5,-.2],1.72,.92,7,16)
            for y in (3.3,6.7):m.box([-3.1,y,-.2],[1.3,.4,3.2],0,.13)
            m.box([-3.1,5,1.6],[1.4,2.6,.4],2,.1)
        m.panel(-3.91,5,.9,1.5,.5,10,-1,repeat=1)
        for y in (3.7,6.3):m.cyl([-2.5,y,1.4],[-2.5,y,2.05],.19,7,8)
    elif slot=='cooling':
        for side in (-1,1):
            m.box([side*1.4,25,1.2],[.3,4,1.7],0,.1)
            if heavy:
                for y in (24,26):
                    m.tube([side*1.58,y,1.2],[side*2.12,y,1.2],.94,.66,5,12)
                    m.cyl([side*2,y,1.2],[side*2.19,y,1.2],.24,7,8)
                    for i in range(4):
                        a=i*math.tau/4
                        m.cyl([side*2.02,y+.2*math.cos(a),1.2+.2*math.sin(a)],[side*2.02,y+.68*math.cos(a+.3),1.2+.68*math.sin(a+.3)],.12,0,6)
            else:
                for y in (23.65,25,26.35):
                    for z in (.45,1.2,1.95):m.cyl([side*1.57,y,z],[side*2.4,y,z],.17,5,6,r2=.1)
    else:raise ValueError(slot)
    return m.tris

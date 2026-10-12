"""Hanging aim above a planted waist, and the seated slide's boot frame."""
import math


def left_lean(yaw):
    """A smooth rearward reach only on the support-hand side of the wall."""
    side=max(0.,math.sin(math.radians(yaw)))
    return aim_deploy(yaw)*side*side


def support_retreat(delta,reach,weight):
    """Back the body away from its fixed palm, without stretching the arm."""
    if weight<=1.e-8:return 0.
    distance=math.sqrt(sum(v*v for v in delta))
    target=distance*(1-weight)+.95*reach*weight
    horizontal=math.sqrt(max(0.,target*target-delta[1]*delta[1]-delta[2]*delta[2]))
    return max(-6.,min(6.,horizontal-delta[0]))


def left_route(yaw):
    angle=yaw%360
    if angle<=180:return aim_deploy(yaw)
    t=max(0.,min(1.,(225-angle)/45))
    return t*t*(3-2*t)


def left_cross_arm(yaw,upper,fore,chest):
    """An elbow in front of the chest, then a bent forearm over the left side.

    The firing direction belongs to the wrist. It must not drag a straight
    upper arm through the torso to put the rifle on the opposite shoulder.
    """
    route=left_route(yaw)
    angle=chest-math.radians(15)
    elbow=(upper*math.cos(math.radians(5))*math.cos(angle),
           upper*math.cos(math.radians(5))*math.sin(angle),upper*math.sin(math.radians(5)))
    wrist=(elbow[0]-fore*math.cos(math.radians(45))*math.sin(chest),
           elbow[1]+fore*math.cos(math.radians(45))*math.cos(chest),
           elbow[2]+fore*math.sin(math.radians(45)))
    return wrist,elbow,route


def aim_deploy(yaw):
    angle=abs((yaw+180)%360-180)
    t=max(0.,min(1.,(angle-45.)/30.))
    return t*t*(3-2*t)


def weapon_pitch(yaw,pitch):
    return -90.+(pitch+90.)*aim_deploy(yaw)


def firing_arm(yaw, pitch, reach):
    """Upright one-hand guard, then an extended arm at shoulder height."""
    angle = math.radians(yaw)
    s, c = math.sin(angle), math.cos(angle)
    crossing = max(0., s, -c)
    deploy=aim_deploy(yaw)
    # Camera pitch articulates the wrist; it does not lift the whole arm.
    arm_angle=angle+math.radians(20*max(0.,s)**2)
    aim=(.94*reach*math.cos(arm_angle),.94*reach*math.sin(arm_angle),0.)
    guard=(6.,-2.,0.)
    extend=deploy**3
    wrist=tuple(a*extend+b*(1-extend)for a,b in zip(aim,guard))
    _,chest,_=body_turn(yaw,pitch)
    chest=math.radians(chest)
    front=14*(1-2*max(0.,s))
    aimed_pole=(front*math.cos(chest),front*math.sin(chest),-8+8*crossing)
    guard_pole=(4.,-10.,-14.)
    pole=tuple(a*extend+b*(1-extend)for a,b in zip(aimed_pole,guard_pole))
    return wrist, pole, crossing


def body_turn(yaw, pitch):
    # The waist and bent knees stay against the wall. Spread a bounded turn
    # through four spine joints; rear shots pass the gun over the shoulder.
    lead = math.sin(math.radians(yaw))
    return 0., max(-45., min(45., yaw - 45 * lead)), .08 * pitch


def head_turn(yaw, pitch):
    _, chest, lean = body_turn(yaw, pitch)
    relative = (yaw - chest + 180) % 360 - 180
    return chest + max(-60., min(60., relative)), lean + max(-45., min(45., pitch - lean))


def slide_foot_rotation():
    # This mesh's toe axis is LOCAL +Y, sole +X. Stand the toes upwards
    # with a ten-degree forward lean, instead of reusing its sideways bind.
    s,c=math.sin(math.radians(10)),math.cos(math.radians(10))
    return ((c,s,0),(0,0,-1),(-s,c,0))


def slide_tucked_foot_rotation():
    # The supporting boot lies under the seat: toe backwards, sole down.
    # Columns are the source boot's local sole, toe and lateral axes.
    s,c=math.sin(math.radians(-30)),math.cos(math.radians(-30))
    return ((0,-c,-s),(0,-s,c),(-1,0,0))

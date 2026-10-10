"""Small authored corrections to the existing MP40-derived left index grip."""
import numpy as np
from scipy.spatial.transform import Rotation
from build_reference_platforms import read_frames, write_frames, globals_of, solve_arm, blend
import build_modular as base

INDEX = (16,17,18,19)


def mounted_index(local):
    """Keep the index outside the common cassette shell, rather than hooked inward."""
    for i,bone in enumerate(INDEX):
        local[bone][:3,:3] = local[bone][:3,:3]@Rotation.from_euler('x',1 if i==0 else 34,degrees=True).as_matrix()
        if i==0:
            local[bone][:3,:3] = local[bone][:3,:3]@Rotation.from_euler('z',5,degrees=True).as_matrix()


def bottom_reload(out):
    """Stabilise the held finger through extraction; preserve the approach/release.

    The old track moves the index even while the palm stays on the magazine.
    A small palm offset also accommodates the widest shared grip shell.
    Finger lengths, mesh and right-hand animation are preserved.
    """
    text,frames = read_frames(out/'reload.smd')
    _,parents,bind = base.skeleton(out/'mp40_hands.smd')
    reference = {b:frames[34][b].copy() for b in INDEX}
    for i,bone in enumerate(INDEX):
        reference[bone][:3,:3] = reference[bone][:3,:3]@Rotation.from_euler('x',-18 if i==0 else 30,degrees=True).as_matrix()
        if i==0:
            reference[bone][:3,:3] = reference[bone][:3,:3]@Rotation.from_euler('z',7,degrees=True).as_matrix()
    mapping = np.linalg.inv(bind[43])@bind[40]
    for t,local in enumerate(frames):
        amount = min(t/18,1.) if t<=93 else max(0.,1-(t-93)/17)
        amount = amount*amount*(3-2*amount)
        if not amount:
            continue
        g = globals_of(local,parents)
        target = g[12].copy()
        target[:3,3] += g[43][:3,:3]@mapping[:3,:3]@np.array([-.65*amount,-.43*amount,0])
        error,_,_ = solve_arm(local,parents,target)
        assert error<1e-5,error
        for bone in INDEX:
            local[bone] = blend(local[bone],reference[bone],min(t/18,1.) if t<=93 else max(0.,1-(t-93)/17))
    write_frames(out/'reload.smd',text,frames)

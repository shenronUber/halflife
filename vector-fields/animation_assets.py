"""Read compiled GoldSrc animation channels for the offline animation workshop.

No model is modified. RLE channels follow Xash3D's R_StudioCalcBones; this
reader exposes integer frames, leaving interpolation to the viewer.
"""
import struct
import numpy as np
from scipy.spatial.transform import Rotation, Slerp


def sequence_info(model, name):
    index = model.sequences.index(name) if isinstance(name, str) else name
    _, offset = struct.unpack_from('<ii', model.data, 164)
    start = offset + index * 176
    return dict(index=index, name=model.sequences[index],
                fps=struct.unpack_from('<f', model.data, start + 32)[0],
                flags=struct.unpack_from('<i', model.data, start + 36)[0],
                frames=struct.unpack_from('<i', model.data, start + 56)[0],
                blends=struct.unpack_from('<i', model.data, start + 120)[0],
                animation=struct.unpack_from('<i', model.data, start + 124)[0],
                group=struct.unpack_from('<i', model.data, start + 156)[0])


def channel(data, offset, frame):
    """Decode one integer sample of a Studio RLE animation channel."""
    while True:
        valid, total = struct.unpack_from('<BB', data, offset)
        if not total or valid > total or not valid:
            raise ValueError('Invalid Studio animation RLE run')
        if frame < total:
            return struct.unpack_from('<h', data, offset + 2 * (min(frame, valid - 1) + 1))[0]
        frame -= total
        offset += 2 * (valid + 1)


def sequence_frames(model, name, blend=None):
    """Return local 4x4 transforms; select or average the authored aim blends."""
    info = sequence_info(model, name)
    data = model.data
    if info['group']:
        data = model.path.with_name(model.path.stem + f"{info['group']:02}.mdl").read_bytes()
    count, boneoff = struct.unpack_from('<ii', model.data, 140)
    values = [struct.unpack_from('<12f', model.data, boneoff + bone * 112 + 64) for bone in range(count)]
    choices = [blend] if blend is not None else ([4] if info['blends'] == 9 else list(range(min(2, info['blends']))))
    tracks = []
    for choice in choices:
        frames = []
        for frame in range(info['frames']):
            local = []
            for bone, raw in enumerate(values):
                base = info['animation'] + (choice * count + bone) * 12
                offsets = struct.unpack_from('<6H', data, base)
                v = np.array(raw[:6])
                for axis, off in enumerate(offsets):
                    if off:
                        v[axis] += channel(data, base + off, frame) * raw[6 + axis]
                m = np.eye(4)
                m[:3, 3] = v[:3]
                m[:3, :3] = Rotation.from_euler('xyz', v[3:]).as_matrix()
                local.append(m)
            frames.append(local)
        tracks.append(np.array(frames))
    result = tracks[0]
    if len(tracks) == 2:
        result = result.copy()
        result[:, :, :3, 3] = (tracks[0][:, :, :3, 3] + tracks[1][:, :, :3, 3]) / 2
        for frame in range(len(result)):
            for bone in range(count):
                rotations = Rotation.from_matrix([tracks[0][frame, bone, :3, :3], tracks[1][frame, bone, :3, :3]])
                result[frame, bone, :3, :3] = Slerp([0, 1], rotations)([.5]).as_matrix()[0]
    return result


def globals_of(local, parents):
    result = []
    for bone, m in enumerate(local):
        result.append(result[parents[bone]] @ m if parents[bone] >= 0 else m.copy())
    return np.array(result)


def packed_frames(frames):
    """Position and quaternion, suitable for shortest-path interpolation in JS."""
    return np.round(np.concatenate([frames[:, :, :3, 3],
                    Rotation.from_matrix(frames[:, :, :3, :3].reshape(-1, 3, 3)).as_quat().reshape(*frames.shape[:2], 4)], axis=2), 6).tolist()

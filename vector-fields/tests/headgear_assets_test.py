"""Verify compiled head weighting and rigid following on the real animation rigs."""
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from animation_assets import globals_of, sequence_frames
from build_headgear import OUT, ROOT
from studio_assets import Studio


def run():
    child = Studio(OUT / 'headgear.mdl')
    assert child.parts[0][1] == 12 and child.mesh({0: 0}) == []
    reference = Studio(ROOT / 'generated/personas/persona_rig.mdl')
    for name, matrix in zip(child.names, child.bind):
        assert np.max(np.abs(matrix - reference.bind[reference.names.index("Bip01 Head" if name.startswith("VF_Headgear") else name)])) < 1e-5
    count, samples, maximum, carrier_error = [], 0, 0., 0.
    for variant in range(1, 12):
        triangles = child.mesh({0: variant}); count.append(len(triangles))
        assert 500 < len(triangles) < 3200
        assert {child.names[v['b']] for _, t in triangles for v in t} <= {'Bip01 Head','VF_Headgear','VF_HeadgearFlex'}
        positions = np.array([v['p'] for _, t in triangles for v in t])
        assert positions[:, 2].max() > (70 if variant <= 3 or variant in (8,9,11) else 68)
        # The respirator filter hangs below the chin in its worn pose.
        assert positions[:, 2].min() > (58 if variant == 10 else 59)
        assert np.isfinite(positions).all()
        head = child.names.index('Bip01 Head')
        local = (np.linalg.inv(child.bind[head]) @ np.column_stack([positions, np.ones(len(positions))]).T).T
        # The accessory must be rigid relative to the actual animated head, not
        # merely translated with the player's origin or evaluated independently.
        for path in [ROOT / 'generated/personas/persona_rig.mdl'] + list((ROOT / 'generated/third-person').glob('r01_tp*.mdl')):
            rig = Studio(path); target = rig.names.index('Bip01 Head')
            assert all(name in rig.names or name.startswith("VF_Headgear") for name in child.names)
            for sequence in ('look_idle', 'run', 'crawl', 'crouch_idle', 'jump', 'ref_aim_mp5', 'die_backwards'):
                frames = sequence_frames(rig, sequence)
                original = sequence_frames(reference, sequence)
                assert len(frames) == len(original)
                for i in range(0, len(frames), max(1, len(frames) // 5)):
                    frame = frames[i]
                    world = globals_of(frame, rig.parents)[target]
                    expected = globals_of(original[i], reference.parents)[reference.names.index('Bip01 Head')]
                    carrier_error = max(carrier_error, float(np.max(np.abs(world - expected))))
                    posed = (world @ local.T).T
                    recovered = (np.linalg.inv(world) @ posed.T).T
                    maximum = max(maximum, float(np.max(np.abs(recovered - local)))); samples += 1
    # Only the shield is additive; opaque shell/bronze cannot inherit its blending.
    off = struct.unpack_from('<i', child.data, 184)[0]
    flags = {n: struct.unpack_from('<i', child.data, off + i * 80 + 64)[0]
             for i, (n, *_) in enumerate(child.textures)}
    assert flags['visor.bmp'] == 32 and all(v == 0 for k, v in flags.items() if k != 'visor.bmp')
    # Check embedded indexed diffuse maps, including compiler resizing errors.
    material_details = {}
    for name, width, height, indices, palette in child.textures:
        assert (width, height) == (256, 256), (name, width, height)
        colors = np.frombuffer(palette, dtype='uint8').reshape(256, 3)
        rgb = colors[np.frombuffer(indices, dtype='uint8')]
        variation = float(rgb.std(axis=0).mean())
        if name != 'visor.bmp':
            assert variation > 4, (name, variation)
        material_details[name] = dict(size=[width, height], variation=variation)
    assert maximum < 1e-9
    # Compare the actual compiled lenses/windows in all five paired designs.
    # Supports stay on the head; moving pieces preserve their rigid shape/UVs.
    from headgear_designs import VISOR_PIVOT, OPTICS_PIVOT, OPTICS_ANGLE
    from headgear_extra_designs import BALLISTIC_PIVOT,BALLISTIC_ANGLE,GAS_PIVOT,GAS_ANGLE,GAS_OFFSET
    def window(variant,material):
        return np.unique(np.round([v['p'] for name, tri in child.mesh({0: variant})
                                   if child.textures[name][0] == material+'.bmp' for v in tri], 5), axis=0)
    paired_errors={}
    for label,down,up,material,pivot,degrees,offset in [
            ('riot',1,3,'visor',VISOR_PIVOT,-112,np.zeros(3)),
            ('nvg_red',4,6,'lens_red',OPTICS_PIVOT,OPTICS_ANGLE,np.zeros(3)),
            ('nvg_green',5,7,'lens_green',OPTICS_PIVOT,OPTICS_ANGLE,np.zeros(3)),
            ('ballistic',8,9,'visor',BALLISTIC_PIVOT,BALLISTIC_ANGLE,np.zeros(3)),
            ('gas_mask',10,11,'visor',GAS_PIVOT,GAS_ANGLE,GAS_OFFSET)]:
        down_points,up_points=window(down,material),window(up,material)
        angle=np.radians(degrees); c,s=np.cos(angle),np.sin(angle)
        rotation=np.array([[1,0,0],[0,c,-s],[0,s,c]])
        expected=(down_points-pivot)@rotation.T+pivot+offset
        error=float(np.linalg.norm(expected[:,None]-up_points[None,:],axis=2).min(axis=1).max())
        # StudioMDL coalesces almost coincident source vertices within .01 units.
        assert len(down_points)==len(up_points) and error<.025,(label,len(down_points),len(up_points),error)
        paired_errors[label]=error
    # Third-person carriers have a different default bind pose but retain the
    # same animated head channels (with StudioMDL's small quantization error).
    assert carrier_error < .02, carrier_error
    report = dict(passed=True,triangles=count,pose_samples=samples,max_rigid_head_error=maximum,
                  bone='Bip01 Head',reference_bind_equal=True,max_carrier_head_pose_error=carrier_error,
                  source_sha256=hashlib.sha256(child.data).hexdigest(),materials=material_details,
                  visor_hinge_error=paired_errors['riot'],paired_pose_errors=paired_errors,
                  headgear_designs=6,static_body_variants=11,paired_designs=5,
                  collision='render-only assembly; no server entity or collision code changed')
    (ROOT / 'build/headgear-assets-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS headgear assets:', count, 'triangles;', samples, 'head poses, error', maximum)
    return report


if __name__ == '__main__':
    run()

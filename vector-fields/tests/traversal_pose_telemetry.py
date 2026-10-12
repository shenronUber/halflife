"""Check actual lower-body movement against the intentional left lean."""
import math,re


def anchored_lean(text,reference=None,network_quantum=0):
    pattern=(r'VFTraversalLean phase=(\d+) weight=([\d.-]+) retreat=([\d.-]+) lift=([\d.-]+) support_extension=([\d.-]+) wall_yaw=([\d.-]+)\s+'
             r'VFTraversalAnchor phase=(\d+) hip=([\d.,-]+) knee=([\d.,-]+)')
    rows=[]
    for phase,weight,retreat,lift,extension,yaw,anchor_phase,hip,knee in re.findall(pattern,text):
        assert phase==anchor_phase
        rows.append((float(weight),float(retreat),float(lift),float(extension),float(yaw),[float(v)for v in (hip+','+knee).split(',')]))
    assert rows,'missing paired lean/anchor telemetry'
    if reference is None:
        neutral=[r for r in rows if r[0]<.00001]
        assert neutral,'missing neutral anchor'
        reference=neutral[-1][-1]
    maximum=0.
    for weight,retreat,lift,extension,yaw,point in rows:
        assert 0<=weight<=1 and abs(retreat)<=6.001 and abs(lift-3*weight)<.0001
        if weight<.00001:assert abs(retreat)<.0001 and abs(lift)<.0001
        offset=[-retreat*math.cos(math.radians(yaw)),-retreat*math.sin(math.radians(yaw)),lift]*2
        error=max(abs(a-b-c)for a,b,c in zip(point,reference,offset))
        maximum=max(maximum,error)
    # Two network samples can round origin in opposite directions. delta.lst
    # encodes origin in 1/32 units; offline/local poses keep the original bound.
    tolerance=max(.035,2*network_quantum+.002)
    assert maximum<tolerance,('unexpected lower-body motion beyond authored left lean',maximum,tolerance)
    left=[r for r in rows if r[0]>.9]
    assert not left or min(r[3]for r in left)>.92,('support arm must extend at left side',left[:2])
    return dict(samples=len(rows),max_world_error=maximum,tolerance=tolerance,reference=reference,
                left_lean_samples=sum(r[0]>.05 for r in rows),maximum_lift=max(r[2]for r in rows),
                maximum_retreat=max(r[1]for r in rows),minimum_left_support_extension=min((r[3]for r in left),default=None))

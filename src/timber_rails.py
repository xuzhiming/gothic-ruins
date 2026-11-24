"""Horizontal half-timber rail spans for timber_face.

Sole and mid rails break only at ops explicitly marked opening == "door"
(street ground-floor doors). Windows — even a low sill that overlaps the mid
rail, and regardless of kind=flat/round — leave the rails continuous; that is
the existing facade style. The storey head rail stays continuous when it sits
above the door. Rails stop at the existing jamb posts (s ± w/2 ± pad).
Pure Python; no Blender or mathutils.
"""

def timber_rail_segments(W, z0, z1, zz, ops, rail_h=0.16, pad=0.09, margin=0.05, min_len=0.08):
    """Return (v0, v1) spans along the face for a rail whose centre is at height zz.

    ops items use the same keys as timber_face / windows_row: s, w, optional
    sill (default 0) and h (default 2.4).
    """
    hy = rail_h / 2.0
    blocked = []
    for o in ops or ():
        # kind is shared by doors and windows; only the explicit door flag cuts a rail.
        if o.get("opening") != "door":
            continue
        sill = float(o.get("sill", 0.0))
        oh = float(o.get("h", 2.4))
        oz0, oz1 = z0 + sill, z0 + oh
        if zz + hy <= oz0 or zz - hy >= oz1:
            continue
        blocked.append((float(o["s"]) - float(o["w"]) / 2.0 - pad,
                        float(o["s"]) + float(o["w"]) / 2.0 + pad))
    blocked.sort()
    merged = []
    for a, b in blocked:
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    cur = margin
    end = W - margin
    segs = []
    for a, b in merged:
        if a > cur + min_len:
            segs.append((cur, min(a, end)))
        cur = max(cur, b)
    if end - cur > min_len:
        segs.append((cur, end))
    return segs

"""Full-field timber geometry audit vs the T24 alley baseline Blend.

blender -b building.blend -P check/test_timber_scope.py -- [baseline.blend] [report.json]

Verifies the published baseline triangle counts for the six houses that the
over-broad t27u rail gap accidentally edited, then compares every timber
mesh (not the 29-mesh isolation set) against that baseline. Only the three
street-door frames W0/NW/NE may change; W1/W2/W3/E0/E1/E2 must return to
the baseline mesh (hash, not just a triangle count).
"""
import bpy, json, hashlib, sys
from pathlib import Path

ROOT = Path(bpy.data.filepath).parent
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BASE = Path(args[0]) if args else Path("/workspace/gothic-t27u-baseline/building.blend")
OUT = Path(args[1]) if len(args) > 1 else ROOT / "t27u-evidence" / "timber_scope.json"

# Verified against gothic-t27u-baseline/building.blend (T24 published alley baseline).
# If a baseline file does not match these counts, fail with the actual numbers;
# do not treat a count check as a substitute for a geometry hash.
BASELINE_TRIS = {
    "House_W1_timber": 2647,
    "House_W2_timber": 2522,
    "House_W3_timber": 2514,
    "House_E0_timber": 2906,
    "House_E1_timber": 3184,
    "House_E2_timber": 2159,
}
ALLOWED = {"House_W0_timber", "House_NW_timber", "House_NE_timber"}
MUST_RESTORE = set(BASELINE_TRIS)


def ntris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def ghash(ob):
    verts = [[round(float(c), 6) for c in v.co] for v in ob.data.vertices]
    faces = [list(p.vertices) for p in ob.data.polygons]
    return hashlib.sha256(json.dumps([verts, faces], separators=(",", ":")).encode()).hexdigest()


def is_timber(ob):
    if ob.type != "MESH":
        return False
    n = ob.name
    if n.endswith("_timber") or "timber" in n.lower():
        return True
    mats = [(m.name if m else "") for m in ob.data.materials]
    return any("timber" in m.lower() for m in mats)


def snapshot():
    rows = {}
    for ob in bpy.context.scene.objects:
        if not is_timber(ob):
            continue
        rows[ob.name] = dict(
            name=ob.name, verts=len(ob.data.vertices), faces=len(ob.data.polygons),
            tris=ntris(ob), sha256=ghash(ob),
            materials=[m.name for m in ob.data.materials if m],
        )
    return rows


current = snapshot()
assert BASE.is_file(), f"missing T24 baseline blend: {BASE}"
bpy.ops.wm.open_mainfile(filepath=str(BASE))
baseline = snapshot()

# 1) confirm the expected restore-house counts on the baseline itself
baseline_count_errors = []
for name, want in BASELINE_TRIS.items():
    got = baseline.get(name, {}).get("tris")
    if got != want:
        baseline_count_errors.append({"name": name, "expected_tris": want, "baseline_tris": got})

changed, unexpected, restore_ok, restore_bad = [], [], [], []
all_names = sorted(set(current) | set(baseline))
for name in all_names:
    a, b = current.get(name), baseline.get(name)
    if a is None or b is None or a["sha256"] != b["sha256"] or a["tris"] != b["tris"]:
        rec = dict(name=name,
                   baseline_tris=None if b is None else b["tris"],
                   current_tris=None if a is None else a["tris"],
                   baseline_sha=None if b is None else b["sha256"],
                   current_sha=None if a is None else a["sha256"],
                   allowed=name in ALLOWED)
        changed.append(rec)
        if name in MUST_RESTORE:
            restore_bad.append(rec)
        elif name not in ALLOWED:
            unexpected.append(rec)
    elif name in MUST_RESTORE:
        restore_ok.append(dict(name=name, tris=a["tris"], sha256=a["sha256"]))

missing_allowed = sorted(n for n in ALLOWED if n not in current or n not in baseline)
# The three door houses must actually differ from baseline (otherwise the door gap is missing).
missing_door_delta = sorted(n for n in ALLOWED if n in current and n in baseline and current[n]["sha256"] == baseline[n]["sha256"])

report = dict(
    PASS=not baseline_count_errors and not unexpected and not restore_bad
         and not missing_allowed and not missing_door_delta
         and len(restore_ok) == len(MUST_RESTORE),
    baseline=str(BASE),
    current=str(ROOT / "building.blend"),
    baseline_object_count=len(baseline),
    current_object_count=len(current),
    baseline_count_errors=baseline_count_errors,
    allowed_changed=sorted(ALLOWED),
    must_restore_tris=BASELINE_TRIS,
    changed=changed,
    unexpected_changes=unexpected,
    restore_hash_mismatches=restore_bad,
    restore_ok=restore_ok,
    missing_allowed=missing_allowed,
    missing_door_delta=missing_door_delta,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2))
print("TIMBER SCOPE")
print("  baseline_count_errors", baseline_count_errors)
print("  changed", [(c["name"], c["baseline_tris"], c["current_tris"]) for c in changed])
print("  unexpected", [c["name"] for c in unexpected])
print("  restore_bad", [c["name"] for c in restore_bad])
print("  restore_ok", len(restore_ok), "/", len(MUST_RESTORE))
print("  missing_door_delta", missing_door_delta)
print("PASS" if report["PASS"] else "FAIL")
assert report["PASS"], (
    f"timber scope failed: baseline_counts={baseline_count_errors} "
    f"unexpected={ [c['name'] for c in unexpected] } "
    f"restore_bad={ [c['name'] for c in restore_bad] } "
    f"missing_door_delta={missing_door_delta}"
)

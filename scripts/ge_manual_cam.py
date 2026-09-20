"""M2A.7: manual CAM readiness walk-through for the frozen GE geometry.

Steps (run with the FEM environment's Python, one per process):

  survey   Geometry for a 3-axis mill, before any toolpath: the part in the CAM frame
           (deck frame turned about z so the pin axis lies along y), every face by type
           and orientation, which of the six axis setup directions can see each face
           (line of sight along the tool axis, from a z-buffer), concave radii and the
           seat-recess groove that limit tool size, and cavity depths that set reach.
           Writes out/ge_manual_cam/survey.json.

Line of sight ignores the tool's radius and holder; radius and reach are checked
separately. A face is reachable from a direction when a point 0.3 mm off the surface,
along its outward normal, has no material above it along that direction.

    vendor/fem-env/bin/python scripts/ge_manual_cam.py survey
"""

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
from FreeCAD import Vector  # noqa: E402

GEOMETRY = ROOT / "data" / "ge_manual" / "Iteration1_partitioned.FCStd"
OUT = ROOT / "out" / "ge_manual_cam"
PIN_REF = Vector(-20.97366, -74.76046, 44.72459)
PIN_AXIS = (0.030278, -0.999542, 0.0)
OFFSET = 0.3        # mm off the surface for the line-of-sight test
PIXEL = 0.1         # mm, z-buffer cell
DEFLECTION = 0.05   # mm, tessellation
REACH_FRACTION = 0.95
DIRECTIONS = {"+z": (0, 0, 1), "-z": (0, 0, -1), "+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0)}


def cam_shape():
    """The part in the CAM frame: deck frame turned about z through the pin reference."""
    doc = FreeCAD.openDocument(str(GEOMETRY))
    shape = doc.getObject("Bracket").Shape.copy()
    FreeCAD.closeDocument(doc.Name)
    angle = math.degrees(math.atan2(PIN_AXIS[0], -PIN_AXIS[1]))
    shape.rotate(Vector(PIN_REF.x, PIN_REF.y, 0), Vector(0, 0, 1), -angle)
    return shape, -angle


def classify(face):
    t = type(face.Surface).__name__
    u0, u1, v0, v1 = face.ParameterRange
    if t == "Plane":
        n = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if abs(n.z) > 0.999:
            return "plane horizontal " + ("up" if n.z > 0 else "down")
        if abs(n.z) < 1e-3:
            return "plane vertical"
        return "plane sloped"
    if t == "Cylinder":
        a = face.Surface.Axis
        axis = "z" if abs(a.z) > 0.999 else "y" if abs(a.y) > 0.999 else "x" if abs(a.x) > 0.999 else "oblique"
        return f"cylinder {axis} r{face.Surface.Radius:.3f}"
    return t.replace("Surface", "").lower()


def basis(d):
    """Rotation taking direction d to +z (rows: new x, new y, new z)."""
    d = np.array(d, float)
    helper = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(helper, d)
    x /= np.linalg.norm(x)
    return np.array([x, np.cross(d, x), d])


def zbuffer(points, tris, R, pixel=PIXEL):
    """Highest projected coordinate along R[2] per cell of the plane R[0], R[1]."""
    p = points @ R.T
    lo = p[:, :2].min(axis=0) - 1
    shape = np.ceil((p[:, :2].max(axis=0) + 1 - lo) / pixel).astype(int)
    buf = np.full(shape, -np.inf)
    for a, b, c in p[tris]:
        area2 = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area2) < 1e-12:
            continue
        i0, j0 = np.ceil((np.minimum(np.minimum(a, b), c)[:2] - lo) / pixel - 0.5).astype(int)
        i1, j1 = np.floor((np.maximum(np.maximum(a, b), c)[:2] - lo) / pixel - 0.5).astype(int)
        if i0 > i1 or j0 > j1:
            continue
        gx, gy = np.meshgrid(lo[0] + (np.arange(i0, i1 + 1) + 0.5) * pixel,
                             lo[1] + (np.arange(j0, j1 + 1) + 0.5) * pixel, indexing="ij")
        w1 = ((gx - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (gy - a[1])) / area2
        w2 = ((b[0] - a[0]) * (gy - a[1]) - (gx - a[0]) * (b[1] - a[1])) / area2
        inside = (w1 >= 0) & (w2 >= 0) & (w1 + w2 <= 1)
        if inside.any():
            z = a[2] + w1 * (b[2] - a[2]) + w2 * (c[2] - a[2])
            view = buf[i0:i1 + 1, j0:j1 + 1]
            view[inside] = np.maximum(view[inside], z[inside])
    return buf, lo


def visible(samples, buf, lo, R):
    q = samples @ R.T
    ij = np.floor((q[:, :2] - lo) / PIXEL).astype(int)
    ij = np.clip(ij, 0, np.array(buf.shape) - 1)
    return q[:, 2] >= buf[ij[:, 0], ij[:, 1]] - 1e-6


def survey():
    OUT.mkdir(parents=True, exist_ok=True)
    shape, angle = cam_shape()
    pts, tris, face_of, samples, normals, areas = [], [], [], [], [], []
    for k, f in enumerate(shape.Faces):
        v, t = f.tessellate(DEFLECTION)
        if not t:
            continue
        base = sum(len(p) for p in pts)
        P = np.array([[p.x, p.y, p.z] for p in v])
        T = np.array(t)
        pts.append(P)
        tris.append(T + base)
        c = P[T].mean(axis=1)
        for ci, tri in zip(c, P[T]):
            uv = f.Surface.parameter(Vector(*ci))
            n = f.normalAt(*uv)
            normals.append((n.x, n.y, n.z))
            samples.append(ci)
            areas.append(0.5 * np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])))
            face_of.append(k)
    points, tris = np.vstack(pts), np.vstack(tris)
    samples, normals = np.array(samples), np.array(normals)
    areas, face_of = np.array(areas), np.array(face_of)
    off = samples + OFFSET * normals
    seen = {}
    for name, d in DIRECTIONS.items():
        R = basis(d)
        buf, lo = zbuffer(points, tris, R)
        seen[name] = visible(off, buf, lo, R)
        print(name, "done", flush=True)

    faces = []
    for k, f in enumerate(shape.Faces):
        m = face_of == k
        a = areas[m].sum()
        frac = {n: float(areas[m & s].sum() / a) if a else 0.0 for n, s in seen.items()}
        any_dir = np.zeros(m.sum(), bool)
        for s in seen.values():
            any_dir |= s[m]
        c = f.CenterOfMass
        faces.append({"face": f"Face{k + 1}", "kind": classify(f), "area_mm2": round(f.Area, 2),
                      "center_cam": [round(c.x, 2), round(c.y, 2), round(c.z, 2)],
                      "visible_fraction": {n: round(v, 3) for n, v in frac.items()},
                      "union_fraction": round(float(areas[m][any_dir].sum() / a) if a else 0.0, 3)})

    def coverage(names):
        mask = np.zeros(len(samples), bool)
        for n in names:
            mask |= seen[n]
        return round(float(areas[mask].sum() / areas.sum()), 4)

    setups = {"top only (+z)": ["+z"], "top + bottom (+z, -z)": ["+z", "-z"],
              "top + bottom + pin side (+z, -z, +y, -y)": ["+z", "-z", "+y", "-y"], "all six": list(DIRECTIONS)}
    kinds = collections.defaultdict(lambda: {"faces": 0, "area_mm2": 0.0})
    for f in faces:
        kinds[f["kind"]]["faces"] += 1
        kinds[f["kind"]]["area_mm2"] = round(kinds[f["kind"]]["area_mm2"] + f["area_mm2"], 1)
    unreachable = [f for f in faces if f["union_fraction"] < REACH_FRACTION]
    bb = shape.BoundBox
    rec = {"geometry": str(GEOMETRY.relative_to(ROOT)), "cam_frame": {
               "rotation_about_z_deg": round(angle, 4), "about": [PIN_REF.x, PIN_REF.y, 0],
               "note": "deck frame turned so the pin axis lies along -y; z = 0 is the base bottom"},
           "bounding_box_mm": {"x": [round(bb.XMin, 3), round(bb.XMax, 3)], "y": [round(bb.YMin, 3), round(bb.YMax, 3)],
                               "z": [round(bb.ZMin, 3), round(bb.ZMax, 3)]},
           "volume_mm3": round(shape.Volume, 3), "surface_area_mm2": round(float(areas.sum()), 1),
           "method": {"offset_mm": OFFSET, "pixel_mm": PIXEL, "deflection_mm": DEFLECTION, "samples": len(samples)},
           "area_coverage_by_setups": {k: coverage(v) for k, v in setups.items()},
           "area_visible_per_direction": {n: coverage([n]) for n in DIRECTIONS},
           "faces_by_kind": dict(sorted(kinds.items(), key=lambda kv: -kv[1]["area_mm2"])),
           "faces_not_reached_by_any_axis_direction": unreachable, "faces": faces}
    (OUT / "survey.json").write_text(json.dumps(rec, indent=2))
    np.savez_compressed(OUT / "samples.npz", samples=samples, normals=normals, areas=areas, face_of=face_of,
                        **{f"seen{n}": s for n, s in seen.items()})
    print(json.dumps({k: rec[k] for k in ("cam_frame", "bounding_box_mm", "area_coverage_by_setups",
                                           "area_visible_per_direction")}, indent=1))
    print("faces below", REACH_FRACTION, "union:", [(f["face"], f["kind"], f["area_mm2"], f["union_fraction"]) for f in unreachable])


# --- CAM jobs ----------------------------------------------------------------

BITS = ROOT / "tooling" / "Bit" / "ge_manual"
DATA = ROOT / "data" / "ge_manual" / "cam"
POST_PROCESSOR = "refactored_linuxcnc"  # ships with FreeCAD 1.1.3; LinuxCNC controller
SPINDLE_MAX_RPM = 12000                 # assumed generic VMC
SIM_RES = 0.2                           # mm, PathSimulator heightmap cell
CHECK_OFFSET = 0.4                      # mm off (air) / into (part) the surface for the stock check
FINISHED_FRACTION = 0.95
MATERIAL = "ti6al4v"                    # G-code is posted for the challenge baseline

# Tool number: (bit file, flutes, cutting role). Balls are modelled straight to 45 mm;
# physically they are necked long-reach tools.
TOOLS = {1: ("12mm_Endmill_L45.fctb", 4, "rough"), 2: ("8mm_Endmill_L30.fctb", 4, "holes"),
         3: ("6mm_Ball_L45.fctb", 2, "finish"), 4: ("4mm_Ball_L45.fctb", 2, "blends")}

# Shop assumptions, not vendor data: (cutting speed m/min, feed per tooth mm) for coated
# solid carbide, flood coolant, per material and role. Replace with the chosen tool
# vendor's figures before cutting metal.
CUTTING = {
    "ti6al4v": {"rough": (45, 0.05), "holes": (40, 0.03), "finish": (60, 0.04), "blends": (50, 0.025)},
    "al7075_t651": {"rough": (350, 0.08), "holes": (250, 0.05), "finish": (400, 0.06), "blends": (350, 0.04)},
    "al6061_t651": {"rough": (400, 0.08), "holes": (300, 0.05), "finish": (450, 0.06), "blends": (400, 0.04)},
    "ss17_4ph_h1025": {"rough": (70, 0.05), "holes": (60, 0.03), "finish": (90, 0.04), "blends": (80, 0.025)},
    "aisi4140_qt": {"rough": (110, 0.06), "holes": (90, 0.04), "finish": (130, 0.05), "blends": (110, 0.03)},
}


def tool_diameter(n):
    return float(json.loads((BITS / TOOLS[n][0]).read_text())["parameter"]["Diameter"].split()[0])


def feeds(material, n):
    """(rpm, feed mm/min, plunge mm/min) from the shop assumptions, capped at the spindle limit."""
    vc, fz = CUTTING[material][TOOLS[n][2]]
    d = tool_diameter(n)
    rpm = min(vc * 1000 / (math.pi * d), SPINDLE_MAX_RPM)
    feed = rpm * TOOLS[n][1] * fz
    return round(rpm), round(feed), round(feed / 3)


def rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


# Each setup turns the CAM-frame part about x so its tool axis becomes +z.
SETUPS = {
    "op10": {"title": "Setup 1: base underside up", "direction": "-z", "rot_x_deg": 180,
             "workholding": "vise on a 10 mm grip band of stock left beyond the lug tips",
             "stock_ext": {"xy": 3.0, "zpos": 2.0, "zneg": 10.0}},
    "op20": {"title": "Setup 2: top", "direction": "+z", "rot_x_deg": 0,
             "workholding": "soft jaws machined to the base outline, gripping z 3-18 mm; base bottom on parallels",
             "stock_ext": {"xy": 3.0, "zpos": 2.0, "zneg": 0.0}},
    "op30": {"title": "Setup 3: pin side +y", "direction": "+y", "rot_x_deg": 90,
             "workholding": "angle plate on the base bottom, bolted through the four finished counterbores",
             "stock_ext": {"xy": 1.0, "zpos": 1.0, "zneg": 1.0}},
    "op40": {"title": "Setup 4: pin side -y", "direction": "-y", "rot_x_deg": -90,
             "workholding": "angle plate on the base bottom, bolted through the four finished counterbores",
             "stock_ext": {"xy": 1.0, "zpos": 1.0, "zneg": 1.0}},
}


def fixtures(setup_id, bb):
    """Coarse workholding boxes in the setup frame: (xmin, xmax, ymin, ymax, zmin, zmax)."""
    if setup_id == "op10":   # vise jaws on the grip band below the part
        z0 = bb.ZMin - 10.0
        return {"vise jaw -x": (bb.XMin - 23, bb.XMin - 3, bb.YMin - 3, bb.YMax + 3, z0 - 30, z0 + 8),
                "vise jaw +x": (bb.XMax + 3, bb.XMax + 23, bb.YMin - 3, bb.YMax + 3, z0 - 30, z0 + 8)}
    if setup_id == "op20":   # soft jaws on the base outline
        return {"soft jaw -x": (-21.6 - 15, -21.6, -162.1, 12.6, -20, 18.0),
                "soft jaw +x": (67.7, 67.7 + 15, -162.1, 12.6, -20, 18.0)}
    # angle plate behind the base bottom: part z < 0 maps to setup y > 0 (op30) or y < 0 (op40)
    sign = 1 if setup_id == "op30" else -1
    return {"angle plate": (-80, 120, 0, 40, -250, 100) if sign > 0 else (-80, 120, -40, 0, -100, 250)}


def face_list(pred, shape):
    return [f"Face{i}" for i, f in enumerate(shape.Faces, 1) if pred(i, f)]


def concave_blend(f):
    """R2/R2.54 concave blends: the faces the 4 mm ball must finish."""
    t = type(f.Surface).__name__
    if t not in ("Cylinder", "Sphere", "Toroid"):
        return False
    r = f.Surface.MinorRadius if t == "Toroid" else f.Surface.Radius
    if r > 2.6:
        return False
    u0, u1, v0, v1 = f.ParameterRange
    p, n = f.valueAt((u0 + u1) / 2, (v0 + v1) / 2), f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    if t == "Cylinder":
        c, a = f.Surface.Center, f.Surface.Axis
        d = p - c
        d = d - a * d.dot(a)
    elif t == "Sphere":
        d = p - f.Surface.Center
    else:
        c, a = f.Surface.Center, f.Surface.Axis
        d = p - c
        d = d - a * d.dot(a)
        d.normalize()
        d = p - (c + d * f.Surface.MajorRadius)
    return n.dot(d) < 0


def one_per_hole(shape, faces):
    """One half-cylinder per hole centre, so Helix does not cut a hole twice."""
    seen, keep = [], []
    for name in faces:
        c = shape.Faces[int(name[4:]) - 1].Surface.Center
        if all((c.x - x) ** 2 + (c.y - y) ** 2 > 0.01 for x, y in seen):
            seen.append((c.x, c.y))
            keep.append(name)
    return keep


class _HeadlessInput:
    @staticmethod
    def selectedToolController():
        return None

    @staticmethod
    def chooseToolController(controllers):
        return controllers[0]


def build_job(setup_id, part, visibility):
    import Path.Main.Job as PathJob
    import Path.Op.Helix as PathHelix
    import Path.Op.Surface as PathSurface
    import Path.Tool.Controller as PathToolController
    from Path.Tool.toolbit import ToolBit
    from PathScripts import PathUtils

    PathUtils.UserInput = _HeadlessInput
    st = SETUPS[setup_id]
    shape = part.copy()
    shape.rotate(Vector(0, 0, 0), Vector(1, 0, 0), st["rot_x_deg"])
    doc = FreeCAD.newDocument(setup_id)
    model = doc.addObject("Part::Feature", "Bracket")
    model.Shape = shape
    doc.recompute()
    job = PathJob.Create("Job", [model], None)
    job.Label = f"{setup_id} {st['title']}"
    e = st["stock_ext"]
    for ext in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos"):
        setattr(job.Stock, ext, e["xy"])
    job.Stock.ExtZpos, job.Stock.ExtZneg = e["zpos"], e["zneg"]
    for tc in list(job.Tools.Group):
        doc.removeObject(tc.Tool.Name)
        doc.removeObject(tc.Name)
    tcs = {}
    for n, (bit, _, role) in TOOLS.items():
        rpm, feed, plunge = feeds(MATERIAL, n)
        b = ToolBit.from_file(BITS / bit)
        tc = PathToolController.Create(f"T{n} {b.label}", b.attach_to_doc(doc=doc), n)
        tc.HorizFeed, tc.VertFeed, tc.SpindleSpeed = f"{feed} mm/min", f"{plunge} mm/min", rpm
        job.Proxy.addToolController(tc)
        tcs[n] = tc
    doc.recompute()
    base = job.Model.Group[0]
    bs = base.Shape
    for i in (0, len(bs.Faces) // 2, len(bs.Faces) - 1):   # the clone keeps the face order
        assert abs(bs.Faces[i].Area - shape.Faces[i].Area) < 1e-6
    top = bs.BoundBox.ZMax

    def surface(name, tc, faces=None, stepover=10.0, sample=0.2, multipass=False, stepdown=2.0,
                offset=0.0, final=None, pattern="ZigZag", angle=0.0):
        op = PathSurface.Create(name)
        op.ToolController = tcs[tc]
        if faces:
            op.Base = [(base, faces)]
        op.StepOver, op.SampleInterval, op.BoundBox = stepover, f"{sample} mm", "BaseBoundBox"
        op.CutPattern, op.CutPatternAngle = pattern, angle
        op.LayerMode = "Multi-pass" if multipass else "Single-pass"
        op.DepthOffset = f"{offset} mm"
        for pn in ("StepDown", "FinalDepth", "StartDepth"):
            op.setExpression(pn, None)
        op.StepDown, op.StartDepth = f"{stepdown} mm", f"{top + e['zpos']} mm"
        op.FinalDepth = f"{final if final is not None else bs.BoundBox.ZMin} mm"
        return op

    def helix(name, tc, faces, start, final):
        op = PathHelix.Create(name)
        op.ToolController = tcs[tc]
        op.Base = [(base, faces)]
        for pn in ("FinalDepth", "StartDepth"):
            op.setExpression(pn, None)
        op.StartDepth, op.FinalDepth = f"{start} mm", f"{final} mm"
        return op

    vis = lambda d, i: visibility[d][i - 1] >= 0.5  # noqa: E731
    blends = lambda d: face_list(lambda i, f: concave_blend(f) and vis(d, i), bs)  # noqa: E731
    if setup_id == "op10":      # base bottom at z = 0, part below; the cavity is at most 39.2 deep
        floor = -40.5
        surface("Rough", 1, stepover=40, sample=0.5, multipass=True, stepdown=2.0, offset=0.5, final=floor)
        surface("Finish", 3, stepover=10, sample=0.2, final=floor)
        surface("Blends R2", 4, faces=blends("-z"), stepover=8, sample=0.15, final=floor)
        holes = one_per_hole(bs, face_list(lambda i, f: classify(f) in ("cylinder z r5.156", "cylinder z r5.334"), bs))
        helix("Bolt holes", 2, holes, start=0.0, final=-8.1)
    elif setup_id == "op20":    # base bottom at z = 0; the soft jaws reach z = 18
        floor = 18.5
        surface("Rough", 1, stepover=40, sample=0.5, multipass=True, stepdown=2.0, offset=0.5, final=floor)
        surface("Finish", 3, stepover=10, sample=0.2, final=floor)
        surface("Blends R2", 4, faces=[f for f in blends("+z") if bs.Faces[int(f[4:]) - 1].BoundBox.ZMin >= floor - 0.01],
                stepover=8, sample=0.15, final=floor)
        cb = one_per_hole(bs, face_list(lambda i, f: classify(f) == "cylinder z r10.541", bs))
        helix("Counterbores", 1, cb, start=25.5, final=10.45)
        seat = face_list(lambda i, f: (classify(f).startswith("plane horizontal up") and abs(f.BoundBox.ZMax - 7.8486) < 0.01)
                         or (type(f.Surface).__name__ == "Toroid" and abs(f.Surface.MinorRadius - 2.54) < 0.01), bs)
        surface("Counterbore floors", 4, faces=seat, stepover=8, sample=0.15, multipass=True, stepdown=0.5,
                final=7.8486)
    else:                       # pin side: bore through both lugs, then the side-only faces
        d = SETUPS[setup_id]["direction"]
        side_only = face_list(lambda i, f: visibility[d][i - 1] >= 0.5 and visibility["+z"][i - 1] < 0.5
                              and visibility["-z"][i - 1] < 0.5, bs)
        if setup_id == "op30":
            bores = face_list(lambda i, f: classify(f).startswith("cylinder z r9.557"), bs)
            zr = [bs.Faces[int(b[4:]) - 1].BoundBox for b in bores]
            helix("Lug bores", 1, bores[:1], start=max(b.ZMax for b in zr) + 1.0, final=min(b.ZMin for b in zr) - 0.5)
        if side_only:
            surface("Side faces", 4, faces=side_only, stepover=8, sample=0.15,
                    final=bs.BoundBox.ZMin)
    doc.recompute()
    return doc, job, base


def simulate_ops(job, ops, resolution=SIM_RES):
    """PathSimulator replay of the given operations on the job stock (as cam_check.simulate)."""
    import PathSimulator
    from cam_check import _linear_moves
    from PathScripts import PathUtils

    stock = job.Stock.Shape
    sim = PathSimulator.PathSim()
    sim.BeginSimulation(stock, resolution)
    pos = FreeCAD.Placement(Vector(0, 0, stock.BoundBox.ZMax), FreeCAD.Rotation())
    moves = 0
    for op in ops:
        sim.SetToolShape(op.ToolController.Tool.Shape, resolution / 5)
        retract = None
        for cmd in PathUtils.getPathWithPlacement(op).Commands:
            for move in _linear_moves(pos, cmd, resolution, retract):
                pos = sim.ApplyCommand(pos, move)
                moves += 1
            if cmd.Name in ("G81", "G82", "G83", "G73"):
                retract = cmd.r
            elif cmd.Name == "G80":
                retract = None
    top, inner = sim.GetResultMesh()
    return top, inner, moves


def zmap_replay(job, ops, res=SIM_RES):
    """Independent z-map replay: stamp each tool's profile along every move onto a grid.

    Flat endmills stamp a disc at the tip height; ball ends stamp tip + r - sqrt(r^2 - d^2).
    Moves are sampled every res / 2 (arcs split into chords by cam_check._linear_moves).
    Rapids (G0) that would remove stock are counted: a rapid through material is a crash.
    Returns the stock-top grid, its grid origin and the rapid-into-stock counts per op.
    """
    from cam_check import _linear_moves
    from PathScripts import PathUtils

    bb = job.Stock.Shape.BoundBox
    pad = 12
    nx, ny = int(math.ceil(bb.XLength / res)) + 2 * pad, int(math.ceil(bb.YLength / res)) + 2 * pad
    x0, y0 = bb.XMin - pad * res, bb.YMin - pad * res
    H = np.full((nx, ny), -1e9)
    H[pad:nx - pad, pad:ny - pad] = bb.ZMax
    rapids = {}
    for op in ops:
        tool = op.ToolController.Tool
        r = tool.Diameter.Value / 2
        w = int(math.ceil(r / res))
        di, dj = np.meshgrid(np.arange(-w, w + 1) * res, np.arange(-w, w + 1) * res, indexing="ij")
        d2 = di ** 2 + dj ** 2
        prof = np.full(d2.shape, np.inf)
        inside = d2 <= r * r
        prof[inside] = (r - np.sqrt(r * r - d2[inside])) if tool.ShapeType == "Ballend" else 0.0
        pos = FreeCAD.Placement(Vector(0, 0, bb.ZMax + 20), FreeCAD.Rotation())
        rapid_hits = 0
        for cmd in PathUtils.getPathWithPlacement(op).Commands:
            for move in _linear_moves(pos, cmd, res, None):
                p = move.Parameters
                a = pos.Base
                bpt = Vector(p.get("X", a.x), p.get("Y", a.y), p.get("Z", a.z))
                n = max(1, int(math.ceil((bpt - a).Length / (res / 2))))
                rapid = move.Name in ("G0", "G00")
                for k in range(1, n + 1):
                    q = a + (bpt - a) * (k / n)
                    i = int(round((q.x - x0) / res))
                    j = int(round((q.y - y0) / res))
                    if not (w <= i < nx - w and w <= j < ny - w):
                        continue
                    win = H[i - w:i + w + 1, j - w:j + w + 1]
                    cut = q.z + prof
                    if rapid:
                        if (cut < win - 0.05).any():
                            rapid_hits += 1
                        continue
                    np.minimum(win, cut, out=win)
                pos = FreeCAD.Placement(bpt, FreeCAD.Rotation())
        if rapid_hits:
            rapids[op.Label] = rapid_hits
    return H, (x0, y0), rapids


def check_samples(setup_id, H, origin, sam, res=SIM_RES):
    """Per-sample stock check in the setup frame: cleared (air point free) and gouged (part point cut)."""
    R = rot_x(SETUPS[setup_id]["rot_x_deg"])

    def lookup(q):
        i = np.clip(np.floor((q[:, 0] - origin[0]) / res + 0.5).astype(int), 0, H.shape[0] - 1)
        j = np.clip(np.floor((q[:, 1] - origin[1]) / res + 0.5).astype(int), 0, H.shape[1] - 1)
        return H[i, j]

    air = (sam["samples"] + CHECK_OFFSET * sam["normals"]) @ R.T
    inside = (sam["samples"] - CHECK_OFFSET * sam["normals"]) @ R.T
    return air[:, 2] >= lookup(air) - 1e-3, inside[:, 2] > lookup(inside) + 1e-3


def evaluate(setup_id, job, meshes, sam):
    """Per-sample stock check in the setup frame: cleared (air point free) and gouged (part point cut).

    The stock top per SIM_RES column is rasterised from PathSimulator's result meshes
    (the untouched top and the cut surface), as in the Gate 4 residual check.
    """
    from cam_check import column_grid, rasterize

    R = rot_x(SETUPS[setup_id]["rot_x_deg"])
    bb = job.Stock.Shape.BoundBox
    x, y = column_grid(bb, SIM_RES)
    nx, ny = len(x), len(y)
    H = np.full((nx, ny), bb.ZMin)
    for mesh in meshes:
        if mesh.CountFacets:
            p = np.array([tuple(v) for v in mesh.Topology[0]])
            H = np.maximum(H, rasterize(p, mesh.Topology[1], x, y, "top"))

    def lookup(q):
        i = np.clip(np.floor((q[:, 0] - bb.XMin) / SIM_RES).astype(int), 0, nx - 1)
        j = np.clip(np.floor((q[:, 1] - bb.YMin) / SIM_RES).astype(int), 0, ny - 1)
        return H[i, j]

    air = (sam["samples"] + CHECK_OFFSET * sam["normals"]) @ R.T
    inside = (sam["samples"] - CHECK_OFFSET * sam["normals"]) @ R.T
    cleared = air[:, 2] >= lookup(air) - 1e-3
    gouged = inside[:, 2] > lookup(inside) + 1e-3
    return cleared, gouged


def collisions(setup_id, job, bb):
    """Toolpath points whose tool (tip up to its length) enters a workholding box."""
    import Path
    from PathScripts import PathUtils

    boxes = fixtures(setup_id, bb)
    hits = {}
    for op in job.Operations.Group:
        tool = op.ToolController.Tool
        r = tool.Diameter.Value / 2
        length = tool.Length.Value
        pos = [None, None, job.Stock.Shape.BoundBox.ZMax + 10]
        for cmd in PathUtils.getPathWithPlacement(op).Commands:
            p = cmd.Parameters
            pos = [p.get("X", pos[0]), p.get("Y", pos[1]), p.get("Z", pos[2])]
            if pos[0] is None or pos[1] is None:
                continue
            for name, (x0, x1, y0, y1, z0, z1) in boxes.items():
                if (x0 - r < pos[0] < x1 + r and y0 - r < pos[1] < y1 + r
                        and pos[2] < z1 and pos[2] + length > z0):
                    hits.setdefault(op.Label, {}).setdefault(name, 0)
                    hits[op.Label][name] += 1
    return {"boxes": {k: [round(v, 2) for v in b] for k, b in boxes.items()}, "hits": hits}


def cam(setups):
    import time

    from cam_check import post_process, simulate
    from Path.Main.Sanity import Sanity

    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    part, _ = cam_shape()
    sam = dict(np.load(OUT / "samples.npz"))
    survey_rec = json.loads((OUT / "survey.json").read_text())
    visibility = {d: [f["visible_fraction"][d] for f in survey_rec["faces"]] for d in DIRECTIONS}
    for sid in setups:
        rec = {"setup": sid, **SETUPS[sid], "material_for_gcode": MATERIAL, "timings_s": {}, "ok": False}
        t0 = time.perf_counter()
        doc, job, base = build_job(sid, part, visibility)
        rec["timings_s"]["build_and_recompute"] = round(time.perf_counter() - t0, 1)
        rec["operations"] = []
        for op in job.Operations.Group:
            cmds = op.Path.Commands
            zs = [c.Parameters["Z"] for c in cmds if "Z" in c.Parameters]
            rec["operations"].append({"label": op.Label, "type": op.Proxy.__class__.__module__.split(".")[-1],
                                      "tool": op.ToolController.Label, "commands": len(cmds),
                                      "status": op.getStatusString(),
                                      "z_min": round(min(zs), 3) if zs else None,
                                      "faces": len(op.Base[0][1]) if getattr(op, "Base", None) else "whole model"})
        doc.saveAs(str(DATA / f"{sid}.FCStd"))
        report = Sanity.CAMSanity(job, output_file=str(OUT / f"{sid}_setup_sheet.html"))
        rec["sanity"] = [{"type": q["squawkType"], "note": q["Note"]} for section in report.data.values()
                         if isinstance(section, dict) for q in section.get("squawkData", [])]
        t = time.perf_counter()
        rec["gcode_lines"] = post_process(job, OUT / f"{sid}.ngc")
        rec["timings_s"]["post"] = round(time.perf_counter() - t, 1)
        t = time.perf_counter()
        top, inner, moves = simulate(job, SIM_RES)
        rec["timings_s"]["simulate"] = round(time.perf_counter() - t, 1)
        rec["simulated_moves"] = moves
        t = time.perf_counter()
        cleared, gouged = evaluate(sid, job, (top, inner), sam)
        rec["timings_s"]["stock_check"] = round(time.perf_counter() - t, 1)
        np.savez_compressed(OUT / f"{sid}_check.npz", cleared=cleared, gouged=gouged)
        rec["collisions"] = collisions(sid, job, base.Shape.BoundBox)
        vis = sam[f"seen{SETUPS[sid]['direction']}"]
        a = sam["areas"]
        rec["visible_area_mm2"] = round(float(a[vis].sum()), 1)
        rec["cleared_fraction_of_visible"] = round(float(a[vis & cleared].sum() / a[vis].sum()), 4)
        rec["gouged_area_mm2"] = round(float(a[gouged].sum()), 2)
        rec["ok"] = True
        (OUT / f"{sid}.json").write_text(json.dumps(rec, indent=2, default=str))
        FreeCAD.closeDocument(doc.Name)
        print(sid, json.dumps({k: rec[k] for k in ("timings_s", "operations", "gcode_lines", "simulated_moves",
                                                   "cleared_fraction_of_visible", "gouged_area_mm2", "collisions")},
                              default=str), flush=True)


# --- Assessment ----------------------------------------------------------------

LD_LIMIT = 6.0   # reach / diameter above which a cut is unverified without vendor data or a trial
HOLDER_R = 15.0  # mm, holder nose radius assumed for the stick-out check


def feature_groups(shape, survey_rec):
    """Assign every face to one machining feature, first match wins."""
    faces = survey_rec["faces"]

    def vis(i, d):
        return faces[i - 1]["visible_fraction"][d]

    def union(i):
        return faces[i - 1]["union_fraction"]

    rules = [
        ("Inner bore chamfers (clevis gap side)", lambda i, f, k: k == "cone" and union(i) < REACH_FRACTION),
        ("Underside cavity undercut strip", lambda i, f, k: union(i) < REACH_FRACTION),
        ("Base bottom (mating face)", lambda i, f, k: k == "plane horizontal down"),
        ("Bolt holes (Ø10.31, B2 Ø10.67)", lambda i, f, k: k in ("cylinder z r5.156", "cylinder z r5.334")),
        ("Nut seats and R2.54 counterbore blends", lambda i, f, k: (k == "plane horizontal up" and f.BoundBox.ZMax < 8)
         or (k == "toroid" and abs(f.Surface.MinorRadius - 2.54) < 0.01)),
        ("Counterbore walls (Ø21.08)", lambda i, f, k: k == "cylinder z r10.541"),
        ("Lug bores (Ø19.11)", lambda i, f, k: k == "cylinder y r9.557"),
        ("Outer bore chamfers", lambda i, f, k: k == "cone"),
        ("Cavity vertical R2 corners", lambda i, f, k: k == "cylinder z r2.000" and concave_blend(f) and vis(i, "-z") >= 0.5),
        ("Underside cavity walls and floors", lambda i, f, k: vis(i, "-z") >= 0.5 and f.BoundBox.ZMin > 0.5
         and not concave_blend(f)),
        ("Concave R2 blends and corners", lambda i, f, k: concave_blend(f)),
        ("Convex R2 edge rounds", lambda i, f, k: type(f.Surface).__name__ in ("Cylinder", "Sphere", "Toroid")
         and not concave_blend(f) and (getattr(f.Surface, "Radius", 0) <= 2.01
                                       or getattr(f.Surface, "MinorRadius", 9) <= 2.01)),
        ("Lug tips and arm-root fillets (R3.175, R8.175, R17.78)", lambda i, f, k: k.startswith("cylinder")
         and ("r3.175" in k or "r8.175" in k or "r17.780" in k)),
        ("Base outline corners (R15.24) and end rounds (R12.7)", lambda i, f, k: k.startswith("cylinder")),
        ("Top and side facets (planes)", lambda i, f, k: k.startswith("plane")),
        ("Small B-spline patches", lambda i, f, k: k == "bspline"),
    ]
    groups = collections.OrderedDict((name, []) for name, _ in rules)
    groups["Other"] = []
    for i, f in enumerate(shape.Faces, 1):
        k = classify(f)
        for name, pred in rules:
            if pred(i, f, k):
                groups[name].append(i)
                break
        else:
            groups["Other"].append(i)
    return {k: v for k, v in groups.items() if v}


def stick_out(setup_id, part):
    """Stick-out each cutting move needs so a Ø(2 x HOLDER_R) holder nose clears the part.

    For every cutting move of an operation: the highest part surface within HOLDER_R of
    the tool axis (square window, conservative) minus the tool tip height. Compared with
    the tool's modelled flute reach, and as reach over diameter.
    """
    import Path  # noqa: F401
    from PathScripts import PathUtils

    shape = part.copy()
    shape.rotate(Vector(0, 0, 0), Vector(1, 0, 0), SETUPS[setup_id]["rot_x_deg"])
    v, t = shape.tessellate(0.1)
    pts = np.array([[p.x, p.y, p.z] for p in v])
    buf, lo = zbuffer(pts, np.array(t), np.eye(3), pixel=0.5)
    w = int(round(HOLDER_R / 0.5))
    hmax = buf.copy()
    for axis in (0, 1):
        base = hmax.copy()
        for k in range(1, w + 1):
            hmax = np.maximum(hmax, np.roll(base, k, axis=axis))
            hmax = np.maximum(hmax, np.roll(base, -k, axis=axis))
    doc = FreeCAD.openDocument(str(DATA / f"{setup_id}.FCStd"))
    job = [o for o in doc.Objects if o.Name == "Job"][0]
    out = []
    for op in job.Operations.Group:
        tool = op.ToolController.Tool
        d, flute = tool.Diameter.Value, tool.CuttingEdgeHeight.Value
        need, pos = 0.0, [None, None, None]
        for cmd in PathUtils.getPathWithPlacement(op).Commands:
            p = cmd.Parameters
            pos = [p.get("X", pos[0]), p.get("Y", pos[1]), p.get("Z", pos[2])]
            if cmd.Name not in ("G1", "G01", "G2", "G02", "G3", "G03") or None in pos:
                continue
            i, j = (np.floor((np.array(pos[:2]) - lo) / 0.5)).astype(int)
            if 0 <= i < hmax.shape[0] and 0 <= j < hmax.shape[1] and np.isfinite(hmax[i, j]):
                need = max(need, hmax[i, j] - pos[2])
        out.append({"setup": setup_id, "op": op.Label, "tool": op.ToolController.Label, "diameter_mm": d,
                    "stick_out_needed_mm": round(float(need), 1), "fluted_reach_mm": flute,
                    "reach_over_diameter": round(float(need) / d, 1), "within_modelled_reach": bool(need <= flute),
                    "long_reach": bool(need / d > LD_LIMIT)})
    FreeCAD.closeDocument(doc.Name)
    return out


def assess():
    shape, _ = cam_shape()
    survey_rec = json.loads((OUT / "survey.json").read_text())
    sam = dict(np.load(OUT / "samples.npz"))
    a, fo = sam["areas"], sam["face_of"]
    finished = np.zeros(len(a), bool)
    gouged = np.zeros(len(a), bool)
    by_setup, setups = {}, {}
    for sid, st in SETUPS.items():
        rec = json.loads((OUT / f"{sid}.json").read_text())
        chk = np.load(OUT / f"{sid}_check.npz")
        vis = sam[f"seen{st['direction']}"]
        done = vis & chk["cleared"]
        by_setup[sid] = done
        finished |= done
        gouged |= chk["gouged"]
        setups[sid] = rec

    reach = [r for sid in SETUPS for r in stick_out(sid, shape)]
    groups = feature_groups(shape, survey_rec)
    features = []
    for name, ids in groups.items():
        m = np.isin(fo, np.array(ids) - 1)
        area = float(a[m].sum())
        fin = float(a[m & finished].sum() / area) if area else 0.0
        gou = float(a[m & gouged].sum())
        union = float(np.mean([survey_rec["faces"][i - 1]["union_fraction"] for i in ids]))
        where = {sid: round(float(a[m & d].sum() / area), 3) for sid, d in by_setup.items() if a[m & d].sum() > 0.01 * area}
        reasons = []
        if union < REACH_FRACTION:
            status = "blocked"
            reasons.append("no axis-aligned setup has line of sight; needs 3+2 / 5-axis or a special tool")
        elif fin < FINISHED_FRACTION:
            status = "unverified"
            reasons.append(f"reachable, but the simulated toolpaths finish only {fin:.0%} of the area to within "
                           f"{CHECK_OFFSET} mm")
        else:
            status = "ready (simulation)"
        if gou > 0.5:
            status = "blocked"
            reasons.append(f"simulated gouge {gou:.1f} mm2")
        features.append({"feature": name, "faces": len(ids), "area_mm2": round(area, 1),
                         "finished_fraction": round(fin, 3), "gouged_area_mm2": round(gou, 2),
                         "finished_in": where, "status": status, "reasons": reasons, "face_ids": ids})

    material_feeds = {mat: {f"T{n} {TOOLS[n][0].removesuffix('.fctb')}": dict(zip(("rpm", "feed_mm_min", "plunge_mm_min"),
                                                                                  feeds(mat, n)))
                            for n in TOOLS} for mat in CUTTING}
    rec = {"geometry": survey_rec["geometry"], "cam_frame": survey_rec["cam_frame"],
           "finished_area_fraction": round(float(a[finished].sum() / a.sum()), 4),
           "gouged_area_mm2": round(float(a[gouged].sum()), 2),
           "check": {"offset_mm": CHECK_OFFSET, "sim_resolution_mm": SIM_RES, "finished_fraction": FINISHED_FRACTION},
           "post_processor": POST_PROCESSOR, "spindle_max_rpm": SPINDLE_MAX_RPM, "gcode_material": MATERIAL,
           "cutting_assumptions": CUTTING, "feeds_by_material": material_feeds, "tool_reach": reach,
           "setups": {sid: {k: r[k] for k in ("title", "direction", "workholding", "operations", "gcode_lines",
                                               "simulated_moves", "timings_s", "sanity", "collisions",
                                               "cleared_fraction_of_visible", "gouged_area_mm2")}
                      for sid, r in setups.items()},
           "features": features}
    (OUT / "assessment.json").write_text(json.dumps(rec, indent=2, default=str))
    np.savez_compressed(OUT / "finished.npz", finished=finished, gouged=gouged)
    print("finished area", rec["finished_area_fraction"], "gouged", rec["gouged_area_mm2"])
    for f in features:
        print(f"{f['status']:20s} {f['finished_fraction']:.3f} {f['area_mm2']:8.1f} {f['feature']} {f['finished_in']} {f['reasons']}")
    for r in reach:
        print("reach", r)


def _poly(shape, tol=0.1):
    import pyvista as pv

    v, t = shape.tessellate(tol)
    return pv.PolyData(np.array([[p.x, p.y, p.z] for p in v]), np.c_[np.full(len(t), 3), np.array(t)].ravel())


def render():
    """Setup views with workholding and toolpaths, and the feature readiness map."""
    import pyvista as pv
    from PathScripts import PathUtils

    part, _ = cam_shape()
    colors = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
    for sid, st in SETUPS.items():
        doc = FreeCAD.openDocument(str(DATA / f"{sid}.FCStd"))
        job = [o for o in doc.Objects if o.Name == "Job"][0]
        base = job.Model.Group[0]
        p = pv.Plotter(off_screen=True, window_size=(1600, 1100))
        p.set_background("white")
        p.add_mesh(_poly(base.Shape), color="#bdbdbd", opacity=0.55)
        p.add_mesh(_poly(job.Stock.Shape, 0.5), style="wireframe", color="#555555", line_width=1)
        for name, (x0, x1, y0, y1, z0, z1) in fixtures(sid, base.Shape.BoundBox).items():
            box = pv.Box(bounds=(x0, x1, y0, y1, max(z0, job.Stock.Shape.BoundBox.ZMin - 40),
                                 min(z1, job.Stock.Shape.BoundBox.ZMax + 5)))
            p.add_mesh(box, color="#fdae61", opacity=0.35)
        legend = []
        for k, op in enumerate(job.Operations.Group):
            pts, pos = [], [None, None, None]
            for cmd in PathUtils.getPathWithPlacement(op).Commands:
                q = cmd.Parameters
                pos = [q.get("X", pos[0]), q.get("Y", pos[1]), q.get("Z", pos[2])]
                if None not in pos and cmd.Name in ("G1", "G01", "G2", "G02", "G3", "G03"):
                    pts.append(pos)
            if len(pts) > 1:
                pts = np.array(pts[:: max(1, len(pts) // 60000)])
                line = pv.lines_from_points(pts)
                p.add_mesh(line, color=colors[k % len(colors)], line_width=1)
                legend.append([f"{op.Label} ({op.ToolController.Label})", colors[k % len(colors)]])
        p.add_legend(legend, bcolor="white", size=(0.34, 0.16), loc="upper right")
        p.add_axes(color="black")
        p.view_isometric()
        p.enable_parallel_projection()
        p.add_text(f"{sid} {st['title']} | tool axis +z of this view = part {st['direction']}\n"
                   f"workholding (orange, coarse boxes): {st['workholding']}", font_size=10, color="black")
        p.screenshot(str(OUT / f"{sid}_setup.png"))
        p.close()
        FreeCAD.closeDocument(doc.Name)

    rec = json.loads((OUT / "assessment.json").read_text())
    status_color = {"ready (simulation)": "#1a9850", "unverified": "#fdae61", "blocked": "#d73027"}
    face_status = {}
    for f in rec["features"]:
        for i in f["face_ids"]:
            face_status[i] = f["status"]
    p = pv.Plotter(off_screen=True, window_size=(1800, 900), shape=(1, 2))
    for col, (view, label) in enumerate((("iso", "top, iso"), ("bottom", "underside"))):
        p.subplot(0, col)
        p.set_background("white")
        for status, color in status_color.items():
            faces = [part.Faces[i - 1] for i, s in face_status.items() if s == status]
            if faces:
                p.add_mesh(_poly(_compound(faces), 0.05), color=color)
        p.add_axes(color="black")
        if view == "iso":
            p.view_isometric()
        else:
            p.camera_position = [(20, -75, -400), (20, -75, 30), (0, 1, 0)]
        p.enable_parallel_projection()
        p.add_text(f"feature readiness ({label}): green ready in simulation, amber unverified, red blocked",
                   font_size=10, color="black")
    p.screenshot(str(OUT / "readiness_map.png"))
    p.close()


def _compound(faces):
    import Part

    return Part.makeCompound(faces)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["survey", "cam", "assess", "render"])
    parser.add_argument("--setups", nargs="+", choices=list(SETUPS), default=list(SETUPS))
    args = parser.parse_args()
    if args.step == "survey":
        survey()
    elif args.step == "cam":
        cam(args.setups)
    elif args.step == "assess":
        assess()
    elif args.step == "render":
        render()


if __name__ == "__main__":
    main()

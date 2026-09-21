"""ge_bracket: the parametric demo part (M2.1, D-04, D-05, D-06, D-14).

A two-arm clevis bracket built around SimJEB's interfaces, in SimJEB's frame
(mm, +z up, "out" is -x). The geometry is a FreeCAD Python feature whose six
length properties are bound by expression to the aliases of a `Params`
spreadsheet. Setting a cell and recomputing rebuilds the shape. The arm-root
fillet edges are chosen inside the builder by position, never by edge index,
so the part itself has no topological-naming dependency.

Faces that constraints, mesh groups and CAM operations use are found by the
geometric predicates in PREDICATES, re-run after every recompute (D-04,
REQ-OPT-008). Each predicate must match exactly one face.

The frozen record for this part is docs/ge-bracket-part.md. Importing this
module needs FreeCAD, so run it with the FEM environment's Python
(scripts/fem_env.py finds it). A saved
document stores the feature's class as parts.ge_bracket.GeBracket, so the
repository root must be on sys.path when the document is opened.
"""

import math

import FreeCAD
import Part
from FreeCAD import Vector

# Interfaces, measured from SimJEB design 148 (148.fem spider nodes and the
# surf = 2/3 nodes of 148field.csv). The same in all 381 designs.
BOLT_CENTRES = (  # interfaces 2-5, in 148.fem RBE2 order; holes run z = 0 up
    (51.948, 1.552),
    (0.042, -0.270),
    (-0.202, -148.094),
    (38.142, -146.964),
)
BOLT_HOLE_D = 10.30  # SimJEB hole; the bolt is 9.525, the nut-face ID 10.287
PIN = (-21.036, -75.065, 44.801)  # load node; pin axis is +y
PIN_D = 19.05
CLEVIS_GAP = 21.64  # inner arm faces, measured -85.52 and -63.88

# Fixed design choices: not agent parameters.
BOSS_D = 20.0  # base lobe round each bolt; clears the 14.173 mm nut-face OD
FOOT_AHEAD = 35.0  # arm foot runs from the lug's -x tangent to pin x + this
POCKET_CLEAR_ARM = 12.0  # pocket edge to arm outer face, in y
POCKET_WALL = 6.0  # pocket edge to base outline
POCKET_CLEAR_BOLT = 14.0  # pocket edge to bolt axis
POCKET_CORNER_R = 4.0  # > the 3 mm radius of the 6 mm endmill
CENTRE_HOLE_X = 39.5  # centre hole on the clevis midplane, clear of the arms
DENSITY_G_MM3 = 4.43e-3  # Ti-6Al-4V, SimJEB deck MAT1 (4.43e-9 t/mm^3)

# The frozen parameter record (D-05): at most six, each of one closed kind.
PARAMS = {
    "base_thickness": {"kind": "wall_thickness", "baseline": 18.0, "min": 12.0, "max": 24.0, "step": 0.5},
    "arm_thickness": {"kind": "wall_thickness", "baseline": 8.0, "min": 4.0, "max": 12.0, "step": 0.5},
    "lug_wall": {"kind": "wall_thickness", "baseline": 10.0, "min": 5.0, "max": 15.0, "step": 0.5},
    "arm_root_fillet": {"kind": "fillet_radius", "baseline": 5.0, "min": 3.0, "max": 8.0, "step": 0.5},
    "base_pocket_depth": {"kind": "pocket_depth", "baseline": 3.0, "min": 1.0, "max": 8.0, "step": 0.5},
    "centre_hole_diameter": {"kind": "hole_diameter", "baseline": 14.0, "min": 8.0, "max": 20.0, "step": 1.0},
}
PROPERTY = {name: "".join(w.capitalize() for w in name.split("_")) for name in PARAMS}

TOL = 1e-3


def _hull(points):
    """Convex hull of 2D points, counter-clockwise (monotone chain)."""
    pts = sorted(set(points))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out

    lower, upper = half(pts), half(reversed(pts))
    return lower[:-1] + upper[:-1]


def _face_xy(points):
    return Part.Face(Part.makePolygon([Vector(x, y, 0) for x, y in points + points[:1]]))


def layout(p):
    """Derived dimensions the builder and the predicates share."""
    px, py, pz = PIN
    lug_r = PIN_D / 2 + p["lug_wall"]
    y_in = (py + CLEVIS_GAP / 2, py - CLEVIS_GAP / 2)  # +y arm, -y arm
    y_out = (y_in[0] + p["arm_thickness"], y_in[1] - p["arm_thickness"])
    return {"lug_r": lug_r, "x0": px - lug_r, "x1": px + FOOT_AHEAD,
            "y_in": y_in, "y_out": y_out, "base_top": p["base_thickness"]}


def _base_outline(g):
    feet = [(g["x0"], g["y_out"][1]), (g["x1"], g["y_out"][1]),
            (g["x1"], g["y_out"][0]), (g["x0"], g["y_out"][0])]
    return _face_xy(_hull(list(BOLT_CENTRES) + feet)).makeOffset2D(BOSS_D / 2)


def _arm(g, y_a, y_b):
    """One clevis arm between y_a < y_b: a lug hulled onto a foot on the base."""
    px, _, pz = PIN
    r, x1, zb = g["lug_r"], g["x1"], g["base_top"]
    # Tangent from the foot's +x end (x1, zb) to the lug circle, upper side.
    dx, dz = x1 - px, zb - pz
    d = math.hypot(dx, dz)
    ang = math.atan2(dz, dx) + math.acos(r / d)
    tx, tz = px + r * math.cos(ang), pz + r * math.sin(ang)
    outline = [(g["x0"], 0.0), (x1, 0.0), (x1, zb), (tx, tz), (px, pz), (g["x0"], pz)]
    face = Part.Face(Part.makePolygon([Vector(x, y_a, z) for x, z in outline + outline[:1]]))
    plate = face.extrude(Vector(0, y_b - y_a, 0))
    lug = Part.makeCylinder(r, y_b - y_a, Vector(px, y_a, pz), Vector(0, 1, 0))
    return plate.fuse(lug)


def _arm_root_edges(shape, g):
    """Edges where an arm meets the base top: every edge in the plane z = base_top
    that lies on the boundary of an arm footprint."""
    zb, x0, x1 = g["base_top"], g["x0"], g["x1"]
    bands = [(g["y_in"][0], g["y_out"][0]), (g["y_out"][1], g["y_in"][1])]
    edges = []
    for e in shape.Edges:
        b = e.BoundBox
        if abs(b.ZMin - zb) > TOL or abs(b.ZMax - zb) > TOL:
            continue
        for ylo, yhi in bands:
            inside = (x0 - TOL <= b.XMin and b.XMax <= x1 + TOL
                      and ylo - TOL <= b.YMin and b.YMax <= yhi + TOL)
            on_boundary = (abs(b.YMin - b.YMax) < TOL and min(abs(b.YMin - ylo), abs(b.YMin - yhi)) < TOL
                           or abs(b.XMin - b.XMax) < TOL and min(abs(b.XMin - x0), abs(b.XMin - x1)) < TOL)
            if inside and on_boundary:
                edges.append(e)
    return edges


def _pockets(g, outline, depth):
    """Underside pockets in the two base wings, between the arms and the bolt rows."""
    inner = outline.makeOffset2D(-POCKET_WALL)
    big = 1000.0
    wings = [Part.makePlane(2 * big, big - (g["y_out"][0] + POCKET_CLEAR_ARM),
                            Vector(-big, g["y_out"][0] + POCKET_CLEAR_ARM, 0)),
             Part.makePlane(2 * big, big + (g["y_out"][1] - POCKET_CLEAR_ARM),
                            Vector(-big, -big, 0))]
    discs = [Part.Face(Part.Wire(Part.makeCircle(POCKET_CLEAR_BOLT, Vector(x, y, 0))))
             for x, y in BOLT_CENTRES]
    solids = []
    for wing in wings:
        region = inner.common(wing).cut(discs)
        for face in region.Faces:
            # Round the pocket's inside corners so a 6 mm endmill reaches them.
            rounded = face.makeOffset2D(-POCKET_CORNER_R).makeOffset2D(POCKET_CORNER_R)
            solids.append(rounded.translated(Vector(0, 0, -1)).extrude(Vector(0, 0, depth + 1)))
    return solids


def build_shape(p):
    """The ge_bracket solid for a parameter dict (mm)."""
    g = layout(p)
    outline = _base_outline(g)
    solid = outline.extrude(Vector(0, 0, g["base_top"]))
    # The bosses are the outline's lobes round each bolt, flush with the base
    # top: a raised boss left a sharp root corner that was singular under LC1.
    parts = [_arm(g, g["y_in"][0], g["y_out"][0]), _arm(g, g["y_out"][1], g["y_in"][1])]
    solid = solid.fuse(parts).removeSplitter()
    solid = solid.makeFillet(p["arm_root_fillet"], _arm_root_edges(solid, g))

    px, py, pz = PIN
    span = 400.0
    cuts = [Part.makeCylinder(PIN_D / 2, span, Vector(px, py - span / 2, pz), Vector(0, 1, 0))]
    cuts += [Part.makeCylinder(BOLT_HOLE_D / 2, g["base_top"] + 2, Vector(x, y, -1))
             for x, y in BOLT_CENTRES]
    cuts.append(Part.makeCylinder(p["centre_hole_diameter"] / 2, g["base_top"] + 2,
                                  Vector(CENTRE_HOLE_X, py, -1)))
    cuts += _pockets(g, outline, p["base_pocket_depth"])
    solid = solid.cut(cuts).removeSplitter()
    return Part.Solid(solid.Solids[0]) if len(solid.Solids) == 1 else solid


class GeBracket:
    """FreeCAD Python feature: rebuilds the solid from its length properties."""

    def __init__(self, obj):
        for name, prop in PROPERTY.items():
            obj.addProperty("App::PropertyLength", prop, "ge_bracket", PARAMS[name]["kind"])
            setattr(obj, prop, PARAMS[name]["baseline"])
        obj.Proxy = self

    def execute(self, obj):
        obj.Shape = build_shape(params_of(obj))

    def dumps(self):
        return None

    def loads(self, state):
        return None


def params_of(obj):
    return {name: float(getattr(obj, prop).getValueAs("mm")) for name, prop in PROPERTY.items()}


def make_document(name="ge_bracket"):
    """A new document: a `Params` spreadsheet and the bound GeBracket feature."""
    doc = FreeCAD.newDocument(name)
    sheet = doc.addObject("Spreadsheet::Sheet", "Params")
    sheet.set("A1", "parameter")
    sheet.set("B1", "value_mm")
    sheet.set("C1", "kind")
    sheet.set("D1", "min")
    sheet.set("E1", "max")
    sheet.set("F1", "step")
    for row, (name, rec) in enumerate(PARAMS.items(), start=2):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", f"={rec['baseline']}mm")
        sheet.setAlias(f"B{row}", name)
        sheet.set(f"C{row}", rec["kind"])
        for col, key in zip("DEF", ("min", "max", "step")):
            sheet.set(f"{col}{row}", str(rec[key]))
    doc.recompute()
    obj = doc.addObject("Part::FeaturePython", "GeBracket")
    GeBracket(obj)
    for name, prop in PROPERTY.items():
        obj.setExpression(prop, f"Params.{name}")
    doc.recompute()
    return doc


def set_params(doc, values):
    """Set spreadsheet cells by alias and recompute: the agent's only edit path."""
    sheet = doc.getObject("Params")
    for name, value in values.items():
        if name not in PARAMS:
            raise KeyError(f"not a ge_bracket parameter: {name}")
        sheet.set(sheet.getCellFromAlias(name), f"={value}mm")
    doc.recompute()
    return doc.getObject("GeBracket")


# ---------------------------------------------------------------------------
# Geometric face predicates (D-04). Each takes (face, g) and says whether the
# face is the named one; `g` is layout() of the current parameters.


def _cyl(face, radius, axis):
    s = face.Surface
    return (isinstance(s, Part.Cylinder) and abs(s.Radius - radius) < TOL
            and abs(abs(s.Axis.dot(Vector(*axis))) - 1) < 1e-6)


def _plane(face, normal, at, coord):
    s = face.Surface
    if not isinstance(s, Part.Plane):
        return False
    n = face.normalAt(*face.ParameterRange[:3:2])
    c = {"x": face.CenterOfMass.x, "y": face.CenterOfMass.y, "z": face.CenterOfMass.z}[coord]
    return n.dot(Vector(*normal)) > 1 - 1e-6 and abs(c - at) < TOL


def _axis_through(face, x, y):
    loc = face.Surface.Center
    return math.hypot(loc.x - x, loc.y - y) < 0.01


def _bolt_hole(i):
    x, y = BOLT_CENTRES[i]
    return lambda f, g: _cyl(f, BOLT_HOLE_D / 2, (0, 0, 1)) and _axis_through(f, x, y)


def _boss_side(i):
    x, y = BOLT_CENTRES[i]
    return lambda f, g: _cyl(f, BOSS_D / 2, (0, 0, 1)) and _axis_through(f, x, y)


def _pin_bore(side):
    def pred(f, g):
        s = f.Surface
        return (_cyl(f, PIN_D / 2, (0, 1, 0))
                and math.hypot(s.Center.x - PIN[0], s.Center.z - PIN[2]) < 0.01
                and (f.CenterOfMass.y - PIN[1]) * side > 0)
    return pred


def _lug(side):
    def pred(f, g):
        s = f.Surface
        return (_cyl(f, g["lug_r"], (0, 1, 0))
                and math.hypot(s.Center.x - PIN[0], s.Center.z - PIN[2]) < 0.01
                and (f.CenterOfMass.y - PIN[1]) * side > 0)
    return pred


def _arm_face(side, which):
    k = 0 if side > 0 else 1

    def pred(f, g):
        y = g["y_out" if which == "outer" else "y_in"][k]
        normal = (0, side, 0) if which == "outer" else (0, -side, 0)
        return _plane(f, normal, y, "y")
    return pred


def _arm_end_x0(side):
    def pred(f, g):
        return (_plane(f, (-1, 0, 0), g["x0"], "x")
                and (f.CenterOfMass.y - PIN[1]) * side > CLEVIS_GAP / 2)
    return pred


def _arm_slope(side):
    def pred(f, g):
        s = f.Surface
        if not isinstance(s, Part.Plane):
            return False
        n = f.normalAt(*f.ParameterRange[:3:2])
        return (abs(n.y) < 1e-6 and n.x > 0.1 and n.z > 0.1
                and (f.CenterOfMass.y - PIN[1]) * side > CLEVIS_GAP / 2)
    return pred


def _fillet(side, where):
    """One arm-root fillet face: non-planar, non-cylinder-axis-z, touching the base
    top, beside one edge of one arm's footprint."""
    k = 0 if side > 0 else 1

    def pred(f, g):
        if isinstance(f.Surface, Part.Plane):
            return False
        b = f.BoundBox
        r_max = PARAMS["arm_root_fillet"]["max"] + TOL
        if abs(b.ZMin - g["base_top"]) > TOL or b.ZMax > g["base_top"] + r_max:
            return False
        c = f.CenterOfMass
        y_in, y_out = g["y_in"][k], g["y_out"][k]
        lo, hi = min(y_in, y_out), max(y_in, y_out)
        if where in ("inner", "outer"):
            y = y_in if where == "inner" else y_out
            beside = (c.y - y) * (1 if (y == hi) else -1) > 0
            return beside and abs(c.y - y) < r_max and g["x0"] < c.x < g["x1"] and b.XLength > 10
        x = g["x0"] if where == "x0" else g["x1"]
        return (abs(c.x - x) < r_max and lo - TOL < c.y < hi + TOL and b.YLength > 1
                and (c.x - x) * (-1 if where == "x0" else 1) > 0)
    return pred


def _base_top(f, g):
    return _plane(f, (0, 0, 1), g["base_top"], "z") and f.Area > 5000


def _base_bottom(f, g):
    return _plane(f, (0, 0, -1), 0.0, "z")


def _centre_hole(f, g):
    return (isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Axis.z) > 1 - 1e-6
            and _axis_through(f, CENTRE_HOLE_X, PIN[1]))


def _pocket_floor(side):
    def pred(f, g):
        return (isinstance(f.Surface, Part.Plane) and f.normalAt(*f.ParameterRange[:3:2]).z < -1 + 1e-6
                and 0.5 < f.CenterOfMass.z < g["base_top"]
                and (f.CenterOfMass.y - PIN[1]) * side > 0)
    return pred


def _base_side(f, g):
    """Set rule: the base outline's vertical side faces."""
    b = f.BoundBox
    vertical = abs(f.normalAt(*f.ParameterRange[:3:2]).z) < 1e-6
    return vertical and b.ZMin < TOL and abs(b.ZMax - g["base_top"]) < TOL


def _pocket_wall(f, g):
    """Set rule: the vertical walls of the underside pockets."""
    b = f.BoundBox
    vertical = abs(f.normalAt(*f.ParameterRange[:3:2]).z) < 1e-6
    return vertical and b.ZMin < TOL and b.ZMax < g["base_top"] - TOL


# Single-face predicates: each must match exactly one face (REQ-OPT-008).
PREDICATES = {
    **{f"bolt_hole_{i + 2}": _bolt_hole(i) for i in range(4)},
    **{f"boss_side_{i + 2}": _boss_side(i) for i in range(4)},
    "pin_bore_pos_y": _pin_bore(1), "pin_bore_neg_y": _pin_bore(-1),
    "lug_pos_y": _lug(1), "lug_neg_y": _lug(-1),
    "arm_outer_pos_y": _arm_face(1, "outer"), "arm_outer_neg_y": _arm_face(-1, "outer"),
    "arm_inner_pos_y": _arm_face(1, "inner"), "arm_inner_neg_y": _arm_face(-1, "inner"),
    "arm_end_pos_y": _arm_end_x0(1), "arm_end_neg_y": _arm_end_x0(-1),
    "arm_slope_pos_y": _arm_slope(1), "arm_slope_neg_y": _arm_slope(-1),
    **{f"fillet_{w}_{s}": _fillet(1 if s == "pos_y" else -1, w)
       for s in ("pos_y", "neg_y") for w in ("inner", "outer", "x0", "x1")},
    "base_top": _base_top, "base_bottom": _base_bottom, "centre_hole": _centre_hole,
    "pocket_floor_pos_y": _pocket_floor(1), "pocket_floor_neg_y": _pocket_floor(-1),
}

def _fillet_corner(f, g):
    """Set rule: blends OCC adds where two arm-root fillets meet at an arm corner.
    They appear only at some radii (at 8 mm, not at 5 mm), and a blend at an
    arm's -x corner rises about 1.7 radii up the arm end."""
    b = f.BoundBox
    r_max = PARAMS["arm_root_fillet"]["max"] + TOL
    return (not isinstance(f.Surface, Part.Plane) and abs(b.ZMin - g["base_top"]) < TOL
            and b.ZMax <= g["base_top"] + 3 * r_max)


# Set rules: whole-region membership, any number of faces, applied only to faces
# no single-face predicate claimed. They only label regions; no constraint or
# CAM operation selects faces with them.
SET_RULES = {"base_side": _base_side, "pocket_wall": _pocket_wall, "fillet_corner": _fillet_corner}

# What uses each predicate. Constraints (M2.2 settles the pin-load model).
CONSTRAINTS = {
    "fixed_bolts": [f"bolt_hole_{i}" for i in (2, 3, 4, 5)],
    "pin_load": ["pin_bore_pos_y", "pin_bore_neg_y"],
}
# D-06 named regions, as Mesh Group face sets. `bulk` is every face in none.
REGIONS = {
    "pin_bore": ["pin_bore_pos_y", "pin_bore_neg_y"],
    "clevis_arm": [f"{n}_{s}" for s in ("pos_y", "neg_y")
                   for n in ("lug", "arm_outer", "arm_inner", "arm_end", "arm_slope")],
    "arm_root_fillet": [f"fillet_{w}_{s}" for s in ("pos_y", "neg_y")
                        for w in ("inner", "outer", "x0", "x1")] + ["fillet_corner"],
    "base_plate": ["base_top", "base_bottom", "centre_hole", "pocket_floor_pos_y",
                   "pocket_floor_neg_y", "base_side", "pocket_wall"],
    "bolt_boss": [f"{n}_{i}" for i in (2, 3, 4, 5) for n in ("bolt_hole", "boss_side")],
}
# D-11 cnc_3axis: setups, and the operations each runs on predicate-selected faces.
CAM = {
    "top_+z": {"Profile": ["base_bottom", "centre_hole"] + [f"bolt_hole_{i}" for i in (2, 3, 4, 5)],
               "Adaptive": ["base_top"]},
    "bottom_-z": {"Adaptive": ["pocket_floor_pos_y", "pocket_floor_neg_y"]},
    "side_+y": {"Profile": ["lug_pos_y", "arm_slope_pos_y", "arm_end_pos_y", "pin_bore_pos_y"],
                "Adaptive": ["arm_outer_pos_y"]},
    "side_-y": {"Profile": ["lug_neg_y", "arm_slope_neg_y", "arm_end_neg_y", "pin_bore_neg_y"],
                "Adaptive": ["arm_outer_neg_y"]},
    # The long arm-root fillets run along x, so only a tool along x cuts them:
    # from each end, halfway along the arm foot.
    **{end: {"Profile": ["fillet_inner_pos_y", "fillet_outer_pos_y",
                         "fillet_inner_neg_y", "fillet_outer_neg_y"],
             "Adaptive": ["arm_inner_pos_y", "arm_inner_neg_y"]} for end in ("end_-x", "end_+x")},
}


def match(shape, p):
    """Face indices each predicate and set rule matches on `shape` (1-based, FaceN)."""
    g = layout(p)
    m = {name: [i + 1 for i, f in enumerate(shape.Faces) if pred(f, g)]
         for name, pred in PREDICATES.items()}
    claimed = {i for v in m.values() for i in v}
    m.update({name: [i + 1 for i, f in enumerate(shape.Faces) if i + 1 not in claimed and pred(f, g)]
              for name, pred in SET_RULES.items()})
    return m


def region_of_faces(shape, p):
    """D-06 label for every face, and the faces with no label or with two."""
    m = match(shape, p)
    labels = {}
    for region, names in REGIONS.items():
        for name in names:
            for i in m[name]:
                labels.setdefault(i, set()).add(region)
    unlabelled = [i for i in range(1, len(shape.Faces) + 1) if i not in labels]
    overlap = {i: sorted(r) for i, r in labels.items() if len(r) > 1}
    return labels, unlabelled, overlap

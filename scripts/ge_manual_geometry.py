"""M2A.1: check the selected GE geometry and write its manual-analysis working copy.

Reads the frozen source data/simjeb/Iteration1.stp (never writes it) after
checking its SHA-256, then records

- STEP header identity, declared units and B-rep validity;
- solid/shell counts, bounding box, volume and surface area;
- the four bolt holes, their nut-seat faces and the largest nut annulus
  each seat can carry, against the GE brief's interface dimensions;
- both clevis lug bores, their common axis, lug thicknesses and pin reference
  point (pin centreline x clevis midplane);
- a sampled minimum-wall estimate (inward ray cast on a fine tessellation);
- mirror symmetry about the clevis midplane;
- the rigid transform from the file's tilted native frame to the SimJEB load
  frame (+z up, out = -x), fitted to the SimJEB design-148 deck's bolt RBE2
  centres and checked against its independent pin load node.

Writes out/ge_manual_geometry/geometry-check.json, annotated views, and the
working copy data/ge_manual/Iteration1_manual.FCStd, built from a deck-frame
STEP data/ge_manual/Iteration1_deck_frame.step (both gitignored: the CAD is
licensed non-commercial by GrabCAD), then reopens the working copy to check it.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_manual_geometry.py
"""

import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import FreeCAD  # noqa: E402
import Part  # noqa: E402

SOURCE = ROOT / "data" / "simjeb" / "Iteration1.stp"
SOURCE_SHA256 = "a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e"
DECK = ROOT / "data" / "simjeb" / "148.fem"
WORKING = ROOT / "data" / "ge_manual" / "Iteration1_manual.FCStd"
DECK_STEP = ROOT / "data" / "ge_manual" / "Iteration1_deck_frame.step"
OUT = ROOT / "out" / "ge_manual_geometry"

# GE brief section 2 (docs/ge-jet-engine-bracket.md), inches converted to mm.
PIN_D = 19.05
BOLT_D = 9.525
NUT_ID = 10.287
NUT_OD = 14.173
MIN_WALL = 1.27

# SimJEB design 148 deck: RBE2 bolt spider centres and the RBE3 pin load node.
BOLT_NODES = [129261, 129262, 129263, 129264]
PIN_NODE = 129265


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vec(v):
    return np.array([v.x, v.y, v.z])


def step_header(path):
    text = path.read_text(errors="replace")
    head = text[: text.index("ENDSEC;")]
    units = re.findall(r"LENGTH_UNIT\(\)NAMED_UNIT\(\*\)SI_UNIT\(([^)]*)\)", text)
    uncertainty = re.search(r"LENGTH_MEASURE\(([^)]*)\)[^;]*distance_accuracy_value", text)
    return {
        "file_description": re.search(r"FILE_DESCRIPTION\(\('([^']*)'", head).group(1),
        "file_name": re.search(r"FILE_NAME\('([^']*)'", head).group(1),
        "timestamp": re.search(r"FILE_NAME\('[^']*','([^']*)'", head).group(1),
        "preprocessor": re.findall(r"'([^']*)'", head.split("FILE_NAME(", 1)[1])[-3:],
        "schema": re.search(r"FILE_SCHEMA\(\('([^']*)'", head).group(1),
        "product": re.search(r"PRODUCT\('([^']*)'", text).group(1),
        "length_unit": units,
        "distance_accuracy_mm": float(uncertainty.group(1)) if uncertainty else None,
    }


def deck_grids(path, ids):
    """Read small-field GRID cards; Nastran shorthand like 4.2367-2 means 4.2367e-2."""
    def num(s):
        s = s.strip()
        return float(re.sub(r"(?<=[0-9.])([+-])(\d+)$", r"e\1\2", s))

    found = {}
    with path.open() as f:
        for line in f:
            if line.startswith("GRID ") and int(line[8:16]) in ids:
                found[int(line[8:16])] = [num(line[24:32]), num(line[32:40]), num(line[40:48])]
    return found


def cylinders(shape, lo, hi):
    """Group cylindrical faces with radius in (lo, hi) by common axis line."""
    groups = []
    for i, f in enumerate(shape.Faces):
        s = f.Surface
        if not isinstance(s, Part.Cylinder) or not lo < s.Radius < hi:
            continue
        a, c = vec(s.Axis), vec(s.Center)
        for g in groups:
            d = c - g["centre"]
            if abs(abs(np.dot(a, g["axis"])) - 1) < 1e-6 and np.linalg.norm(d - np.dot(d, g["axis"]) * g["axis"]) < 1e-3 and abs(g["radius"] - s.Radius) < 1e-4:
                g["faces"].append(i)
                break
        else:
            groups.append({"axis": a / np.linalg.norm(a), "centre": c, "radius": s.Radius, "faces": [i]})
    for g in groups:
        ts = [np.dot(vec(v.Point) - g["centre"], g["axis"]) for i in g["faces"] for v in shape.Faces[i].Vertexes]
        g["t"] = (min(ts), max(ts))
    return groups


def seat_faces(shape, hole, up, bottom):
    """Planar faces normal to the hole axis that meet the hole's circular edges.

    Heights are measured along the base normal `up` from the base bottom plane.
    """
    out = []
    for i, f in enumerate(shape.Faces):
        if not isinstance(f.Surface, Part.Plane):
            continue
        n = vec(f.Surface.Axis)
        if abs(abs(np.dot(n, hole["axis"])) - 1) > 1e-6:
            continue
        t = np.dot(vec(f.Vertexes[0].Point) - hole["centre"], hole["axis"])
        if min(abs(t - hole["t"][0]), abs(t - hole["t"][1])) > 1e-3:
            continue
        # Radial distance from the hole axis to every non-hole boundary edge.
        radii, touches_hole = [], False
        for e in f.Edges:
            pts = np.array([vec(p) for p in e.discretize(200)])
            d = pts - hole["centre"]
            r = np.linalg.norm(d - np.outer(d @ hole["axis"], hole["axis"]), axis=1)
            if np.ptp(r) < 1e-3 and abs(r.mean() - hole["radius"]) < 1e-3:
                touches_hole = True
            else:
                radii.append(r.min())
        if touches_hole:
            out.append({"face": i, "height_above_base_bottom_mm": round(float(np.dot(vec(f.Vertexes[0].Point), up) - bottom), 4),
                        "area_mm2": round(f.Area, 2),
                        "max_concentric_annulus_od_mm": round(2 * min(radii), 3) if radii else None})
    return out


def bop_check(shape):
    """Count the BOP checker's findings by type; it raises with a text report."""
    try:
        shape.check(True)
        return {}
    except Exception as exc:  # noqa: BLE001
        counts = {}
        for line in str(exc).splitlines():
            if line.startswith("Error in "):
                counts[line] = counts.get(line, 0) + 1
        return counts


def kabsch_2d(src, dst):
    """Proper rotation + translation (no reflection) taking src (n,2) onto dst."""
    sc, dc = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((src - sc).T @ (dst - dc))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    r = vt.T @ np.diag([1, d]) @ u.T
    return r, dc - r @ sc


def ray_thickness(shape, deflection):
    """Local wall thickness: inward ray from each triangle centroid to the next surface hit."""
    import vtk
    import pyvista as pv

    verts, tris = shape.tessellate(deflection)
    mesh = pv.PolyData(np.array([[v.x, v.y, v.z] for v in verts]), np.c_[np.full(len(tris), 3), np.array(tris)].ravel())
    mesh = mesh.compute_normals(cell_normals=True, point_normals=False, auto_orient_normals=True)
    tree = vtk.vtkOBBTree()
    tree.SetDataSet(mesh)
    tree.BuildLocator()
    centres, normals = mesh.cell_centers().points, mesh.cell_data["Normals"]
    hits, found = vtk.vtkPoints(), []
    for c, n in zip(centres, normals):
        start = c - 1e-4 * n
        tree.IntersectWithLine(start, c - 200.0 * n, hits, None)
        ds = [np.linalg.norm(np.array(hits.GetPoint(k)) - c) for k in range(hits.GetNumberOfPoints())]
        ds = [d for d in ds if d > 1e-3]
        found.append(min(ds) if ds else np.nan)
    return mesh, centres, np.array(found)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    WORKING.parent.mkdir(parents=True, exist_ok=True)
    actual = sha256(SOURCE)
    if actual != SOURCE_SHA256:
        sys.exit(f"SOURCE CHECKSUM MISMATCH: {SOURCE}\n  expected {SOURCE_SHA256}\n  actual   {actual}")
    record = {"source": str(SOURCE.relative_to(ROOT)), "sha256": actual, "bytes": SOURCE.stat().st_size,
              "freecad_version": ".".join(FreeCAD.Version()[:3]), "step_header": step_header(SOURCE)}

    shape = Part.read(str(SOURCE))
    bb = shape.BoundBox
    record["brep"] = {
        "valid": shape.isValid(), "solids": len(shape.Solids), "shells": len(shape.Shells),
        "faces": len(shape.Faces), "edges": len(shape.Edges), "closed_shell": all(s.isClosed() for s in shape.Shells),
        "volume_mm3": round(shape.Volume, 3), "area_mm2": round(shape.Area, 3),
        "centre_of_mass_native": [round(x, 4) for x in vec(shape.Solids[0].CenterOfMass)],
        "bbox_native": [round(x, 4) for x in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)],
    }
    record["brep"]["bop_check"] = bop_check(shape)
    record["brep"]["max_tolerance_mm"] = {k: shape.getTolerance(1, t) for k, t in (("vertex", Part.Vertex), ("edge", Part.Edge), ("face", Part.Face))}

    # Interfaces: bolt holes near the 10.3 mm clearance size, pin bores near 19.05 mm.
    bolts = cylinders(shape, 4.5, 6.0)
    pins = cylinders(shape, 9.0, 10.0)
    if len(bolts) != 4 or len(pins) != 1:
        sys.exit(f"expected 4 bolt axes and 1 pin axis, found {len(bolts)} and {len(pins)}")
    pin = pins[0]
    # Base normal: bolt axis, oriented from the base toward the pin.
    z = bolts[0]["axis"].copy()
    if np.dot(pin["centre"] - bolts[0]["centre"], z) < 0:
        z = -z
    for b in bolts:
        b["axis"] = z if np.dot(b["axis"], z) > 0 else -z
        b["t"] = (min(np.dot(vec(v.Point) - b["centre"], b["axis"]) for i in b["faces"] for v in shape.Faces[i].Vertexes),
                  max(np.dot(vec(v.Point) - b["centre"], b["axis"]) for i in b["faces"] for v in shape.Faces[i].Vertexes))
    # Individual lug bores: split the pin faces into contiguous axial spans.
    spans = sorted({(round(min(np.dot(vec(v.Point) - pin["centre"], pin["axis"]) for v in shape.Faces[i].Vertexes), 4),
                     round(max(np.dot(vec(v.Point) - pin["centre"], pin["axis"]) for v in shape.Faces[i].Vertexes), 4)) for i in pin["faces"]})
    mid_t = (spans[0][0] + spans[-1][1]) / 2
    pin_ref = pin["centre"] + mid_t * pin["axis"]

    # Native base frame: origin on the base bottom plane below bolt 0, z up, y along the pin axis.
    y = pin["axis"] - np.dot(pin["axis"], z) * z
    y /= np.linalg.norm(y)
    x = np.cross(y, z)
    bottom = min(b["t"][0] + np.dot(b["centre"], z) for b in bolts)
    origin = bolts[0]["centre"] + (bottom - np.dot(bolts[0]["centre"], z)) * z
    local = np.stack([x, y, z])
    bolt_xy = np.array([local @ (b["centre"] - origin) for b in bolts])[:, :2]
    pin_local = local @ (pin_ref - origin)

    # Fit to the SimJEB deck frame using only the bolt centres (best of all orderings).
    grids = deck_grids(DECK, set(BOLT_NODES + [PIN_NODE]))
    deck_bolts = np.array([grids[n] for n in BOLT_NODES])
    best = None
    for perm in itertools.permutations(range(4)):
        r2, t2 = kabsch_2d(bolt_xy[list(perm)], deck_bolts[:, :2])
        res = np.linalg.norm((bolt_xy[list(perm)] @ r2.T + t2) - deck_bolts[:, :2], axis=1)
        if best is None or res.max() < best[0].max():
            best = (res, perm, r2, t2)
    res, perm, r2, t2 = best
    # Deck frame z = 0 on the base bottom plane: 148.stp's base bottom is at z = 0.
    rot = np.eye(3)
    rot[:2, :2] = r2
    to_deck = rot @ local                     # native -> deck rotation
    shift = np.r_[t2, 0.0] - to_deck @ origin  # native -> deck translation
    pin_deck = to_deck @ pin_ref + shift
    pin_axis_deck = to_deck @ pin["axis"]
    com_deck = to_deck @ vec(shape.Solids[0].CenterOfMass) + shift
    record["frame"] = {
        "native": "STEP file axes as exported; base plane tilted about native +x, pin axis along native x",
        "base_normal_native": z.round(9).tolist(),
        "pin_axis_native": pin["axis"].round(9).tolist(),
        "tilt_of_base_normal_from_native_z_deg": round(float(np.degrees(np.arccos(abs(z[2])))), 4),
        "deck": "SimJEB 148.fem frame: +z vertical up (base normal), LC2 'out' = -x, z = 0 on base bottom plane",
        "native_to_deck_rotation_rows": to_deck.round(12).tolist(),
        "native_to_deck_translation_mm": shift.round(6).tolist(),
        "fit": "2-D rigid fit of the 4 bolt axes to 148.fem RBE2 centres; the pin node is an independent check",
        "bolt_fit_residual_mm": res.round(3).tolist(),
        "deck_pin_node": grids[PIN_NODE],
        "pin_ref_in_deck_frame": pin_deck.round(3).tolist(),
        "pin_ref_vs_deck_node_mm": (pin_deck - np.array(grids[PIN_NODE])).round(3).tolist(),
        "pin_axis_in_deck_frame": pin_axis_deck.round(6).tolist(),
        "centre_of_mass_deck": com_deck.round(3).tolist(),
        "out_minus_x_points_from_body_to_pin": bool(pin_deck[0] < com_deck[0]),
    }

    # Bolt holes and nut seats, reported in the deck frame and ordered by deck node.
    order = {perm[k]: k for k in range(4)}
    record["bolts"] = []
    for i, b in enumerate(bolts):
        k = order[i]
        axis_pt = to_deck @ b["centre"] + shift
        seats = seat_faces(shape, b, z, bottom)
        top = max(seats, key=lambda s: s["height_above_base_bottom_mm"]) if seats else None
        record["bolts"].append({
            "label": f"B{k + 1}", "deck_rbe2_node": BOLT_NODES[k], "deck_rbe2_centre": grids[BOLT_NODES[k]],
            "axis_xy_deck": (axis_pt - np.dot(axis_pt, [0, 0, 1]) * np.array([0, 0, 1]))[:2].round(3).tolist(),
            "hole_d_mm": round(2 * b["radius"], 4), "hole_length_mm": round(b["t"][1] - b["t"][0], 4),
            "bolt_clearance_diametral_mm": round(2 * b["radius"] - BOLT_D, 4),
            "hole_d_minus_nut_face_max_id_mm": round(2 * b["radius"] - NUT_ID, 4),
            "seat_faces": seats,
            "nut_seat": top and {"face": top["face"], "height_above_base_bottom_mm": top["height_above_base_bottom_mm"],
                                 "max_annulus_od_mm": top["max_concentric_annulus_od_mm"],
                                 "carries_ge_nut_annulus": bool(top["max_concentric_annulus_od_mm"] and top["max_concentric_annulus_od_mm"] >= NUT_OD)},
            "brep_faces": b["faces"],
        })
    record["bolts"].sort(key=lambda r: r["label"])
    xy = np.array([r["axis_xy_deck"] for r in record["bolts"]])
    record["bolt_pattern_distances_mm"] = {f"B{a + 1}-B{b + 1}": round(float(np.linalg.norm(xy[a] - xy[b])), 3)
                                          for a, b in itertools.combinations(range(4), 2)}

    lugs = []
    for lo, hi in spans:
        c = to_deck @ (pin["centre"] + (lo + hi) / 2 * pin["axis"]) + shift
        lugs.append({"bore_d_mm": round(2 * pin["radius"], 4), "bore_length_mm": round(hi - lo, 4),
                     "centre_deck": c.round(3).tolist()})
    record["pin"] = {
        "bores": lugs, "bore_faces": pin["faces"],
        "bore_d_mm": round(2 * pin["radius"], 4), "pin_d_mm": PIN_D,
        "diametral_clearance_mm": round(2 * pin["radius"] - PIN_D, 4),
        "clevis_gap_mm": round(spans[-1][0] - spans[0][1], 4),
        "clevis_outer_span_mm": round(spans[-1][1] - spans[0][0], 4),
        "pin_ref_height_above_base_bottom_mm": round(float(pin_local[2]), 4),
    }

    # Mirror symmetry about the clevis midplane (normal = pin axis): signed distance
    # from the mirrored surface to the original. Booleans fail on this file's BOP flags.
    import pyvista as pv
    verts, tris = shape.tessellate(0.1)
    surf = pv.PolyData(np.array([[v.x, v.y, v.z] for v in verts]), np.c_[np.full(len(tris), 3), np.array(tris)].ravel())
    mirror = surf.copy()
    d = mirror.points - pin_ref
    mirror.points = mirror.points - 2 * np.outer(d @ pin["axis"], pin["axis"])
    dist = np.abs(mirror.compute_implicit_distance(surf)["implicit_distance"])
    far = mirror.points[dist > 0.1]
    record["symmetry"] = {"plane": "clevis midplane through pin reference, normal = pin axis",
                          "max_surface_deviation_mm": round(float(dist.max()), 3),
                          "fraction_of_mirrored_vertices_off_by_more_than_0.1mm": round(float((dist > 0.1).mean()), 4),
                          "deviating_region_bbox_deck": (np.r_[(far @ to_deck.T + shift).min(0), (far @ to_deck.T + shift).max(0)].round(1).tolist() if len(far) else None)}

    # Minimum wall: sampled estimate, not an exact B-rep distance.
    mesh, centres, thick = ray_thickness(shape, 0.05)
    ok = ~np.isnan(thick)
    worst = np.argsort(np.where(ok, thick, np.inf))[:10]
    record["wall_thickness_sampled"] = {
        "method": "inward ray from each triangle centroid of a 0.05 mm-deflection tessellation to the next surface",
        "triangles": int(len(thick)), "rays_without_hit": int((~ok).sum()),
        "min_mm": round(float(np.nanmin(thick)), 3),
        "p01_mm": round(float(np.nanpercentile(thick, 1)), 3),
        "count_below_ge_min_feature": int((thick[ok] < MIN_WALL).sum()),
        "ge_min_feature_mm": MIN_WALL,
        "thinnest_locations_deck": [(to_deck @ centres[i] + shift).round(2).tolist() + [round(float(thick[i]), 3)] for i in worst],
    }

    # Working copy: native solid with a Placement into the deck frame; source file untouched.
    doc = FreeCAD.newDocument("Iteration1_manual")
    part = doc.addObject("Part::Feature", "Bracket")
    m = FreeCAD.Matrix(*(float(v) for v in np.vstack([np.c_[to_deck, shift], [0, 0, 0, 1]]).ravel()))
    # Bake the transform into the geometry with a STEP round trip. Left as a
    # Placement, BRepCheck flags five located chamfer cones "Unorientable"
    # (the unlocated source passes), and FEM would inherit that located shape.
    located = shape.copy()
    located.Placement = FreeCAD.Placement(m)
    bad = [i for i, f in enumerate(located.Faces) if not f.isValid()]
    located.exportStep(str(DECK_STEP))
    working = Part.read(str(DECK_STEP))
    record["deck_frame_step"] = {
        "path": str(DECK_STEP.relative_to(ROOT)), "sha256": sha256(DECK_STEP),
        "located_source_invalid_faces": [{"face": i, "surface": located.Faces[i].Surface.__class__.__name__,
                                          "area_mm2": round(located.Faces[i].Area, 3),
                                          "centre_deck": vec(located.Faces[i].CenterOfMass).round(2).tolist()} for i in bad],
        "roundtrip_valid": working.isValid(), "roundtrip_faces": len(working.Faces),
        "roundtrip_volume_change_mm3": round(working.Volume - shape.Volume, 4),
    }
    part.Shape = working
    part.Label = "Bracket (Iteration1.stp, SimJEB deck frame)"
    ref = doc.addObject("Part::Vertex", "PinReference")
    ref.X, ref.Y, ref.Z = (float(v) for v in pin_deck)
    ref.Label = "Pin reference (pin centreline x clevis midplane)"
    doc.recompute()
    WORKING.unlink(missing_ok=True)  # no .FCBak backup of a regenerated file
    doc.saveAs(str(WORKING))
    FreeCAD.closeDocument(doc.Name)

    doc = FreeCAD.openDocument(str(WORKING))
    s = doc.getObject("Bracket").Shape
    record["working_copy"] = {
        "path": str(WORKING.relative_to(ROOT)), "sha256": sha256(WORKING),
        "reopened": True, "valid": s.isValid(), "solids": len(s.Solids),
        "volume_mm3": round(s.Volume, 3),
        "volume_matches_source_within_1e-6": abs(s.Volume - shape.Volume) < 1e-6 * shape.Volume,
        "placement_is_identity": s.Placement.isIdentity(),
        "max_tolerance_mm": {k: s.getTolerance(1, t) for k, t in (("vertex", Part.Vertex), ("edge", Part.Edge), ("face", Part.Face))},
        "bop_check": bop_check(s),
        "bbox_deck": [round(v, 3) for v in (s.BoundBox.XMin, s.BoundBox.YMin, s.BoundBox.ZMin, s.BoundBox.XMax, s.BoundBox.YMax, s.BoundBox.ZMax)],
    }
    FreeCAD.closeDocument(doc.Name)
    record["source_unchanged"] = sha256(SOURCE) == SOURCE_SHA256

    (OUT / "geometry-check.json").write_text(json.dumps(record, indent=2))
    render(shape, to_deck, shift, record)
    print(json.dumps(record, indent=2))


def render(shape, to_deck, shift, record):
    """Annotated interface views in the deck frame."""
    import pyvista as pv

    verts, tris = shape.tessellate(0.1)
    pts = np.array([[v.x, v.y, v.z] for v in verts]) @ to_deck.T + shift
    mesh = pv.PolyData(pts, np.c_[np.full(len(tris), 3), np.array(tris)].ravel())
    pin = record["pin"]
    pin_ref = np.array(record["frame"]["pin_ref_in_deck_frame"])
    pin_axis = np.array(record["frame"]["pin_axis_in_deck_frame"])
    views = {"iso": None, "top": "xy", "side": "yz", "front": "xz"}
    for name, view in views.items():
        p = pv.Plotter(off_screen=True, window_size=(1400, 1000))
        p.set_background("white")
        p.add_mesh(mesh, color="#d9d9d9", opacity=0.55 if name != "iso" else 0.8, smooth_shading=True)
        p.add_mesh(pv.Cylinder(center=pin_ref, direction=pin_axis, radius=PIN_D / 2, height=pin["clevis_outer_span_mm"] + 10), color="#2166ac", opacity=0.6)
        labels, lpts = [f"I1 pin Ø{PIN_D} ref {pin_ref.round(2).tolist()}"], [pin_ref + np.array([0, 0, 18])]
        for b in record["bolts"]:
            seat = b["nut_seat"]
            c = np.r_[b["axis_xy_deck"], seat["height_above_base_bottom_mm"]]
            p.add_mesh(pv.Disc(center=c + [0, 0, 0.05], inner=NUT_ID / 2, outer=NUT_OD / 2, normal=(0, 0, 1), c_res=72), color="#b2182b")
            p.add_mesh(pv.Line(c - [0, 0, 5], c + [0, 0, 20]), color="#b2182b", line_width=3)
            labels.append(f"{b['label']} hole Ø{b['hole_d_mm']:.3f} seat z={seat['height_above_base_bottom_mm']:.2f}")
            lpts.append(c + [0, 0, 22])
        p.add_point_labels(np.array(lpts), labels, font_size=14, point_size=8, point_color="black", shape_opacity=0.8, always_visible=True)
        p.add_mesh(pv.Arrow((0, 0, 0), (-1, 0, 0), scale=30), color="#1b7837")
        p.add_point_labels(np.array([[-32, 0, 0]]), ["out (−x, LC2)"], font_size=12, always_visible=True)
        p.add_axes()
        p.show_grid(color="#888888")
        if view:
            getattr(p, f"view_{view}")()
        else:
            p.view_isometric()
        p.enable_parallel_projection()
        p.reset_camera()
        p.camera.zoom(1.05)
        p.add_text(f"Iteration1.stp in SimJEB deck frame | {name} | red annulus = GE nut face Ø{NUT_ID}/Ø{NUT_OD}", font_size=11, color="black")
        p.screenshot(str(OUT / f"interfaces_{name}.png"))
        p.close()


if __name__ == "__main__":
    main()

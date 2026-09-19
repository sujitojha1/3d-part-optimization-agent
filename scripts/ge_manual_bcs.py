"""M2A.4: nut-seat supports and rigid-pin load transfer for the GE manual study.

Two steps:

  partition  Imprint a coplanar disc of the GE nut-face OD (14.173 mm) on each of
             the four nut seats of data/ge_manual/Iteration1_manual.FCStd, so each
             seat splits into a nut-contact patch (hole edge to 14.173 mm) and a
             free outer ring. Writes data/ge_manual/Iteration1_partitioned.FCStd,
             the geometry M2A.2 meshes and everything later uses.

  setup      On a mesh level's document from M2A.2, add what a person adds by hand:
             CalculiX solver, the Ti-6Al-4V card, Fixed_B1..B4 on the four patches
             and one Rigid Body Constraint `Pin` on both lug bores, reference node
             at the pin reference point. Writes an LC1 deck (force on the reference
             node) and an LC4 deck (moment on the rotation node) and checks them:
             node sets against the mesh, restrained DOFs, no extra restraints,
             *RIGID BODY and *CLOAD cards. With --solve, runs ccx on both and
             reports the summed support reactions (a smoke test; the balance
             check with moments is M2A.6).

Outputs: out/ge_manual_bcs/bcs.json and views; data/ge_manual/bcs/<level>/
(gitignored, derived from licensed CAD).

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_manual_bcs.py partition
    vendor/fem-env/bin/python scripts/ge_manual_bcs.py setup [--level L1] [--solve]
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
import Part  # noqa: E402
from femtools import ccxtools  # noqa: E402

from ge_manual_materials import CARDS  # noqa: E402

GEOMETRY_CHECK = ROOT / "out" / "ge_manual_geometry" / "geometry-check.json"
SOURCE = ROOT / "data" / "ge_manual" / "Iteration1_manual.FCStd"
PARTITIONED = ROOT / "data" / "ge_manual" / "Iteration1_partitioned.FCStd"
MESH_DIR = ROOT / "data" / "ge_manual" / "mesh"
DATA = ROOT / "data" / "ge_manual" / "bcs"
OUT = ROOT / "out" / "ge_manual_bcs"

NUT_ID = 10.287   # GE brief section 2: nut face max ID
NUT_OD = 14.173   # nut face min OD
PIN_BORE_R = 9.557
LC1_FORCE = (0.0, 0.0, 35585.77)       # N, SimJEB 148.fem FORCE 2
LC4_MOMENT = (0.0, 0.0, 564924.2)      # N*mm, SimJEB 148.fem MOMENT 5


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vec(v):
    return np.array([v.x, v.y, v.z])


def geometry():
    return json.loads(GEOMETRY_CHECK.read_text())


def patch_faces(shape, geom):
    """Per bolt: the nut-contact patch (touches the hole edge) and the free ring."""
    out = {}
    for b in geom["bolts"]:
        axis = np.array(b["axis_xy_deck"])
        z = b["nut_seat"]["height_above_base_bottom_mm"]
        hole_r = b["hole_d_mm"] / 2
        found = {"patch": [], "ring": []}
        for i, f in enumerate(shape.Faces, 1):
            if not isinstance(f.Surface, Part.Plane):
                continue
            c = vec(f.CenterOfMass)
            if abs(c[2] - z) > 0.01 or np.linalg.norm(c[:2] - axis) > 0.5 or f.Area > 200:
                continue
            radii = sorted(round(e.Curve.Radius, 3) for e in f.Edges if hasattr(e.Curve, "Radius"))
            kind = "patch" if any(abs(r - hole_r) < 1e-3 for r in radii) else "ring"
            found[kind].append({"face": f"Face{i}", "area_mm2": round(f.Area, 3), "edge_radii": sorted(set(radii))})
        out[b["label"]] = {"axis_xy_deck": b["axis_xy_deck"], "seat_z": z, "hole_d_mm": b["hole_d_mm"], **found}
    return out


def bore_faces(shape):
    return [f"Face{i}" for i, f in enumerate(shape.Faces, 1)
            if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - PIN_BORE_R) < 0.01]


def partition():
    OUT.mkdir(parents=True, exist_ok=True)
    geom = geometry()
    doc = FreeCAD.openDocument(str(SOURCE))
    shape = doc.getObject("Bracket").Shape.copy()
    pin_ref = doc.getObject("PinReference")
    pin_xyz = (pin_ref.X.Value, pin_ref.Y.Value, pin_ref.Z.Value)
    FreeCAD.closeDocument(doc.Name)
    discs = []
    for b in geom["bolts"]:
        x, y = b["axis_xy_deck"]
        z = b["nut_seat"]["height_above_base_bottom_mm"]
        circle = Part.makeCircle(NUT_OD / 2, FreeCAD.Vector(x, y, z), FreeCAD.Vector(0, 0, 1))
        discs.append(Part.Face(Part.Wire(circle)))
    fused, _ = shape.generalFuse(discs, 1e-4)
    if len(fused.Solids) != 1:
        sys.exit(f"partition produced {len(fused.Solids)} solids")
    solid = fused.Solids[0]
    rec = {"source": str(SOURCE.relative_to(ROOT)), "source_sha256": sha256(SOURCE),
           "method": f"generalFuse with four coplanar discs, diameter {NUT_OD} mm, on the seat planes",
           "faces_before": len(shape.Faces), "faces_after": len(solid.Faces), "valid": solid.isValid(),
           "volume_before_mm3": round(shape.Volume, 4), "volume_after_mm3": round(solid.Volume, 4),
           "patches": patch_faces(solid, geom), "pin_bore_faces": bore_faces(solid)}
    if abs(solid.Volume - shape.Volume) > 1e-6 * shape.Volume or not rec["valid"]:
        sys.exit(f"partition changed the solid: {rec}")
    for label, p in rec["patches"].items():
        if len(p["patch"]) != 1 or len(p["ring"]) != 1:
            sys.exit(f"{label}: expected one patch and one ring, got {p}")

    new = FreeCAD.newDocument("Iteration1_partitioned")
    part = new.addObject("Part::Feature", "Bracket")
    part.Shape = solid
    part.Label = "Bracket (Iteration1.stp, deck frame, nut seats partitioned)"
    ref = new.addObject("Part::Vertex", "PinReference")
    ref.X, ref.Y, ref.Z = pin_xyz
    new.recompute()
    PARTITIONED.unlink(missing_ok=True)
    new.saveAs(str(PARTITIONED))
    FreeCAD.closeDocument(new.Name)
    rec["partitioned"] = str(PARTITIONED.relative_to(ROOT))
    rec["partitioned_sha256"] = sha256(PARTITIONED)
    rec["pin_reference_deck"] = list(pin_xyz)
    (OUT / "partition.json").write_text(json.dumps(rec, indent=2))
    print(json.dumps({k: rec[k] for k in ("faces_before", "faces_after", "volume_before_mm3", "volume_after_mm3")}))
    for label, p in rec["patches"].items():
        print(label, p["patch"], p["ring"])


def build(level, part_rec, case):
    """Analysis objects for one case on a copy of the level's mesh document."""
    doc = FreeCAD.openDocument(str(MESH_DIR / level / f"Iteration1_mesh_{level}.FCStd"))
    part, analysis = doc.getObject("Bracket"), doc.getObject("Analysis")
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
    solver.AnalysisType = "static"
    analysis.addObject(solver)
    c = CARDS["ti6al4v"]
    mat = ObjectsFem.makeMaterialSolid(doc, "Material")
    card = mat.Material
    card.update({"Name": c["name"], "YoungsModulus": f"{c['youngs_mpa']} MPa", "PoissonRatio": str(c["poisson"]),
                 "Density": f"{c['density_kg_m3']} kg/m^3", "YieldStrength": f"{c['yield_mpa']} MPa"})
    mat.Material = card
    mat.References = [(part, "Solid1")]
    analysis.addObject(mat)
    for label, p in part_rec["patches"].items():
        fixed = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{label}")
        fixed.References = [(part, p["patch"][0]["face"])]
        analysis.addObject(fixed)
    pin = ObjectsFem.makeConstraintRigidBody(doc, "Pin")
    pin.References = [(part, tuple(part_rec["pin_bore_faces"]))]
    pin.ReferenceNode = FreeCAD.Vector(*part_rec["pin_reference_deck"])
    force, moment = case["force"], case["moment"]
    for i, axis in enumerate("XYZ"):
        setattr(pin, f"TranslationalMode{axis}", "Load")
        setattr(pin, f"Force{axis}", f"{force[i]} N")
        setattr(pin, f"RotationalMode{axis}", "Load")
        setattr(pin, f"Moment{axis}", f"{moment[i]} N*mm")
    analysis.addObject(pin)
    doc.recompute()
    return doc, part, analysis, solver


def parse_deck(text):
    """Node sets, boundary cards, rigid-body and load cards written by FreeCAD."""
    nsets = {}
    for name, body in re.findall(r"\*NSET,NSET=(\S+)\n(.*?)(?=\n\*|\n\s*\n)", text, re.S):
        nsets[name] = {int(t) for t in re.split(r"[,\s]+", body) if t.strip().isdigit()}
    boundary = re.findall(r"\*BOUNDARY[^\n]*\n((?:[^*\n][^\n]*\n)+)", text)
    bnd = [line.strip() for block in boundary for line in block.splitlines() if line.strip()]
    rigid = re.findall(r"(\*RIGID BODY[^\n]*)", text)
    cload = re.findall(r"\*CLOAD[^\n]*\n((?:[^*\n][^\n]*\n)+)", text)
    cl = [line.strip() for block in cload for line in block.splitlines() if line.strip()]
    extra_nodes = re.findall(r"^(\d+),([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)$", text, re.M)
    return nsets, bnd, rigid, cl, extra_nodes


def check(level, part_rec, doc, part, case_name, inp):
    """Compare the deck's sets and cards with the mesh nodes on the chosen faces."""
    fem = doc.getObject("Mesh").FemMesh
    shape = part.Shape
    text = inp.read_text()
    nsets, bnd, rigid, cl, _ = parse_deck(text)
    rec = {"inp": str(inp.relative_to(ROOT)), "sha256": sha256(inp), "supports": {}, "boundary_lines": bnd,
           "rigid_body_cards": rigid, "cload_lines": cl}
    fixed_union = set()
    for label, p in part_rec["patches"].items():
        face = shape.Faces[int(p["patch"][0]["face"][4:]) - 1]
        ring = shape.Faces[int(p["ring"][0]["face"][4:]) - 1]
        mesh_nodes = set(fem.getNodesByFace(face))
        ring_nodes = set(fem.getNodesByFace(ring))
        deck = nsets.get(f"Fixed_{label}", set())
        fixed_union |= deck
        rec["supports"][label] = {
            "face": p["patch"][0]["face"], "nodes_in_deck": len(deck), "nodes_on_face": len(mesh_nodes),
            "deck_equals_face_nodes": deck == mesh_nodes,
            "ring_nodes_fixed_excluding_shared_edge": len((deck & ring_nodes) - mesh_nodes),
            "shared_edge_nodes": len(mesh_nodes & ring_nodes),
            "boundary_dofs": sorted({line.split(",")[1] for line in bnd if line.startswith(f"Fixed_{label},")}),
        }
    bores = [shape.Faces[int(f[4:]) - 1] for f in part_rec["pin_bore_faces"]]
    bore_nodes = set().union(*(set(fem.getNodesByFace(f)) for f in bores))
    pin_deck = nsets.get("Pin", set())
    # Group the four bore faces into the two lugs by axial position.
    axis = np.array([0.030278, -0.999542, 0.0])
    lug_of = {f: ("lug_A" if np.dot(vec(shape.Faces[int(f[4:]) - 1].CenterOfMass), axis) < 74.7 else "lug_B")
              for f in part_rec["pin_bore_faces"]}
    lug_nodes = {}
    for f, lug in lug_of.items():
        lug_nodes.setdefault(lug, set()).update(fem.getNodesByFace(shape.Faces[int(f[4:]) - 1]))
    rec["pin"] = {"faces": part_rec["pin_bore_faces"], "nodes_in_deck": len(pin_deck), "nodes_on_bores": len(bore_nodes),
                  "deck_equals_bore_nodes": pin_deck == bore_nodes,
                  "nodes_per_lug": {k: len(v & pin_deck) for k, v in lug_nodes.items()}}
    other_bnd = [line for line in bnd if not line.startswith("Fixed_")]
    rec["extra_restraints"] = other_bnd
    rec["fixed_nodes_total"] = len(fixed_union)
    rec["fixed_and_pin_overlap"] = len(fixed_union & pin_deck)
    m = re.search(r"REF NODE=(\d+), ROT NODE=(\d+)", rigid[0]) if rigid else None
    ref, rot = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    loads = {}
    for line in cl:
        n, dof, val = line.split(",")
        loads.setdefault(int(n), {})[int(dof)] = float(val)
    rec["ref_node"], rec["rot_node"] = ref, rot
    rec["loads_on_ref_node"] = loads.get(ref, {})
    rec["loads_on_rot_node"] = loads.get(rot, {})
    rec["loads_elsewhere"] = {n: v for n, v in loads.items() if n not in (ref, rot)}
    node_lines = dict((int(n), (float(x), float(y), float(z))) for n, x, y, z in
                      re.findall(r"^(\d+),([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)$", text, re.M) if int(n) in (ref, rot))
    rec["ref_node_xyz"] = node_lines.get(ref)
    rec["rot_node_xyz"] = node_lines.get(rot)
    return rec


def solve(analysis, solver, work):
    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(str(work), create=True)
    fea.write_inp_file()
    t = time.perf_counter()
    code = fea.ccx_run()
    elapsed = time.perf_counter() - t
    dat = Path(fea.inp_file_name).with_suffix(".dat")
    text = dat.read_text() if dat.exists() else ""
    totals = {}
    for name, fx, fy, fz in re.findall(r"total force \(fx,fy,fz\) for set (\S+) and time\s+\S+\s*\n\s*\n?\s*(\S+)\s+(\S+)\s+(\S+)", text):
        totals[name] = [float(fx), float(fy), float(fz)]
    work.mkdir(parents=True, exist_ok=True)  # setup_working_dir does not create it in 1.1.3
    for f in (dat, Path(fea.inp_file_name).with_suffix(".frd"), Path(fea.inp_file_name)):
        if f.exists():
            shutil.copyfile(f, work / f.name)
    return {"ccx_exit": code, "elapsed_s": round(elapsed, 1), "reaction_totals": totals,
            # ccx also prints the pin's reference and rotation nodes; sum the supports only.
            "support_reaction_sum_N": [round(sum(v[i] for k, v in totals.items() if k.startswith("FIXED_")), 3)
                                       for i in range(3)] if totals else None}


def render(level, part_rec, shape):
    import pyvista as pv

    verts, tris = shape.tessellate(0.1)
    def mesh_of(faces):
        polys = []
        for f in faces:
            v, t = f.tessellate(0.05)
            if t:
                polys.append(pv.PolyData(np.array([[p.x, p.y, p.z] for p in v]), np.c_[np.full(len(t), 3), np.array(t)].ravel()))
        return polys
    body = pv.PolyData(np.array([[v.x, v.y, v.z] for v in verts]), np.c_[np.full(len(tris), 3), np.array(tris)].ravel())
    patches = [shape.Faces[int(p["patch"][0]["face"][4:]) - 1] for p in part_rec["patches"].values()]
    rings = [shape.Faces[int(p["ring"][0]["face"][4:]) - 1] for p in part_rec["patches"].values()]
    bores = [shape.Faces[int(f[4:]) - 1] for f in part_rec["pin_bore_faces"]]
    ref = np.array(part_rec["pin_reference_deck"])
    for name, view in (("iso", None), ("top", "xy"), ("front", "xz")):
        p = pv.Plotter(off_screen=True, window_size=(1400, 1000))
        p.set_background("white")
        p.add_mesh(body, color="#d9d9d9", opacity=0.45)
        for m in mesh_of(patches):
            p.add_mesh(m, color="#b2182b")
        for m in mesh_of(rings):
            p.add_mesh(m, color="#fdae61")
        for m in mesh_of(bores):
            p.add_mesh(m, color="#2166ac")
        p.add_mesh(pv.Sphere(radius=1.5, center=ref), color="black")
        p.add_mesh(pv.Arrow(ref, (0, 0, 1), scale=25), color="#1b7837")
        labels = [f"Pin ref {ref.round(3).tolist()}: LC1 Fz (green), LC4 Mz"]
        pts = [ref + [0, 0, 28]]
        for label, prec in part_rec["patches"].items():
            labels.append(f"Fixed_{label} {prec['patch'][0]['face']} {prec['patch'][0]['area_mm2']} mm2")
            pts.append(np.r_[prec["axis_xy_deck"], prec["seat_z"] + 6])
        p.add_point_labels(np.array(pts), labels, font_size=13, point_size=6, always_visible=True, shape_opacity=0.8)
        p.add_axes()
        if view:
            getattr(p, f"view_{view}")()
        else:
            p.view_isometric()
        p.enable_parallel_projection()
        p.add_text("red = fixed nut patch (hole edge to Ø14.173), orange = free ring, blue = rigid-pin bores",
                   font_size=11, color="black")
        p.screenshot(str(OUT / f"bcs_{name}.png"))
        p.close()


def setup(level, run_solve):
    OUT.mkdir(parents=True, exist_ok=True)
    part_rec = json.loads((OUT / "partition.json").read_text())
    report_path = OUT / "bcs.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report.update({"partition": part_rec, "freecad_version": ".".join(FreeCAD.Version()[:3])})
    cases = {"LC1": {"force": LC1_FORCE, "moment": (0.0, 0.0, 0.0)},
             "LC4": {"force": (0.0, 0.0, 0.0), "moment": LC4_MOMENT}}
    level_rec = {}
    for name, case in cases.items():
        work = DATA / level / name
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        doc, part, analysis, solver = build(level, part_rec, case)
        doc.saveAs(str(work / f"Iteration1_bcs_{level}_{name}.FCStd"))
        fea = ccxtools.FemToolsCcx(analysis, solver)
        fea.update_objects()
        fea.write_inp_file()
        inp = work / f"{name}.inp"
        shutil.copyfile(fea.inp_file_name, inp)
        rec = check(level, part_rec, doc, part, name, inp)
        rec["applied_force_N"], rec["applied_moment_Nmm"] = case["force"], case["moment"]
        if run_solve:
            rec["solve"] = solve(analysis, solver, work / "solve")
        if name == "LC1":
            render(level, part_rec, part.Shape)
        FreeCAD.closeDocument(doc.Name)
        level_rec[name] = rec
        print(level, name, json.dumps({k: rec[k] for k in ("supports", "pin", "extra_restraints", "loads_on_ref_node",
                                                          "loads_on_rot_node", "loads_elsewhere", "ref_node_xyz")}),
              json.dumps(rec.get("solve")), flush=True)
    report.setdefault("levels", {})[level] = level_rec
    report_path.write_text(json.dumps(report, indent=2, default=list))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["partition", "setup"])
    parser.add_argument("--level", default="L1")
    parser.add_argument("--solve", action="store_true")
    args = parser.parse_args()
    if args.step == "partition":
        partition()
    else:
        setup(args.level, args.solve)


if __name__ == "__main__":
    main()

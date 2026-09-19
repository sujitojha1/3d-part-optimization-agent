"""M2A.5: the four independent GE static load cases on the M2A.4 supports and rigid pin.

For each of LC1-LC4, opens a fresh copy of the L1 mesh document from M2A.2 and adds
what a person adds by hand: CalculiX solver, the Ti-6Al-4V card, Fixed_B1..B4 on the
nut-contact patches and the rigid-body constraint `Pin` on both lug bores, with the
case's force and moment on its reference point (ge_manual_bcs.build). Each case is
its own document and deck, so no load can carry over from the one before.

Checks per deck: supports and pin as in M2A.4 (ge_manual_bcs.check); the *CLOAD
values on the reference node (force) and rotation node (moment) equal the case
vector, and no other node is loaded; the analysis holds exactly four fixed
constraints and one rigid body and nothing else that loads or restrains; the deck
is identical to every other case's once the *CLOAD cards and header are removed;
and the mesh document on disk is not changed. With --solve, runs ccx on each case
and reports the summed support reactions against the applied force (a smoke test;
the force and moment balance is M2A.6).

Vectors are in the SimJEB deck frame (+z up, out = -x), the frame of the working
copy, so they are applied unchanged. Sources: docs/ge-jet-engine-bracket.md s3 and
docs/simjeb-dataset.md s2.

Outputs: out/ge_manual_loads/loads.json and one view per case; data/ge_manual/loads/
L1/<case>/ (gitignored, derived from licensed CAD). Only L1 is used: the L2 solve ran
out of memory (docs/ge-manual-mesh.md).

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_manual_loads.py [--solve]
"""

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
from femtools import ccxtools  # noqa: E402

from ge_manual_bcs import MESH_DIR, OUT as BCS_OUT, build, check, sha256, solve  # noqa: E402

LEVEL = "L1"
DATA = ROOT / "data" / "ge_manual" / "loads" / LEVEL
OUT = ROOT / "out" / "ge_manual_loads"

# N and N*mm in the deck frame; SimJEB 148.fem FORCE/MOMENT cards.
CASES = {
    "LC1": {"title": "vertical", "force": (0.0, 0.0, 35585.77), "moment": (0.0, 0.0, 0.0)},
    "LC2": {"title": "horizontal", "force": (-37809.9, 0.0, 0.0), "moment": (0.0, 0.0, 0.0)},
    "LC3": {"title": "diagonal, 42 deg from vertical", "force": (-28276.2, 0.0, 31403.9), "moment": (0.0, 0.0, 0.0)},
    "LC4": {"title": "torsion about +z", "force": (0.0, 0.0, 0.0), "moment": (0.0, 0.0, 564924.2)},
}

# Constraint types that load or restrain; the analysis must hold only the expected ones.
LOADING_TYPES = ("Fem::ConstraintFixed", "Fem::ConstraintRigidBody", "Fem::ConstraintForce",
                 "Fem::ConstraintPressure", "Fem::ConstraintDisplacement", "Fem::ConstraintSelfWeight",
                 "Fem::ConstraintBearing", "Fem::ConstraintPlaneRotation", "Fem::ConstraintSpring",
                 "Fem::ConstraintTie", "Fem::ConstraintContact", "Fem::ConstraintCentrif",
                 "Fem::ConstraintSectionPrint", "Fem::ConstraintTransform")


def geometry_of(v):
    v = np.array(v)
    mag = float(np.linalg.norm(v))
    if mag == 0:
        return {"magnitude": 0.0}
    rec = {"magnitude": round(mag, 2), "deg_from_plus_z": round(math.degrees(math.acos(v[2] / mag)), 3)}
    h = np.linalg.norm(v[:2])
    if h > 0:
        rec["horizontal_deg_from_minus_x"] = round(math.degrees(math.acos(-v[0] / h)), 3)
    return rec


def analysis_types(analysis):
    counts = {}
    for o in analysis.Group:
        if o.TypeId in LOADING_TYPES:
            counts[o.TypeId] = counts.get(o.TypeId, 0) + 1
    return counts


def normalised(text):
    """The deck without its load cards and header comments, for comparing cases."""
    text = re.sub(r"\*CLOAD\n[^*\n][^\n]*\n", "", text)
    return "\n".join(line for line in text.splitlines() if not line.startswith("**"))


def load_checks(rec, case, pin_ref):
    ok = {}
    for i, axis in enumerate("xyz"):
        ok[f"force_{axis}"] = math.isclose(rec["loads_on_ref_node"].get(i + 1, math.nan), case["force"][i], abs_tol=1e-6)
        ok[f"moment_{axis}"] = math.isclose(rec["loads_on_rot_node"].get(i + 1, math.nan), case["moment"][i], abs_tol=1e-6)
    ok["no_other_loaded_nodes"] = not rec["loads_elsewhere"]
    ok["ref_node_at_pin_reference"] = rec["ref_node_xyz"] is not None and np.allclose(rec["ref_node_xyz"], pin_ref, atol=1e-6)
    ok["rot_node_at_pin_reference"] = rec["rot_node_xyz"] is not None and np.allclose(rec["rot_node_xyz"], pin_ref, atol=1e-6)
    return ok


def render(name, case, shape, part_rec):
    import pyvista as pv

    def poly(s, tol):
        v, t = s.tessellate(tol)
        return pv.PolyData(np.array([[p.x, p.y, p.z] for p in v]), np.c_[np.full(len(t), 3), np.array(t)].ravel())

    body = poly(shape, 0.1)
    patches = [poly(shape.Faces[int(p["patch"][0]["face"][4:]) - 1], 0.05) for p in part_rec["patches"].values()]
    bores = [poly(shape.Faces[int(f[4:]) - 1], 0.05) for f in part_rec["pin_bore_faces"]]
    ref = np.array(part_rec["pin_reference_deck"])
    force, moment = np.array(case["force"]), np.array(case["moment"])
    p = pv.Plotter(off_screen=True, window_size=(1800, 900), shape=(1, 2))
    for col, view in enumerate(("iso", "xz")):
        p.subplot(0, col)
        p.set_background("white")
        p.add_mesh(body, color="#d9d9d9", opacity=0.4)
        for m in patches:
            p.add_mesh(m, color="#b2182b")
        for m in bores:
            p.add_mesh(m, color="#2166ac")
        p.add_mesh(pv.Sphere(radius=1.5, center=ref), color="black")
        if np.linalg.norm(force):
            d = force / np.linalg.norm(force)
            p.add_mesh(pv.Arrow(start=ref, direction=d, scale=45, shaft_radius=0.03, tip_radius=0.08), color="#1b7837")
            tip, label = ref + 48 * d, f"F = ({force[0]:g}, {force[1]:g}, {force[2]:g}) N"
        else:
            # Moment about +z: axis arrow plus a counter-clockwise arc seen from +z.
            p.add_mesh(pv.Arrow(start=ref, direction=(0, 0, 1), scale=35, shaft_radius=0.03, tip_radius=0.08), color="#762a83")
            arc = pv.CircularArc(pointa=ref + [18, 0, 8], pointb=ref + [0, 18, 8], center=ref + [0, 0, 8], resolution=60)
            p.add_mesh(arc.tube(radius=0.8), color="#762a83")
            p.add_mesh(pv.Cone(center=ref + [0, 18, 8], direction=(-1, 0, 0), height=5, radius=2.2), color="#762a83")
            tip, label = ref + [0, 0, 40], f"M = ({moment[0]:g}, {moment[1]:g}, {moment[2]:g}) N*mm"
        p.add_point_labels(np.array([tip]), [label], font_size=14, point_size=1, always_visible=True, shape_opacity=0.8)
        p.add_axes()
        p.show_grid(color="#999999")
        if view == "xz":
            p.view_xz()
        else:
            p.view_isometric()
        p.enable_parallel_projection()
        p.add_text(f"{name} {case['title']} ({'iso' if view == 'iso' else 'front, x-z'})", font_size=12, color="black")
    p.screenshot(str(OUT / f"{name}.png"))
    p.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solve", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    part_rec = json.loads((BCS_OUT / "partition.json").read_text())
    mesh_doc = MESH_DIR / LEVEL / f"Iteration1_mesh_{LEVEL}.FCStd"
    mesh_sha = sha256(mesh_doc)
    report = {"level": LEVEL, "mesh_doc": str(mesh_doc.relative_to(ROOT)), "mesh_doc_sha256": mesh_sha,
              "freecad_version": ".".join(FreeCAD.Version()[:3]), "frame": "SimJEB deck frame: +z up, out = -x",
              "cases": {}}
    bodies = {}
    for name, case in CASES.items():
        work = DATA / name
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        doc, part, analysis, solver = build(LEVEL, part_rec, case)
        doc.saveAs(str(work / f"Iteration1_{name}_{LEVEL}.FCStd"))
        fea = ccxtools.FemToolsCcx(analysis, solver)
        fea.update_objects()
        fea.write_inp_file()
        inp = work / f"{name}.inp"
        shutil.copyfile(fea.inp_file_name, inp)
        rec = check(LEVEL, part_rec, doc, part, name, inp)
        rec.update({"title": case["title"], "applied_force_N": case["force"], "applied_moment_Nmm": case["moment"],
                    "force_geometry": geometry_of(case["force"]), "analysis_constraints": analysis_types(analysis)})
        rec["load_checks"] = load_checks(rec, case, part_rec["pin_reference_deck"])
        rec["constraints_as_expected"] = rec["analysis_constraints"] == {"Fem::ConstraintFixed": 4,
                                                                         "Fem::ConstraintRigidBody": 1}
        bodies[name] = normalised(inp.read_text())
        if args.solve:
            rec["solve"] = solve(analysis, solver, work / "solve")
            s = rec["solve"]["support_reaction_sum_N"]
            if s:
                rec["solve"]["support_sum_plus_applied_N"] = [round(s[i] + case["force"][i], 3) for i in range(3)]
        render(name, case, part.Shape, part_rec)
        FreeCAD.closeDocument(doc.Name)
        report["cases"][name] = rec
        print(name, json.dumps({k: rec[k] for k in ("load_checks", "constraints_as_expected", "extra_restraints",
                                                   "loads_on_ref_node", "loads_on_rot_node", "force_geometry")}),
              json.dumps(rec.get("solve")), flush=True)
    ref_body = bodies["LC1"]
    report["decks_identical_apart_from_loads"] = {n: b == ref_body for n, b in bodies.items()}
    report["mesh_doc_unchanged"] = sha256(mesh_doc) == mesh_sha
    report["all_checks_pass"] = (all(all(r["load_checks"].values()) and r["constraints_as_expected"]
                                     and not r["extra_restraints"] and r["fixed_and_pin_overlap"] == 0
                                     and all(s["deck_equals_face_nodes"] for s in r["supports"].values())
                                     and r["pin"]["deck_equals_bore_nodes"] for r in report["cases"].values())
                                 and all(report["decks_identical_apart_from_loads"].values())
                                 and report["mesh_doc_unchanged"])
    (OUT / "loads.json").write_text(json.dumps(report, indent=2, default=list))
    print("decks identical apart from loads:", report["decks_identical_apart_from_loads"],
          "mesh doc unchanged:", report["mesh_doc_unchanged"], "all checks pass:", report["all_checks_pass"])


if __name__ == "__main__":
    main()

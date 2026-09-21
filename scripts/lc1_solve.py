"""M2.5: hand-run the ccxtools solve of ge_bracket LC1 on the accepted D-24 mesh.

M2.2 ([#44](../docs/ge-bracket-lc1.md)) chose the rigid pin model on a provisional
4 mm mesh with no MeshRegion. M2.3 then froze D-24 sizing, and M2.4 found that no
D-06 label reaches the ccxtools deck, so the element-centroid fallback is the
route to a region label. This script joins the three:

    gm.build (D-24 mesh objects) -> mesh groups -> gmsh -> write_inp_file
        -> ccx_run -> load_results -> mass, stress, displacement, peak element

and reports the four M2.5 quantities on the full model:

- full-part mass in grams, from the CAD volume and cross-checked against the mesh
- maximum von Mises, both raw and outside the support zone the LC1 record fixes
- maximum displacement magnitude
- the peak element's D-06 region label, from M2.4's element-centroid partition

Every stage is timed. The total is the first measured input to D-13's budget of
8 evaluations in 20 minutes, and the 60 s figure in the 21 Sep cut trigger.

The raw peak is reported and flagged, never silently dropped: the fixed bolt-hole
faces are a singularity (fem-geometry-preparation section 13), which is why the
LC1 record's stress_check reads the peak outside the support zone. Both are here.

Run with FreeCAD's own Python:
    freecadcmd scripts/lc1_solve.py [--hmax MM] [--region MM] [--no-solve]

Writes the deck, the .frd and out/lc1_solve/result.json. Exit 0 when the solve
finished and every guard passed, 2 otherwise.
"""

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
from FreeCAD import Vector  # noqa: E402
from femtools import ccxtools  # noqa: E402

import ge_bracket_labels as gl  # noqa: E402  D-06 groups and the centroid fallback (M2.4)
import ge_bracket_mesh as gm  # noqa: E402  D-24 sizing and the Gmsh runner (M2.3)
import lc1_pin_models as pm  # noqa: E402  reaction and CLOAD readers (M2.2)
from parts import ge_bracket as gb  # noqa: E402

OUT = ROOT / "out" / "lc1_solve"
LC1 = json.loads((ROOT / "parts" / "ge_bracket_lc1.json").read_text())

# M2.2's hand calculation (docs/ge-bracket-lc1.md section 2), frozen here so the
# comparison is against what was written before the first solve, not after it.
HAND = {
    "bolt_share_n": {"bolt_hole_2": -10400.0, "bolt_hole_3": 28200.0,
                     "bolt_hole_4": 23200.0, "bolt_hole_5": -5300.0},
    "governing_vm_mpa": 174.0,        # base plate, -y wing, full-outline width
    "peak_region": "base_plate",
    "arm_root_fillet_mpa": 115.0,     # 76 MPa nominal x Kt about 1.5
    "pin_bearing_mpa": 117.0,
    "lug_net_section_mpa": 111.0,
}

# A second hot spot has to be a different site, not the far side of the first.
# 25 mm is wider than the 10 mm support zone and than the base-plate thickness.
RUNNER_UP_MIN_MM = 25.0


def environment():
    """What produced these numbers. D-17 pins macOS arm64; this records the truth."""
    ccx = shutil.which("ccx") or str(Path(sys.executable).parent / "ccx.exe")
    version = ""
    try:
        out = subprocess.run([ccx, "-v"], capture_output=True, text=True, timeout=30)
        version = (out.stdout + out.stderr).strip().splitlines()[-1]
    except Exception as e:  # the solve will fail later and say so
        version = f"unreadable: {type(e).__name__}"
    return {
        "freecad": ".".join(FreeCAD.Version()[:3]),
        "platform": f"{platform.system()}-{platform.machine()}",
        "python": platform.python_version(),
        "ccx": version,
        "ccx_binary": ccx,
        "d17_environment": "vendor/fem-env (osx-arm64)",
        "d17_met": (ROOT / "vendor" / "fem-env").exists(),
    }


def add_physics(doc, part, mesh, matched):
    """The LC1 record as FreeCAD objects: material, four fixed bolt holes, rigid pin.

    `matched` is `gb.match`'s predicate -> face indices, so every reference is
    resolved by geometry, never by a stored index. `gm.build` already made the
    Analysis and put the mesh in it, so this only adds what M2.3 had no need for.
    The pin model is the one M2.2 chose: `rigid`.
    """
    analysis = next(o for o in doc.Objects if o.isDerivedFrom("Fem::FemAnalysis"))
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
    analysis.addObject(solver)

    mat = LC1["material"]
    material = ObjectsFem.makeMaterialSolid(doc, "Material")
    card = material.Material
    card.update({"Name": mat["name"], "YoungsModulus": f"{mat['youngs_mpa']} MPa",
                 "PoissonRatio": str(mat["poisson"]), "Density": f"{mat['density_kg_m3']} kg/m^3"})
    material.Material = card
    analysis.addObject(material)

    supports = []  # one Fixed per hole, so ccx prints each bolt's reaction separately
    for name in LC1["support"]["predicates"]:
        fixed = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{name}")
        fixed.References = [(part, f"Face{matched[name][0]}")]
        analysis.addObject(fixed)
        supports.append(fixed)

    fx, fy, fz = LC1["load"]["vector_n"]
    pin = ObjectsFem.makeConstraintRigidBody(doc, "Pin")
    pin.References = [(part, f"Face{matched[n][0]}") for n in LC1["load"]["load_faces"]]
    pin.ReferenceNode = Vector(*LC1["load"]["applied_at"])
    for axis, value in zip("XYZ", (fx, fy, fz)):
        setattr(pin, f"TranslationalMode{axis}", "Load")
        setattr(pin, f"Force{axis}", f"{value} N")
    analysis.addObject(pin)
    doc.recompute()
    return analysis, solver, supports


def element_stress(fm, vm):
    """Per volume element, the maximum nodal von Mises over its nodes, and the map
    from node to the elements that carry it. The peak element is the element the
    peak node sits in; a node is shared, so the tie is resolved by reporting every
    element that holds it and whether they agree on a label."""
    per_element, holders = {}, {}
    for eid in fm.Volumes:
        nodes = fm.getElementNodes(eid)
        per_element[eid] = max(vm.get(n, 0.0) for n in nodes)
        for n in nodes:
            holders.setdefault(n, []).append(eid)
    return per_element, holders


def meshed_volume(fm):
    """Sum of the straight-edge tet volumes: a discretisation check on the CAD mass,
    not a second measurement of it. Curved tet10 faces make it a slight under-read."""
    nodes = fm.Nodes
    total = 0.0
    for eid in fm.Volumes:
        a, b, c, d = (nodes[n] for n in fm.getElementNodes(eid)[:4])
        total += abs((b - a).cross(c - a).dot(d - a)) / 6.0
    return total


def label_of(node, holders, label_by_element):
    """The D-06 label of the elements holding one node: the agreed label, or the
    conflict. This is the unambiguous-evidence check the peak reading needs."""
    elements = holders.get(node, [])
    labels = sorted({label_by_element[e] for e in elements if e in label_by_element})
    return {"elements": len(elements), "labels": labels,
            "label": labels[0] if len(labels) == 1 else None,
            "unambiguous": len(labels) == 1}


def solve(hmax, region_size, curvature, run_ccx, out=OUT):
    OUT = out  # noqa: F841  local to this run, so a probe cannot overwrite the record
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    record = {"task": "M2.5", "load_case": LC1["name"], "model_extent": LC1["model_extent"],
              "environment": environment(), "timings_s": {}, "problems": []}

    p = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    if hmax is not None:
        gm.SIZES["max"] = hmax
    if region_size is not None:
        gm.SIZES["region"] = region_size
    if curvature is not None:
        gm.SIZES["curvature"] = curvature
    record["d24_sizes_mm"] = dict(gm.SIZES)

    t = time.perf_counter()
    doc, part, mesh, shape, geom = gm.build(p["arm_root_fillet"], half=False, params=p)
    record["timings_s"]["cad"] = round(time.perf_counter() - t, 2)
    record["geometry"] = geom
    record["mesh_settings"] = gm.settings(mesh)

    faces, problems = gl.cad_labels(shape, p)
    record["problems"] += problems
    if problems:
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record
    gl.add_groups(doc, part, mesh, faces)  # M2.4: they never reach the deck, but they
    #                                        are where the centroid fallback's labels start
    analysis, solver, supports = add_physics(doc, part, mesh, gb.match(shape, p))

    tools, err, mesh_s = gm.run_gmsh(mesh, OUT / "gmsh")
    record["timings_s"]["mesh"] = round(mesh_s, 2)
    if err:
        record["problems"].append(f"gmsh: {err}")
    fm = mesh.FemMesh
    record["mesh"] = {"nodes": fm.NodeCount, "c3d10": fm.VolumeCount,
                      "surface_elements": fm.FaceCount}
    if fm.VolumeCount == 0:
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record

    # Mass (M2.5's first quantity). The CAD volume is the contract; the mesh is the check.
    vol_cad = shape.Volume
    vol_mesh = meshed_volume(fm)
    record["mass"] = {
        "grams": round(vol_cad * gb.DENSITY_G_MM3, 2),
        "volume_mm3": round(vol_cad, 3),
        "density_g_mm3": gb.DENSITY_G_MM3,
        "source": "CAD solid volume x Ti-6Al-4V density (SimJEB MAT1)",
        "meshed_volume_mm3": round(vol_mesh, 3),
        "mesh_vs_cad_pct": round(100 * (vol_mesh - vol_cad) / vol_cad, 3),
    }

    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    # ccxtools' own `create` only prints; an absent dir silently becomes a temp dir.
    (OUT / "ccx").mkdir(parents=True, exist_ok=True)
    fea.setup_working_dir(str(OUT / "ccx"), create=True)
    fea.setup_ccx()
    record["environment"]["ccx_used"] = str(getattr(fea, "ccx_binary", ""))
    if Path(fea.working_dir).resolve() != (OUT / "ccx").resolve():
        record["problems"].append(f"ccxtools redirected the working dir to {fea.working_dir}")
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record
    blockers = fea.check_prerequisites()
    if blockers:
        record["problems"].append(f"prerequisites: {blockers}")
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record

    t = time.perf_counter()
    fea.write_inp_file()
    record["timings_s"]["write_inp"] = round(time.perf_counter() - t, 2)
    work = Path(fea.working_dir)
    inp = work / f"{mesh.Name}.inp"
    record["deck"] = {"inp": str(inp.relative_to(ROOT)), "bytes": inp.stat().st_size,
                      "sets": gl.deck_sets(inp), "d06_sets": gl.d06_sets(gl.deck_sets(inp))}
    if record["deck"]["d06_sets"]:
        record["problems"].append("D-06 sets unexpectedly present in the deck (M2.4 says none)")
    if not run_ccx:
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        record["problems"].append("--no-solve: deck written, ccx not run")
        return record

    t = time.perf_counter()
    code = fea.ccx_run()
    record["timings_s"]["ccx"] = round(time.perf_counter() - t, 2)
    if code != 0:
        record["problems"].append(f"ccx exited {code}")
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record

    t = time.perf_counter()
    fea.load_results()
    record["timings_s"]["load_results"] = round(time.perf_counter() - t, 2)
    res = next(o for o in analysis.Group if o.isDerivedFrom("Fem::FemResultObject"))

    nodes = fm.Nodes
    vm = dict(zip(res.NodeNumbers, res.vonMises))
    disp = dict(zip(res.NodeNumbers, res.DisplacementVectors))
    if not vm or max(vm.values()) == 0.0:  # D-24's silent failure mode
        record["problems"].append("all-zero stress field")
        FreeCAD.closeDocument(doc.Name)
        record["ok"] = False
        return record

    # D-06 labels: the element-centroid partition, because no label reaches the deck.
    t = time.perf_counter()
    got = gl.femmesh_groups(fm)
    sets, checks = gl.centroid_labels(fm, got)
    record["timings_s"]["labels"] = round(time.perf_counter() - t, 2)
    record["d06_partition"] = checks
    if not checks["ok"]:
        record["problems"].append(f"centroid fallback is not a partition: {checks}")
    gl.write_elsets(OUT / "d06_elsets.inp", sets)
    label_by_element = {e: r for r, members in sets.items() for e in members}
    per_element, holders = element_stress(fm, vm)

    def at(node):
        c = nodes[node]
        return [round(c.x, 2), round(c.y, 2), round(c.z, 2)]

    def report(node):
        return {"mpa": round(vm[node], 1), "node": int(node), "at_mm": at(node),
                "region": label_of(node, holders, label_by_element)}

    # The support zone the LC1 record fixes: a plan radius about each bolt axis,
    # full height. Outside it the field is a real stress; inside it is singular.
    zone_r = LC1["support"]["zone"]["radius_mm"]
    outside = [n for n in vm
               if min(math.hypot(nodes[n].x - x, nodes[n].y - y)
                      for x, y in gb.BOLT_CENTRES) > zone_r]
    raw_peak = max(vm, key=vm.get)
    zone_peak = max(outside, key=vm.get)
    disp_peak = max(disp, key=lambda n: disp[n].Length)

    # The governing peak sits on one of two base-plate wings that carry almost the
    # same stress, so the argmax can move between meshes while the value barely
    # does. The runner-up is the highest node outside the zone and at least
    # RUNNER_UP_MIN_MM from the first peak: a second site, not the same hot spot.
    far = [n for n in outside
           if (nodes[n] - nodes[zone_peak]).Length >= RUNNER_UP_MIN_MM]
    runner_up = max(far, key=vm.get) if far else None

    # Per region, from the disjoint element partition, not from overlapping face nodes.
    by_region = {}
    for region, members in sets.items():
        top = max(members, key=lambda e: per_element[e])
        node = max(fm.getElementNodes(top), key=lambda n: vm.get(n, 0.0))
        by_region[region] = {"mpa": round(per_element[top], 1), "element": int(top),
                             "at_mm": at(node), "elements": len(members)}

    per_bolt = {f.Name[len("Fixed_"):]: pm.reactions(work / f"{mesh.Name}.dat", f.Name)
                for f in supports}
    load = Vector(*LC1["load"]["vector_n"])
    if any(v is None for v in per_bolt.values()):
        record["problems"].append("no reaction totals in the .dat")
        rf, angle, error_pct = [0.0, 0.0, 0.0], None, None
    else:
        rf = [sum(v[k] for v in per_bolt.values()) for k in range(3)]
        angle = round(math.degrees((-Vector(*rf)).getAngle(load)), 4)
        error_pct = round(100 * ((-Vector(*rf)).Length - load.Length) / load.Length, 4)
        if angle > 0.1 or abs(error_pct) > 0.5:  # REQ-VER-006's balance check
            record["problems"].append(f"reactions {rf} do not balance the load {tuple(load)}")

    allowable = LC1["allowable_vm_mpa"]
    record["result"] = {
        "raw_peak_vm": {**report(raw_peak), "flag": "support singularity: fixed hole faces "
                        "(fem-geometry-preparation section 13); not a converged stress"},
        "peak_vm_outside_support_zone": {**report(zone_peak), "zone_radius_mm": zone_r},
        "peak_vm_outside_support_zone_runner_up": (
            {**report(runner_up), "min_separation_mm": RUNNER_UP_MIN_MM,
             "separation_mm": round((nodes[runner_up] - nodes[zone_peak]).Length, 1),
             "fraction_of_peak": round(vm[runner_up] / vm[zone_peak], 3)}
            if runner_up else None),
        "peak_vm_by_region": by_region,
        "max_disp_mm": round(disp[disp_peak].Length, 4),
        "max_disp_at_mm": at(disp_peak),
        "max_disp_node": int(disp_peak),
        "pin_bore_mean_uz_mm": round(
            float(np.mean([disp[n].z for e in sets["pin_bore"] for n in fm.getElementNodes(e)
                           if n in disp])), 4),
        "reaction_total_n": [round(v, 2) for v in rf],
        "reaction_by_bolt_n": {k: [round(c, 1) for c in v] for k, v in per_bolt.items()
                               if v is not None},
        "reaction_angle_deg": angle,
        "reaction_magnitude_error_pct": error_pct,
        "written_cload_n": [round(v, 2) for v in pm.written_load(inp)],
    }
    record["check"] = {
        "quantity": LC1["stress_check"]["quantity"],
        "allowable_mpa": allowable,
        "measured_mpa": record["result"]["peak_vm_outside_support_zone"]["mpa"],
        "margin": round(allowable / record["result"]["peak_vm_outside_support_zone"]["mpa"], 3),
        "passes": record["result"]["peak_vm_outside_support_zone"]["mpa"] <= allowable,
        "raw_peak_mpa": record["result"]["raw_peak_vm"]["mpa"],
        "raw_peak_would_pass": record["result"]["raw_peak_vm"]["mpa"] <= allowable,
        "displacement_limit_mm": LC1["displacement_limit"]["limit_mm"],
        "note": "M2.5 reports both peaks. The headline is the peak outside the support "
                "zone; the raw peak is flagged. The raw-versus-exclusion acceptance "
                "question stays open for REQ-VER-002 and D-12 (plan.md next action 3).",
    }

    # Against the hand calculation, which was written before any solve.
    fe_by_bolt = {k: round(v[2], 1) for k, v in per_bolt.items() if v is not None}
    record["vs_hand_calculation"] = {
        "source": "docs/ge-bracket-lc1.md section 2 (M2.2, before the first solve)",
        "bolt_fz_n": {k: {"hand": HAND["bolt_share_n"][k], "fe_reaction": fe_by_bolt.get(k)}
                      for k in HAND["bolt_share_n"]},
        "bolt_sign_pattern_agrees": all(
            HAND["bolt_share_n"][k] * -fe_by_bolt[k] > 0 for k in fe_by_bolt) if fe_by_bolt else None,
        "governing_vm_mpa": {"hand": HAND["governing_vm_mpa"],
                             "fe": record["result"]["peak_vm_outside_support_zone"]["mpa"],
                             "fe_over_hand": round(
                                 record["result"]["peak_vm_outside_support_zone"]["mpa"]
                                 / HAND["governing_vm_mpa"], 2)},
        "peak_region": {"hand": HAND["peak_region"],
                        "fe": record["result"]["peak_vm_outside_support_zone"]["region"]["label"]},
        "arm_root_fillet_mpa": {"hand": HAND["arm_root_fillet_mpa"],
                                "fe": by_region.get("arm_root_fillet", {}).get("mpa")},
        "pin_bore_mpa": {"hand_bearing": HAND["pin_bearing_mpa"],
                         "fe": by_region.get("pin_bore", {}).get("mpa")},
    }

    total = round(sum(record["timings_s"].values()), 2)
    record["timings_s"]["total"] = total
    record["d13"] = {
        "solve_s": record["timings_s"]["ccx"],
        "cad_to_result_s": total,
        "cut_trigger_s": 60.0,
        "cut_trigger_quantity": "mesh and solve, full model (D-23 does not hold)",
        "mesh_and_solve_s": round(record["timings_s"]["mesh"] + record["timings_s"]["ccx"], 2),
        "budget_evaluations": 8,
        "budget_wall_minutes": 20,
        "eight_evaluations_min": round(8 * total / 60, 2),
        "note": "An evaluation also carries the D-11 CAM jobs, which M3.8 times. "
                "This is the simulation half only, measured outside the D-17 environment.",
    }
    record["d13"]["fits_budget_simulation_only"] = record["d13"]["eight_evaluations_min"] <= 20
    record["d13"]["trigger_l_bracket"] = record["d13"]["mesh_and_solve_s"] > 60.0

    doc.saveAs(str(OUT / "lc1_solve.FCStd"))
    FreeCAD.closeDocument(doc.Name)
    record["ok"] = not record["problems"]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hmax", type=float, help="override D-24 CharacteristicLengthMax, mm")
    parser.add_argument("--region", type=float, help="override the D-24 MeshRegion size, mm")
    parser.add_argument("--curvature", type=int,
                        help="override D-24 MeshSizeFromCurvature (FreeCAD's own default is 12)")
    parser.add_argument("--no-solve", action="store_true", help="write the deck, skip ccx")
    parser.add_argument("--tag", help="write to out/lc1_solve_TAG instead, for probe runs "
                                      "that must not overwrite the M2.5 record")
    args = parser.parse_args()
    out = OUT if not args.tag else OUT.with_name(f"{OUT.name}_{args.tag}")
    try:
        record = solve(args.hmax, args.region, args.curvature, not args.no_solve, out)
    except Exception as e:  # errors as values, so a failed run still leaves evidence
        record = {"task": "M2.5", "ok": False,
                  "problems": [f"{type(e).__name__}: {e}"]}
        out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    sys.exit(0 if record.get("ok") else 2)


if __name__ == "__main__":
    main()

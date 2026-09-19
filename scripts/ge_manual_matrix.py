"""M2A.6: the manual 5 material x 4 load-case matrix on the L1 mesh, with stress, mass and displacement.

Each run is the M2A.5 setup (supports and rigid pin from M2A.4, one load case) with one
M2A.3 material card, built as its own FreeCAD document from a fresh copy of the L1 mesh
document (ge_manual_bcs.build). The deck FreeCAD writes gets one edit: `*NODE FILE`
asks for RF as well as U, so the nodal reactions are in the .frd and the force AND
moment balance can be checked. ccx is run on that deck in the run's folder.

Per run: deck checks (supports, pin, loads, material), solve status, warnings and wall
time, mass, von Mises (raw maximum and maximum outside the exclusion zones below) and
displacement maxima with locations, and the support force and moment residuals about
the pin reference point. A run is valid only if ccx exits 0 with no *ERROR, the result
blocks are complete, the deck checks pass and both residuals are within tolerance;
anything else is reported as invalid with the reason, never as zero stress.

Stress is ccx's nodal stress (extrapolated from the integration points and averaged
over the elements sharing a node); von Mises is computed from that averaged tensor.
Exclusion zones (fixed before any M2A.6 result, see docs/ge-manual-analysis-report.md):
  bolts  plan distance from a bolt axis < 10 mm, full height (fixed-patch edge and hole);
  pin    within 3 mm of the lug bore and chamfer faces (the M2A.2 pin_bore region), the
         rigid-bore boundary. Amended after the first results: the first definition (lug
         axial bounds, radius < 12.557 mm) missed nodes on the lug faces and chamfer cones;
         runs whose peak changed keep the first value as stress_first_definition.

Outputs: out/ge_manual_matrix/ (matrix.csv, matrix.json, maps/), with matrix.csv also
copied to docs/ge-manual-analysis-matrix.csv; per run
data/ge_manual/matrix/L1/<card>/<case>/ (FCStd, deck, ccx log, .dat, .frd, fields.npz;
gitignored, derived from licensed CAD). Finished runs are skipped unless --force.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_manual_matrix.py [--cards ti6al4v ...] [--cases LC1 ...] [--force]
    vendor/fem-env/bin/python scripts/ge_manual_matrix.py --report-only
"""

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
from femtools import ccxtools  # noqa: E402

from ge_manual_bcs import MESH_DIR, OUT as BCS_OUT, build, check, parse_deck, sha256  # noqa: E402
from ge_manual_loads import CASES, load_checks  # noqa: E402
from ge_manual_materials import CARDS  # noqa: E402

LEVEL = "L1"
CCX = ROOT / "vendor" / "fem-env" / "bin" / "ccx"
DATA = ROOT / "data" / "ge_manual" / "matrix" / LEVEL
OUT = ROOT / "out" / "ge_manual_matrix"
MESH_QUALITY = ROOT / "out" / "ge_manual_mesh" / "mesh-quality.json"
MATERIALS = ROOT / "out" / "ge_manual_materials" / "materials.json"

BOLT_EXCLUSION_R = 10.0            # mm, plan radius about each bolt axis (as M2's LC1)
PIN_EXCLUSION = 3.0                # mm from the lug bore and chamfer faces (M2A.2 pin_bore region)
PIN_AXIS = np.array([0.030278, -0.999542, 0.0])
PARTITIONED = ROOT / "data" / "ge_manual" / "Iteration1_partitioned.FCStd"
_PIN_MASK = {}
BALANCE_TOL = 0.005                # residual <= 0.5 % of the applied load
L_REF = 100.0                      # mm, converts between force and moment scales
SAFETY_FACTOR = 1.5                # project choice (docs/ge-manual-materials.md s5)
DISP_LIMIT = 1.1                   # x the Ti baseline, project choice


def read_mesh(text):
    """Part nodes (FreeCAD's Nall block) and C3D10 connectivity from the deck."""
    m = re.search(r"\*Node, NSET=Nall\n(.*?)\n\*", text, re.S)
    nodes = np.array([[float(t) for t in line.split(",")] for line in m.group(1).splitlines() if line.strip()])
    m = re.search(r"\*Element, TYPE=C3D10, ELSET=\S+\n(.*?)(?=\n\*|\Z)", text, re.S)
    elems = np.array([[int(t) for t in line.split(",") if t.strip()] for line in m.group(1).splitlines() if line.strip()])
    return nodes[:, 0].astype(int), nodes[:, 1:], elems[:, 1:]


def read_frd(path):
    """Nodal result blocks: {'DISP': {node: values}, 'STRESS': ..., 'FORC': ...}."""
    blocks, cur = {}, None
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith(" -4"):
                cur = line[3:].split()[0]
                blocks[cur] = {}
            elif line.startswith(" -1") and cur is not None:
                body = line[13:].rstrip("\n")
                blocks[cur][int(line[3:13])] = [float(body[i:i + 12]) for i in range(0, len(body) - 11, 12)]
            elif line.startswith(" -3"):
                cur = None
    return blocks


def von_mises(s):
    sxx, syy, szz, sxy, syz, szx = s.T
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + szx ** 2))


def pin_zone(xyz, part_rec):
    """Nodes within PIN_EXCLUSION of the bore and chamfer faces; computed once per mesh."""
    if len(xyz) not in _PIN_MASK:
        import Part
        faces = json.loads(MESH_QUALITY.read_text())["regions"]["pin_bore"]["faces"]
        doc = FreeCAD.openDocument(str(PARTITIONED))
        shape = doc.getObject("Bracket").Shape
        target = Part.makeCompound([shape.Faces[int(f[4:]) - 1] for f in faces])
        FreeCAD.closeDocument(doc.Name)
        d = xyz - np.array(part_rec["pin_reference_deck"])
        axial = d @ PIN_AXIS
        radial = np.linalg.norm(d - np.outer(axial, PIN_AXIS), axis=1)
        mask = np.zeros(len(xyz), bool)
        for i in np.flatnonzero((radial < 20) & (np.abs(axial) < 25)):
            mask[i] = target.distToShape(Part.Vertex(FreeCAD.Vector(*xyz[i])))[0] < PIN_EXCLUSION
        _PIN_MASK[len(xyz)] = mask
    return _PIN_MASK[len(xyz)]


def zones(xyz, part_rec):
    bolt = np.zeros(len(xyz), bool)
    for p in part_rec["patches"].values():
        bolt |= np.linalg.norm(xyz[:, :2] - np.array(p["axis_xy_deck"]), axis=1) < BOLT_EXCLUSION_R
    return bolt, pin_zone(xyz, part_rec)


def where(i, xyz, bolt, pin):
    return {"node_index": int(i), "xyz_deck": [round(float(v), 2) for v in xyz[i]],
            "zone": "bolt exclusion" if bolt[i] else "pin exclusion" if pin[i] else "outside exclusions"}


def field_metrics(vm, disp, xyz, part_rec):
    """Raw and outside-exclusion von Mises maxima and the displacement maximum, with locations."""
    umag = np.linalg.norm(disp, axis=1)
    bolt, pin = zones(xyz, part_rec)
    away = ~(bolt | pin)
    i_raw, i_away, i_u = int(np.nanargmax(vm)), int(np.flatnonzero(away)[np.nanargmax(vm[away])]), int(np.nanargmax(umag))
    stress = {"max_vm_raw_MPa": round(float(vm[i_raw]), 1), "raw_at": where(i_raw, xyz, bolt, pin),
              "max_vm_away_MPa": round(float(vm[i_away]), 1), "away_at": where(i_away, xyz, bolt, pin),
              "nodes_excluded": {"bolt": int(bolt.sum()), "pin": int(pin.sum()), "total_nodes": len(xyz)}}
    return stress, {"max_mm": round(float(umag[i_u]), 4), "at": where(i_u, xyz, bolt, pin)}


def rezone(runs, part_rec):
    """Recompute the field metrics from each run's saved fields with the current exclusion zones."""
    valid = [r for r in runs if r["status"] == "valid"]
    if not valid:
        return
    _, xyz, _ = read_mesh((ROOT / valid[0]["deck"]["inp"]).read_text())
    for r in valid:
        f = np.load(DATA / r["card"] / r["case"] / "fields.npz")
        stress, disp = field_metrics(f["vm"].astype(float), f["disp"].astype(float), xyz, part_rec)
        if stress["max_vm_away_MPa"] != r["stress"]["max_vm_away_MPa"] and "stress_first_definition" not in r:
            r["stress_first_definition"] = {k: r["stress"][k] for k in ("max_vm_away_MPa", "away_at")}
        r["stress"], r["displacement"] = stress, disp
        (DATA / r["card"] / r["case"] / "result.json").write_text(json.dumps(r, indent=2))


def run_one(card, case_name, part_rec, force):
    work = DATA / card / case_name
    result_path = work / "result.json"
    if result_path.exists() and not force:
        return json.loads(result_path.read_text())
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    case, c = CASES[case_name], CARDS[card]
    job = f"{card}_{case_name}"
    rec = {"card": card, "material": c["name"], "role": c["role"], "case": case_name, "title": case["title"],
           "applied_force_N": list(case["force"]), "applied_moment_Nmm": list(case["moment"]), "problems": []}

    doc, part, analysis, solver = build(LEVEL, part_rec, case, card)
    fcstd = work / f"Iteration1_{card}_{case_name}_{LEVEL}.FCStd"
    doc.saveAs(str(fcstd))
    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.write_inp_file()
    text = Path(fea.inp_file_name).read_text()
    if text.count("*NODE FILE\nU\n") != 1:
        rec["problems"].append("deck has no single '*NODE FILE / U' block to extend with RF")
    text = text.replace("*NODE FILE\nU\n", "*NODE FILE\nU, RF\n", 1)
    inp = work / f"{job}.inp"
    inp.write_text(text)
    chk = check(LEVEL, part_rec, doc, part, case_name, inp)
    FreeCAD.closeDocument(doc.Name)
    lc = load_checks(chk, case, part_rec["pin_reference_deck"])
    elastic = re.search(r"\*ELASTIC\n([^\n]+)", text)
    e_nu = [float(v) for v in elastic.group(1).split(",")] if elastic else [math.nan, math.nan]
    deck_ok = {"supports": all(s["deck_equals_face_nodes"] for s in chk["supports"].values()),
               "pin": chk["pin"]["deck_equals_bore_nodes"], "no_extra_restraints": not chk["extra_restraints"],
               "loads": all(lc.values()),
               "material": math.isclose(e_nu[0], c["youngs_mpa"], rel_tol=1e-9) and math.isclose(e_nu[1], c["poisson"], abs_tol=1e-9)}
    rec["deck"] = {"fcstd": str(fcstd.relative_to(ROOT)), "inp": str(inp.relative_to(ROOT)), "inp_sha256": sha256(inp),
                   "elastic_line": elastic.group(1) if elastic else None, "checks": deck_ok}
    rec["problems"] += [f"deck check failed: {k}" for k, v in deck_ok.items() if not v]

    t = time.perf_counter()
    proc = subprocess.run([str(CCX), "-i", job], cwd=work, capture_output=True, text=True)
    rec["wall_s"] = round(time.perf_counter() - t, 1)
    log = proc.stdout + proc.stderr
    (work / f"{job}.log").write_text(log)
    rec["ccx_exit"] = proc.returncode
    rec["warnings"] = sorted({line.strip() for line in log.splitlines() if "*WARNING" in line})
    errors = sorted({line.strip() for line in log.splitlines() if "*ERROR" in line})
    if proc.returncode != 0:
        rec["problems"].append(f"ccx exit {proc.returncode}")
    rec["problems"] += errors
    frd = work / f"{job}.frd"
    rec["artifacts"] = {"log": str((work / f"{job}.log").relative_to(ROOT)), "dat": str((work / f"{job}.dat").relative_to(ROOT)),
                        "frd": str(frd.relative_to(ROOT))}

    ids, xyz, _ = read_mesh(text)
    blocks = read_frd(frd) if frd.exists() else {}
    missing = [b for b in ("DISP", "STRESS", "FORC") if b not in blocks or not blocks[b]]
    if missing:
        rec["problems"].append(f"result blocks missing: {missing}")
    else:
        disp = np.array([blocks["DISP"].get(n, [math.nan] * 3)[:3] for n in ids])
        stress = np.array([blocks["STRESS"].get(n, [math.nan] * 6)[:6] for n in ids])
        if np.isnan(disp).any() or np.isnan(stress).any():
            rec["problems"].append("result blocks do not cover every part node")
        vm = von_mises(stress)
        rec["stress"], rec["displacement"] = field_metrics(vm, disp, xyz, part_rec)
        np.savez_compressed(work / "fields.npz", vm=vm.astype(np.float32), disp=disp.astype(np.float32))

        nsets, *_ = parse_deck(text)
        fixed = sorted(set().union(*(nsets[f"Fixed_{b}"] for b in part_rec["patches"])))
        index = {n: i for i, n in enumerate(ids)}
        rf = np.array([blocks["FORC"].get(n, [math.nan] * 3)[:3] for n in fixed])
        r = xyz[[index[n] for n in fixed]] - np.array(part_rec["pin_reference_deck"])
        F, M = np.array(case["force"]), np.array(case["moment"])
        res_f = rf.sum(axis=0) + F
        res_m = np.cross(r, rf).sum(axis=0) + M
        f_ref = max(np.linalg.norm(F), np.linalg.norm(M) / L_REF)
        m_ref = max(np.linalg.norm(M), np.linalg.norm(F) * L_REF)
        rec["balance"] = {"origin": "pin reference point", "fixed_nodes": len(fixed),
                          "sum_reaction_force_N": np.round(rf.sum(axis=0), 3).tolist(),
                          "sum_reaction_moment_Nmm": np.round(np.cross(r, rf).sum(axis=0), 1).tolist(),
                          "force_residual_N": np.round(res_f, 3).tolist(), "moment_residual_Nmm": np.round(res_m, 1).tolist(),
                          "force_residual_pct": round(100 * np.linalg.norm(res_f) / f_ref, 4),
                          "moment_residual_pct": round(100 * np.linalg.norm(res_m) / m_ref, 4)}
        rec["balance"]["within_tolerance"] = bool(max(rec["balance"]["force_residual_pct"],
                                                      rec["balance"]["moment_residual_pct"]) <= 100 * BALANCE_TOL)
        if not rec["balance"]["within_tolerance"]:
            rec["problems"].append("reaction balance outside tolerance")
    rec["status"] = "valid" if not rec["problems"] else "INVALID"
    result_path.write_text(json.dumps(rec, indent=2))
    return rec


def screening(runs):
    """Mass, yield/SF margins and displacement against the Ti baseline, per run."""
    masses = json.loads(MATERIALS.read_text())["cards"]
    ti = {r["case"]: r for r in runs if r["card"] == "ti6al4v" and r["status"] == "valid"}
    for r in runs:
        c = CARDS[r["card"]]
        r["mass_g"] = masses[r["card"]]["mass_g"]
        r["yield_MPa"] = c["yield_mpa"]
        if r["status"] != "valid":
            continue
        s = r["stress"]
        s["sf_raw"] = round(c["yield_mpa"] / s["max_vm_raw_MPa"], 3)
        s["sf_away"] = round(c["yield_mpa"] / s["max_vm_away_MPa"], 3)
        s["yield_exceeded_raw"] = s["max_vm_raw_MPa"] > c["yield_mpa"]
        s["yield_exceeded_away"] = s["max_vm_away_MPa"] > c["yield_mpa"]
        s["meets_sf_away"] = s["sf_away"] >= SAFETY_FACTOR
        base = ti.get(r["case"])
        if base:
            ratio = r["displacement"]["max_mm"] / base["displacement"]["max_mm"]
            r["displacement"]["ratio_to_ti"] = round(ratio, 3)
            r["displacement"]["within_1p1_ti"] = ratio <= DISP_LIMIT + 1e-9


def render_maps(runs, part_rec):
    import pyvista as pv

    first = next(r for r in runs if r["status"] == "valid")
    ids, xyz, conn = read_mesh((ROOT / first["deck"]["inp"]).read_text())
    index = np.full(ids.max() + 1, -1)
    index[ids] = np.arange(len(ids))
    cells = np.c_[np.full(len(conn), 10), index[conn]].ravel()
    grid = pv.UnstructuredGrid(cells, np.full(len(conn), pv.CellType.QUADRATIC_TETRA), xyz)
    focal = xyz.mean(axis=0)
    cams = {"iso (+x, +y, +z)": [tuple(focal + 400 * np.array([1, 1, 1]) / 3 ** 0.5), tuple(focal), (0, 0, 1)],
            "lug side (-x, -y, +z)": [tuple(focal + 400 * np.array([-1, -0.8, 0.6]) / 1.428), tuple(focal), (0, 0, 1)]}
    maps = OUT / "maps"
    maps.mkdir(parents=True, exist_ok=True)
    ranges = {}
    for case in CASES:
        valid = [r for r in runs if r["case"] == case and r["status"] == "valid"]
        if valid:
            ranges[case] = {"vm_max_MPa": max(r["stress"]["max_vm_away_MPa"] for r in valid),
                            "disp_max_mm": max(r["displacement"]["max_mm"] for r in valid)}
            ranges[case]["deformation_scale"] = round(8.0 / ranges[case]["disp_max_mm"], 1)
    for r in runs:
        if r["status"] != "valid":
            continue
        f = np.load(DATA / r["card"] / r["case"] / "fields.npz")
        rng = ranges[r["case"]]
        g = grid.copy()
        g.point_data["von Mises (MPa)"] = f["vm"]
        g.point_data["displacement (mm)"] = np.linalg.norm(f["disp"], axis=1)
        surf = g.extract_surface(algorithm="dataset_surface", nonlinear_subdivision=1)
        g.point_data["u"] = f["disp"]
        warped = g.warp_by_vector("u", factor=rng["deformation_scale"]).extract_surface(algorithm="dataset_surface", nonlinear_subdivision=1)
        p = pv.Plotter(off_screen=True, window_size=(1800, 1400), shape=(2, 2))
        for row, (field, mesh, clim, extra) in enumerate((
                ("von Mises (MPa)", surf, [0, rng["vm_max_MPa"]], {"above_color": "magenta"}),
                ("displacement (mm)", warped, [0, rng["disp_max_mm"]], {}))):
            for col, (cam_name, cam) in enumerate(cams.items()):
                p.subplot(row, col)
                p.set_background("white")
                p.add_mesh(mesh, scalars=field, clim=clim, cmap="viridis", show_edges=False, **extra,
                           scalar_bar_args={"title": field, "color": "black", "fmt": "%.3g", "n_labels": 6, "vertical": True,
                                            "position_x": 0.86, "position_y": 0.15, "height": 0.6,
                                            "title_font_size": 14, "label_font_size": 12})
                if row == 0:
                    for key, color in (("raw_at", "red"), ("away_at", "black")):
                        p.add_mesh(pv.Sphere(radius=2.0, center=r["stress"][key]["xyz_deck"]), color=color)
                p.camera_position = cam
                p.enable_parallel_projection()
                p.camera.parallel_scale = 115
                p.add_axes(color="black")
                if row == 0:
                    note = (f"stress, undeformed; common {r['case']} range 0-{rng['vm_max_MPa']:.0f} MPa "
                            f"(max outside exclusions over 5 materials); magenta = above range\n"
                            f"raw max {r['stress']['max_vm_raw_MPa']:.0f} MPa (red, {r['stress']['raw_at']['zone']}); "
                            f"outside exclusions {r['stress']['max_vm_away_MPa']:.0f} MPa (black)")
                else:
                    note = (f"displacement magnitude, deformed x{rng['deformation_scale']}; common {r['case']} range "
                            f"0-{rng['disp_max_mm']:.3f} mm; max {r['displacement']['max_mm']:.4f} mm")
                p.add_text(f"{r['material']} | {r['case']} {r['title']} | {cam_name}\n{note}", font_size=10, color="black")
        png = maps / f"{r['card']}_{r['case']}.png"
        p.screenshot(str(png))
        p.close()
        r["artifacts"]["map"] = str(png.relative_to(ROOT))
    return ranges


def write_report(runs, ranges):
    mq = json.loads(MESH_QUALITY.read_text())
    part = json.loads((BCS_OUT / "partition.json").read_text())
    ident = {"geometry": part["partitioned"], "geometry_sha256": part["partitioned_sha256"],
             "mesh": f"{LEVEL} connectivity {mq['levels'][LEVEL]['connectivity_sha256']}"}
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["geometry_sha256", "mesh_id", "material", "role", "lc", "status", "problems", "mass_g",
            "max_vm_raw_MPa", "raw_peak_location_deck", "raw_peak_zone", "max_vm_away_MPa", "away_peak_location_deck",
            "max_disp_mm", "displacement_location_deck", "disp_ratio_to_ti", "yield_MPa", "sf_raw", "sf_away",
            "yield_exceeded_raw", "yield_exceeded_away", "meets_sf_1p5_away", "force_residual_N", "force_residual_pct",
            "moment_residual_Nmm", "moment_residual_pct", "wall_s", "ccx_warnings", "deck", "frd", "map"]
    with open(OUT / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in runs:
            ok = r["status"] == "valid"
            s, d, b = r.get("stress", {}), r.get("displacement", {}), r.get("balance", {})
            w.writerow([ident["geometry_sha256"], ident["mesh"], r["material"], r["role"], r["case"], r["status"],
                        "; ".join(r["problems"]), r["mass_g"],
                        s.get("max_vm_raw_MPa") if ok else "", s.get("raw_at", {}).get("xyz_deck") if ok else "",
                        s.get("raw_at", {}).get("zone") if ok else "", s.get("max_vm_away_MPa") if ok else "",
                        s.get("away_at", {}).get("xyz_deck") if ok else "", d.get("max_mm") if ok else "",
                        d.get("at", {}).get("xyz_deck") if ok else "", d.get("ratio_to_ti", "") if ok else "",
                        r["yield_MPa"], s.get("sf_raw", "") if ok else "", s.get("sf_away", "") if ok else "",
                        s.get("yield_exceeded_raw", "") if ok else "", s.get("yield_exceeded_away", "") if ok else "",
                        s.get("meets_sf_away", "") if ok else "", b.get("force_residual_N", ""),
                        b.get("force_residual_pct", ""), b.get("moment_residual_Nmm", ""), b.get("moment_residual_pct", ""),
                        r.get("wall_s", ""), len(r.get("warnings", [])), r["deck"]["inp"], r["artifacts"]["frd"],
                        r["artifacts"].get("map", "")])
    governing = {}
    for card in CARDS:
        valid = [r for r in runs if r["card"] == card and r["status"] == "valid"]
        if valid:
            gs = max(valid, key=lambda r: r["stress"]["max_vm_away_MPa"])
            gd = max(valid, key=lambda r: r["displacement"]["max_mm"])
            governing[card] = {"stress_case": gs["case"], "max_vm_away_MPa": gs["stress"]["max_vm_away_MPa"],
                               "displacement_case": gd["case"], "max_disp_mm": gd["displacement"]["max_mm"],
                               "valid_runs": len(valid)}
    report = {**ident, "freecad_version": ".".join(FreeCAD.Version()[:3]),
              "ccx": subprocess.run([str(CCX), "-v"], capture_output=True, text=True).stdout.strip(),
              "exclusions": {"bolt_plan_radius_mm": BOLT_EXCLUSION_R,
                             "pin_distance_to_bore_and_chamfer_faces_mm": PIN_EXCLUSION,
                             "pin_faces": json.loads(MESH_QUALITY.read_text())["regions"]["pin_bore"]["faces"],
                             "first_definition": "pin: 11.1125 <= |axial| <= 17.4625 mm and radius < 12.557 mm"},
              "balance_tolerance_pct": 100 * BALANCE_TOL, "l_ref_mm": L_REF, "safety_factor": SAFETY_FACTOR,
              "displacement_limit_x_ti": DISP_LIMIT, "legend_ranges": ranges, "governing": governing,
              "valid_runs": sum(r["status"] == "valid" for r in runs), "runs": runs}
    (OUT / "matrix.json").write_text(json.dumps(report, indent=2, default=float))
    shutil.copyfile(OUT / "matrix.csv", ROOT / "docs" / "ge-manual-analysis-matrix.csv")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", nargs="+", choices=list(CARDS), default=list(CARDS))
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    part_rec = json.loads((BCS_OUT / "partition.json").read_text())
    if not args.report_only:
        for card in args.cards:
            for case in args.cases:
                r = run_one(card, case, part_rec, args.force)
                print(card, case, r["status"], r.get("wall_s"), json.dumps(r.get("stress", {}).get("max_vm_away_MPa")),
                      r.get("displacement", {}).get("max_mm"), r.get("balance", {}).get("force_residual_pct"),
                      r.get("balance", {}).get("moment_residual_pct"), r["problems"], flush=True)
    runs = [json.loads(p.read_text()) for card in CARDS for case in CASES
            if (p := DATA / card / case / "result.json").exists()]
    rezone(runs, part_rec)
    screening(runs)
    ranges = render_maps(runs, part_rec)
    report = write_report(runs, ranges)
    print("runs on disk:", len(runs), "valid:", report["valid_runs"], "governing:", json.dumps(report["governing"]))


if __name__ == "__main__":
    main()

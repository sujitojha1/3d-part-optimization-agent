"""M3.4: read one solved ge_bracket run back as mass, stress, displacement and peak region.

`read_result(run_dir, lc)` is the `read_result` contract of requirements
section 5. It reads only what `ge_bracket_analysis.run` left on disk:

    ccx/<job>.frd     nodes, C3D10 elements, displacement and stress (parsed here)
    ccx/<job>.dat     each support's reaction total
    d06_elsets.inp    the D-06 label of every element (element-centroid membership, M2.4)
    candidate.json    parameters, CAD volume, bolt axes

and returns validity, `mass_g`, `max_vm` and `max_disp` with units, the peak
region as one D-06 label, and the element count by type. It needs numpy and
nothing else: no FreeCAD, no mesher, no solver, so a stored run can be read
again with all three disabled.

What the numbers are:

- `mass_g`: CAD solid volume x the record's density, for the full part. The
  meshed volume is a cross-check on it, not a second measurement.
- `max_vm`: the largest nodal von Mises outside the support zone the load-case
  record fixes about each bolt axis. `raw_max_vm` is the largest anywhere, kept
  and flagged: the fixed bolt-hole faces are a singularity.
- `max_disp`: the largest nodal displacement magnitude.
- `peak_region`: the D-06 label of the largest von Mises outside the record's
  wider region-scoring zone (owner, 2026-09-22, docs/m2-exchange.md section 4).
  It is the truth a region claim is scored against, never the stress check.

A node's label is the label its elements agree on; a node on a region boundary
has none, and a peak there makes the result invalid rather than guessed.

Anything that makes a number untrustworthy makes the result `invalid`
(REQ-VER-004): a missing file, a non-finite or all-zero field, element sets
that do not partition the mesh, reactions that do not balance the load, or a
meshed volume far from the CAD volume.

Run the check with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/ge_bracket_result.py --check [--no-solve]

It solves the baseline and one material-only variant, reads both back, compares
the reader with M2.5's record (FreeCAD's own .frd loader) when out/lc1_solve
exists, and writes out/ge_bracket_result/result_check.json. Exit 0 when every
check passes, 2 otherwise.
"""

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "ge_bracket_result"

# CalculiX .frd element type codes (cgx manual, "Element Types").
FRD_TYPES = {1: "C3D8", 2: "C3D6", 3: "C3D4", 4: "C3D20", 5: "C3D15", 6: "C3D10",
             7: "S3", 8: "S6", 9: "S4", 10: "S8", 11: "B31", 12: "B32"}
CORNERS = 4  # a C3D10's first four nodes are its corners, in the .frd as in the deck

# REQ-VER-006's balance, as M2.5 applied it.
REACTION_ANGLE_DEG = 0.1
REACTION_MAGNITUDE_PCT = 0.5
# A gross-error guard on the mass input, not OD-C's mass tolerance (still open).
MESH_VS_CAD_PCT = 1.0


def _floats(text, width=12):
    out = []
    for i in range(0, len(text) - width + 1, width):
        try:
            out.append(float(text[i:i + width]))
        except ValueError:  # Fortran overflow stars, or an empty field
            out.append(float("nan"))
    return out


def parse_frd(path):
    """Nodes, elements and the DISP and STRESS blocks of a CalculiX ASCII .frd."""
    node_ids, xyz, elem_ids, elem_types, conn = [], [], [], [], []
    blocks, mode, rows = {}, None, None
    with open(path, errors="replace") as f:
        for line in f:
            key = line[:3]
            if key == " -1":
                if mode == "nodes":
                    node_ids.append(int(line[3:13]))
                    xyz.append(_floats(line[13:].rstrip("\n"))[:3])
                elif mode == "elements":
                    elem_ids.append(int(line[3:13]))
                    elem_types.append(int(line[13:18]))
                    conn.append([])
                elif mode == "result" and rows is not None:
                    rows[0].append(int(line[3:13]))
                    rows[1].append(_floats(line[13:].rstrip("\n")))
            elif key == " -2" and mode == "elements":
                conn[-1] += [int(v) for v in line[3:].split()]
            elif key == " -4":
                name = line[5:13].strip()
                mode = "result"
                rows = blocks.setdefault(name, ([], [])) if name in ("DISP", "STRESS") else None
            elif key == " -3":
                mode = None
            elif line.startswith("    2C"):
                mode = "nodes"
            elif line.startswith("    3C"):
                mode = "elements"
    return {"node_ids": np.array(node_ids, dtype=np.int64), "xyz": np.array(xyz, dtype=float),
            "elem_ids": np.array(elem_ids, dtype=np.int64),
            "elem_types": np.array(elem_types, dtype=np.int64), "conn": conn,
            "blocks": {k: (np.array(ids, dtype=np.int64), np.array(vals, dtype=float))
                       for k, (ids, vals) in blocks.items()}}


def read_elsets(path):
    """Region -> element ids, from the one-*ELSET-per-region include M2.4 writes."""
    sets, name = {}, None
    for line in Path(path).read_text().splitlines():
        if line.startswith("**"):
            continue
        m = re.match(r"\*ELSET\s*,\s*ELSET\s*=\s*(\S+)", line, re.I)
        if m:
            name = m.group(1)
            sets[name] = []
        elif name is not None:
            sets[name] += [int(v) for v in line.replace(",", " ").split()]
    return sets


def reactions(dat, nset):
    """Total reaction force on one node set, from ccx's *NODE PRINT totals."""
    m = re.findall(rf"total force \(fx,fy,fz\) for set {nset.upper()} and time\s+\S+\s*\n\s*\n?\s*"
                   r"(\S+)\s+(\S+)\s+(\S+)", dat)
    return [float(v) for v in m[-1]] if m else None


def load(run_dir):
    """Everything `summarise` needs, read from one run directory: (data, problems)."""
    run_dir = Path(run_dir)
    data, problems = {}, []
    frds = sorted((run_dir / "ccx").glob("*.frd"))
    paths = {"frd": frds[0] if len(frds) == 1 else None,
             "elsets": run_dir / "d06_elsets.inp", "candidate": run_dir / "candidate.json"}
    paths["dat"] = paths["frd"].with_suffix(".dat") if paths["frd"] else None
    for name, path in paths.items():
        if path is None or not path.exists() or path.stat().st_size == 0:
            problems.append(f"missing output: {name}")
    if problems:
        return data, problems
    data.update(parse_frd(paths["frd"]))
    data["elsets"] = read_elsets(paths["elsets"])
    data["dat"] = paths["dat"].read_text(errors="replace")
    data["candidate"] = json.loads(paths["candidate"].read_text())
    data["frd"] = paths["frd"].name
    return data, problems


def _invalid(problems, **extra):
    return {"validity": "invalid", "problems": problems, "mass_g": None, "max_vm": None,
            "max_disp": None, "peak_region": None, "contour_png": None, **extra}


def summarise(data, lc):
    """The `read_result` response from loaded data and the load-case record."""
    problems = []
    cand = data["candidate"]
    ids, xyz = data["node_ids"], data["xyz"]
    counts = {FRD_TYPES.get(int(t), f"frd_type_{int(t)}"): int(n)
              for t, n in zip(*np.unique(data["elem_types"], return_counts=True))}
    base = {"element_counts_by_type": counts, "nodes": int(len(ids))}
    if set(counts) != {"C3D10"}:
        return _invalid([f"element types {counts}, not C3D10 alone"], **base)
    for name in ("DISP", "STRESS"):
        if name not in data["blocks"] or not np.array_equal(data["blocks"][name][0], ids):
            return _invalid([f"{name} block missing or not on the mesh's nodes"], **base)
    disp, stress = data["blocks"]["DISP"][1][:, :3], data["blocks"]["STRESS"][1][:, :6]

    conn = np.array(data["conn"], dtype=np.int64)
    row = np.full(int(ids.max()) + 1, -1, dtype=np.int64)
    row[ids] = np.arange(len(ids))
    conn_rows = row[conn]
    used = np.zeros(len(ids), dtype=bool)
    used[conn_rows.ravel()] = True  # reference nodes of a rigid body are not part of the part

    if not (np.isfinite(disp[used]).all() and np.isfinite(stress[used]).all()):
        return _invalid(["non-finite displacement or stress"], **base)
    sxx, syy, szz, sxy, syz, szx = stress.T
    vm = np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                 + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))
    mag = np.linalg.norm(disp, axis=1)
    vm[~used], mag[~used] = -1.0, -1.0
    if vm.max() <= 0.0 or mag.max() <= 0.0:  # ccx exits 0 with this under SecondOrderLinear
        return _invalid(["all-zero stress or displacement field"], **base)

    # D-06 labels: the stored element sets must partition the mesh.
    regions = list(data["elsets"])
    label = np.full(int(data["elem_ids"].max()) + 1, -1, dtype=np.int64)
    doubly = 0
    for ri, region in enumerate(regions):
        members = np.array(data["elsets"][region], dtype=np.int64)
        if len(members) == 0 or members.max() >= len(label):
            problems.append(f"D-06 set {region} is empty or names elements the mesh does not have")
            continue
        doubly += int((label[members] >= 0).sum())
        label[members] = ri
    elem_label = label[data["elem_ids"]]
    if doubly or (elem_label < 0).any():
        problems.append(f"D-06 sets are not a partition: {doubly} elements in two sets, "
                        f"{int((elem_label < 0).sum())} in none")
    if problems:
        return _invalid(problems, **base)

    def at(i):
        return [round(float(v), 2) for v in xyz[i]]

    def region_of(i):
        held = np.unique(elem_label[(conn_rows == i).any(axis=1)])
        return {"labels": [regions[r] for r in held],
                "label": regions[held[0]] if len(held) == 1 else None,
                "unambiguous": len(held) == 1}

    def peak(mask, **extra):
        i = int(np.argmax(np.where(mask, vm, -1.0)))
        return {"value": round(float(vm[i]), 1), "unit": "MPa", "node": int(ids[i]),
                "at_mm": at(i), "region": region_of(i), **extra}

    bolts = np.array(cand["bolt_centres_mm"], dtype=float)
    plan = np.min(np.linalg.norm(xyz[:, None, :2] - bolts[None, :, :], axis=2), axis=1)
    zone_r = lc["support"]["zone"]["radius_mm"]
    scoring_r = lc["support"]["region_scoring_zone"]["radius_mm"]
    raw = peak(used, flag="support singularity: fixed hole faces; not a converged stress")
    governing = peak(used & (plan > zone_r), quantity=lc["stress_check"]["quantity"],
                     zone_radius_mm=zone_r)
    scoring = peak(used & (plan > scoring_r), zone_radius_mm=scoring_r,
                   use="region-hit truth only; the stress check reads max_vm")
    for name, p in (("max_vm", governing), ("peak_region", scoring)):
        if not p["region"]["unambiguous"]:
            problems.append(f"{name}: the peak node sits on a boundary between {p['region']['labels']}")

    by_region = {}
    for ri, region in enumerate(regions):
        nodes_in = np.unique(conn_rows[elem_label == ri])
        i = int(nodes_in[np.argmax(vm[nodes_in])])
        by_region[region] = {"value": round(float(vm[i]), 1), "unit": "MPa", "at_mm": at(i),
                             "elements": int((elem_label == ri).sum())}

    i_disp = int(np.argmax(mag))
    max_disp = {"value": round(float(mag[i_disp]), 4), "unit": "mm",
                "quantity": lc["displacement_limit"]["quantity"],
                "node": int(ids[i_disp]), "at_mm": at(i_disp)}

    # Mass for the full part: the CAD volume is the contract, the mesh is the check.
    a, b, c, d = (xyz[conn_rows[:, k]] for k in range(CORNERS))
    meshed = float(np.abs(np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a)).sum() / 6.0)
    volume = float(cand["volume_mm3"])
    density_g_mm3 = lc["material"]["density_kg_m3"] * 1e-6
    mesh_vs_cad = 100.0 * (meshed - volume) / volume
    if abs(mesh_vs_cad) > MESH_VS_CAD_PCT:
        problems.append(f"meshed volume is {mesh_vs_cad:+.2f} % off the CAD volume")
    mass = {"mass_g": round(volume * density_g_mm3, 2), "unit": "g", "model_extent": lc["model_extent"],
            "volume_mm3": round(volume, 3), "density_g_mm3": density_g_mm3,
            "source": f"CAD solid volume x {lc['material']['name']} density from the load-case record",
            "meshed_volume_mm3": round(meshed, 3), "mesh_vs_cad_pct": round(mesh_vs_cad, 3)}

    per = {name: reactions(data["dat"], f"Fixed_{name}") for name in lc["support"]["predicates"]}
    load = np.array(lc["load"]["vector_n"], dtype=float)
    react = {"by_support_n": {k: [round(c, 1) for c in v] for k, v in per.items() if v is not None},
             "total_n": None, "angle_deg": None, "magnitude_error_pct": None}
    if any(v is None for v in per.values()):
        problems.append("no reaction total in the .dat for " + str([k for k, v in per.items() if v is None]))
    else:
        total = np.sum(list(per.values()), axis=0)
        cos = float(np.dot(-total, load) / (np.linalg.norm(total) * np.linalg.norm(load)))
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
        error = 100.0 * (np.linalg.norm(total) - np.linalg.norm(load)) / np.linalg.norm(load)
        react.update(total_n=[round(float(v), 2) for v in total], angle_deg=round(angle, 4),
                     magnitude_error_pct=round(float(error), 4))
        if angle > REACTION_ANGLE_DEG or abs(error) > REACTION_MAGNITUDE_PCT:
            problems.append(f"reactions {react['total_n']} do not balance the load {load.tolist()}")

    return {"validity": "invalid" if problems else "valid", "problems": problems,
            "load_case": lc["name"], "parameters_mm": cand["parameters_mm"],
            "mass_g": mass["mass_g"], "mass": mass,
            "max_vm": governing, "raw_max_vm": raw, "max_disp": max_disp,
            "peak_region": scoring["region"]["label"], "peak_region_basis": scoring,
            "max_vm_by_region": by_region, "reactions": react,
            "contour_png": None,  # M3.7 renders it
            "frd": data["frd"], **base}


def read_result(run_dir, lc):
    """The `read_result` response for one run directory. Never raises on a bad run."""
    data, problems = load(run_dir)
    if problems:
        return _invalid(problems)
    try:
        return summarise(data, lc)
    except Exception as e:  # errors as values: an unreadable result is an invalid one
        return _invalid([f"{type(e).__name__}: {e}"])


def check(solve):
    """Solve and read back the baseline and a material-only variant; break the result on purpose."""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    import ge_bracket_analysis as ga
    from parts import ge_bracket as gb

    lc = ga.load_case()
    baseline = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    # Al 7075-T6 by handbook values: only the card moves, so only the response may.
    soft = copy.deepcopy(lc)
    soft["material"].update(name="Al 7075-T6", youngs_mpa=71700, poisson=0.33, density_kg_m3=2810)
    report, checks = {"task": "M3.4", "runs": {}}, {}

    results = {}
    for label, case in (("baseline", lc), ("material_only", soft)):
        run_dir = OUT / label
        if solve:
            run = ga.run(baseline, case, run_dir)
            print(f"{label:16} run {run['status']:10} {run['timings_s']}  {run['diagnostic']}", flush=True)
        results[label] = read_result(run_dir, case)
        r = results[label]
        report["runs"][label] = r
        print(f"{label:16} {r['validity']:8} mass {r['mass_g']} g  max_vm "
              f"{(r['max_vm'] or {}).get('value')} MPa  max_disp {(r['max_disp'] or {}).get('value')} mm  "
              f"peak_region {r['peak_region']}  {r['problems']}", flush=True)
    base, alt = results["baseline"], results["material_only"]
    checks["baseline_valid"] = base["validity"] == "valid"
    checks["contract_fields_present"] = all(
        base.get(k) is not None for k in ("mass_g", "max_vm", "max_disp", "peak_region")) \
        and base["max_vm"]["unit"] == "MPa" and base["max_disp"]["unit"] == "mm"
    if checks["baseline_valid"] and alt["validity"] == "valid":
        ratio = alt["max_disp"]["value"] / base["max_disp"]["value"]
        report["material_only"] = {
            "disp_ratio": round(ratio, 4),
            "modulus_ratio": round(lc["material"]["youngs_mpa"] / soft["material"]["youngs_mpa"], 4),
            "max_vm_change_pct": round(100 * (alt["max_vm"]["value"] / base["max_vm"]["value"] - 1), 2)}
        # The sanity check the task names: a material change must not move the mesh.
        checks["counts_unchanged_by_material"] = (
            alt["element_counts_by_type"] == base["element_counts_by_type"]
            and alt["nodes"] == base["nodes"])
        checks["mass_follows_density"] = math.isclose(
            alt["mass_g"] / base["mass_g"],
            soft["material"]["density_kg_m3"] / lc["material"]["density_kg_m3"], rel_tol=1e-4)
        checks["displacement_follows_modulus"] = abs(
            ratio / report["material_only"]["modulus_ratio"] - 1) < 0.02

    # Against M2.5's record, which reads the same kind of .frd with FreeCAD's own loader.
    m25 = ROOT / "out" / "lc1_solve"
    if (m25 / "result.json").exists() and (m25 / "ccx").exists():
        old = json.loads((m25 / "result.json").read_text())
        data, problems = load(m25) if (m25 / "candidate.json").exists() else ({}, ["no candidate.json"])
        if problems:  # an M2.5 run predates candidate.json; supply what it holds
            frd = sorted((m25 / "ccx").glob("*.frd"))[0]
            data = {**parse_frd(frd), "elsets": read_elsets(m25 / "d06_elsets.inp"),
                    "dat": frd.with_suffix(".dat").read_text(), "frd": frd.name,
                    "candidate": {"parameters_mm": old["geometry"]["parameters_mm"],
                                  "volume_mm3": old["mass"]["volume_mm3"],
                                  "bolt_centres_mm": [list(c) for c in gb.BOLT_CENTRES]}}
        mine, theirs = summarise(data, lc), old["result"]
        pairs = {
            "mass_g": (mine["mass_g"], old["mass"]["grams"]),
            "meshed_volume_mm3": (mine["mass"]["meshed_volume_mm3"], old["mass"]["meshed_volume_mm3"]),
            "max_vm": (mine["max_vm"]["value"], theirs["peak_vm_outside_support_zone"]["mpa"]),
            "max_vm_node": (mine["max_vm"]["node"], theirs["peak_vm_outside_support_zone"]["node"]),
            "max_vm_region": (mine["max_vm"]["region"]["label"],
                              theirs["peak_vm_outside_support_zone"]["region"]["label"]),
            "raw_max_vm": (mine["raw_max_vm"]["value"], theirs["raw_peak_vm"]["mpa"]),
            "max_disp": (mine["max_disp"]["value"], theirs["max_disp_mm"]),
            "max_disp_node": (mine["max_disp"]["node"], theirs["max_disp_node"]),
            "peak_region": (mine["peak_region"], theirs["peak_vm_for_region_scoring"]["region"]["label"]),
            "peak_region_value": (mine["peak_region_basis"]["value"],
                                  theirs["peak_vm_for_region_scoring"]["mpa"]),
            "reaction_total_n": (mine["reactions"]["total_n"], theirs["reaction_total_n"]),
            "by_region": ({k: v["value"] for k, v in mine["max_vm_by_region"].items()},
                          {k: v["mpa"] for k, v in theirs["peak_vm_by_region"].items()}),
            "c3d10": (mine["element_counts_by_type"].get("C3D10"), old["mesh"]["c3d10"]),
        }
        # The .frd carries coordinates to six significant figures, so the meshed
        # volume agrees to that and no further; everything else must be equal.
        report["against_m2_5"] = {
            k: {"read_result": a, "m2_5": b,
                "equal": math.isclose(a, b, rel_tol=1e-6) if k == "meshed_volume_mm3" else a == b}
            for k, (a, b) in pairs.items()}
        checks["agrees_with_freecad_loader_on_m2_5"] = all(
            v["equal"] for v in report["against_m2_5"].values())

    # REQ-VER-004 fixtures: each breaks one thing in a loaded copy of the baseline.
    data, problems = load(OUT / "baseline")
    if not problems:
        def broken(edit):
            d = dict(data, blocks=copy.deepcopy(data["blocks"]), elsets=copy.deepcopy(data["elsets"]))
            edit(d)
            try:
                return summarise(d, lc)
            except Exception as e:
                return _invalid([f"{type(e).__name__}: {e}"])

        def zero(d):
            d["blocks"]["STRESS"][1][:] = 0.0
            d["blocks"]["DISP"][1][:] = 0.0

        def nan(d):
            d["blocks"]["STRESS"][1][0, 0] = float("nan")

        def drop_set(d):
            d["elsets"].pop("pin_bore")

        def flip_reactions(d):
            d["dat"] = re.sub(r"(?m)^(\s+)(-?\d\.\d+E[+-]\d+)(\s+)(-?\d\.\d+E[+-]\d+)(\s+)(-?)(\d\.\d+E[+-]\d+)\s*$",
                              lambda m: f"{m[1]}{m[2]}{m[3]}{m[4]}{m[5]}{'' if m[6] else '-'}{m[7]}",
                              d["dat"])

        def no_reactions(d):
            d["dat"] = ""

        fixtures = {"all_zero_field": zero, "non_finite": nan, "sets_not_a_partition": drop_set,
                    "reactions_do_not_balance": flip_reactions, "no_reaction_totals": no_reactions}
        report["invalid_fixtures"] = {}
        for name, edit in fixtures.items():
            r = broken(edit)
            report["invalid_fixtures"][name] = {"validity": r["validity"], "problems": r["problems"]}
        missing = read_result(OUT / "no_such_run", lc)
        report["invalid_fixtures"]["missing_output"] = {"validity": missing["validity"],
                                                        "problems": missing["problems"]}
        checks["every_invalid_fixture_is_invalid"] = all(
            v["validity"] == "invalid" and v["problems"] for v in report["invalid_fixtures"].values())

    report.update(checks=checks, ok=bool(checks) and all(checks.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result_check.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, passed in checks.items():
        print(f"{name:44} {'ok' if passed else 'FAIL'}")
    print("ok" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", nargs="?", help="print read_result for this run directory (LC1)")
    parser.add_argument("--check", action="store_true", help="solve, read back and run the fixtures")
    parser.add_argument("--no-solve", action="store_true",
                        help="with --check: reuse the runs already under out/ge_bracket_result")
    args = parser.parse_args()
    if args.check:
        return check(not args.no_solve)
    if not args.run_dir:
        parser.error("give a run directory, or --check")
    lc = json.loads((ROOT / "parts" / "ge_bracket_lc1.json").read_text())
    result = read_result(args.run_dir, lc)
    print(json.dumps(result, indent=2))
    return 0 if result["validity"] == "valid" else 2


if __name__ == "__main__":
    sys.exit(main())

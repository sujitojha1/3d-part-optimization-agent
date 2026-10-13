"""M3.3: assemble the ge_bracket FEM analysis from a load-case record; ccxtools writes the deck.

One candidate's parameters and one load-case record in, a meshed FreeCAD
analysis and its CalculiX deck out:

    gm.mesh_candidate (M3.1 face selection, M3.2 D-24 mesh and retry)
        -> material, supports and pin load from the record -> ccxtools write_inp_file
        -> the written deck read back and checked against the record

The record is task data (parts/ge_bracket_lc1.json for LC1). What it fixes is
what M2.2 froze, and this module refuses a record it does not implement:

- units mm, N, MPa, stated in the record and on every FreeCAD quantity;
- a FreeCAD Fixed constraint on each support face, one per bolt hole, so ccx
  prints each bolt's reaction separately;
- the `rigid` pin model: one Rigid Body Constraint on the load faces, reference
  node at the load point, the load vector on its translations;
- the full model. D-23's symmetry constraint is not added, because the bolt
  pattern is not symmetric about the clevis midplane (ge-bracket-part.md
  section 7).

Nothing here writes or edits the deck. `deck_checks` only reads it: the
material line, the supports, the rigid body and the load are compared with the
record, so a deck that does not say what the task says is `unverified`. The
load-direction check (M5.4) reads the same deck.

`assemble` returns `record` with `status` "ok" or "unverified" and a
`diagnostic`, and for "ok" the open document, analysis, ccxtools object and deck
path, which the caller solves and closes.

Run with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/ge_bracket_analysis.py [--bounds]

checks the assembly at the baseline (with --bounds, at every parameter bound
too) and writes out/ge_bracket_analysis/analysis.json. Exit 0 when every check
passes, 2 otherwise.
"""

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
from FreeCAD import Vector  # noqa: E402
from femtools import ccxtools  # noqa: E402

import ge_bracket_labels as gl  # noqa: E402  the element-centroid D-06 labels (M2.4)
import ge_bracket_mesh as gm  # noqa: E402  the pipeline mesher (M3.2)
from parts import ge_bracket as gb  # noqa: E402

OUT = ROOT / "out" / "ge_bracket_analysis"
LC1_PATH = ROOT / "parts" / "ge_bracket_lc1.json"

UNITS = {"length": "mm", "force": "N", "stress": "MPa"}
TOL = 1e-6  # relative, deck value against record value


def load_case(path=LC1_PATH):
    return json.loads(Path(path).read_text())


def validate(lc):
    """Refuse a record this assembly does not implement. A bad record is a task
    error, not a verdict on the candidate, so it raises."""
    if lc.get("units") != UNITS:
        raise ValueError(f"load case units {lc.get('units')} are not {UNITS}")
    choice = lc["load"]["pin_model"]["choice"]
    if choice != "rigid":
        raise ValueError(f"pin model {choice!r} is not implemented; M2.2 chose 'rigid'")
    if lc["model_extent"] != "full":
        raise ValueError(f"model extent {lc['model_extent']!r} is not implemented; D-23 does not hold")
    unknown = [n for n in lc["support"]["predicates"] + lc["load"]["load_faces"]
               if n not in gb.PREDICATES]
    if unknown:
        raise ValueError(f"not single-face predicates of ge_bracket: {unknown}")


def add_physics(doc, part, matched, lc):
    """The record as FreeCAD objects: solver, material, one Fixed per support face, rigid pin.

    `matched` is `gb.select`'s predicate -> face indices, so every reference is
    resolved by geometry, never by a stored index.
    """
    analysis = next(o for o in doc.Objects if o.isDerivedFrom("Fem::FemAnalysis"))
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
    analysis.addObject(solver)

    mat = lc["material"]
    material = ObjectsFem.makeMaterialSolid(doc, "Material")
    card = material.Material
    card.update({"Name": mat["name"], "YoungsModulus": f"{mat['youngs_mpa']} MPa",
                 "PoissonRatio": str(mat["poisson"]), "Density": f"{mat['density_kg_m3']} kg/m^3"})
    material.Material = card
    analysis.addObject(material)

    supports = []
    for name in lc["support"]["predicates"]:
        fixed = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{name}")
        fixed.References = [(part, f"Face{matched[name][0]}")]
        analysis.addObject(fixed)
        supports.append(fixed)

    pin = ObjectsFem.makeConstraintRigidBody(doc, "Pin")
    pin.References = [(part, f"Face{matched[n][0]}") for n in lc["load"]["load_faces"]]
    pin.ReferenceNode = Vector(*lc["load"]["applied_at"])
    for axis, value in zip("XYZ", lc["load"]["vector_n"]):
        setattr(pin, f"TranslationalMode{axis}", "Load")
        setattr(pin, f"Force{axis}", f"{value} N")
    analysis.addObject(pin)
    doc.recompute()
    return analysis, solver, supports


def write_deck(analysis, solver, mesh, work):
    """ccxtools writes the deck into `work`: (fea, inp path, problems)."""
    work = Path(work)
    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    # ccxtools' own `create` only prints; an absent dir silently becomes a temp dir.
    work.mkdir(parents=True, exist_ok=True)
    fea.setup_working_dir(str(work), create=True)
    if Path(fea.working_dir).resolve() != work.resolve():
        return fea, None, [f"ccxtools redirected the working dir to {fea.working_dir}"]
    blockers = fea.check_prerequisites()
    if blockers:
        return fea, None, [f"prerequisites: {blockers}"]
    fea.write_inp_file()
    # A failed write can leave inp_file_name empty; the file on disk is what counts.
    inp = work / f"{mesh.Name}.inp"
    if not inp.exists() or inp.stat().st_size == 0:
        return fea, None, [f"ccxtools wrote no deck at {inp.name}"]
    return fea, inp, []


def _close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(b))


def deck_checks(inp, lc):
    """What the written deck says, against what the record says: (facts, problems)."""
    text = Path(inp).read_text(errors="replace")
    # The mesh is nearly all of the file and holds none of the cards below.
    cards = text[text.index("*ELSET,ELSET=MaterialSolid"):] if "*ELSET,ELSET=MaterialSolid" in text else text
    problems = []

    types = sorted(set(re.findall(r"^\*Element,\s*TYPE=(\w+)", text, re.M)))
    if types != ["C3D10"]:
        problems.append(f"element types {types}, not C3D10 alone")

    mat = lc["material"]
    elastic = re.findall(r"^\*ELASTIC[^\n]*\n\s*([^\n,]+),\s*([^\n,]+)", cards, re.M)
    elastic = [[float(e), float(nu)] for e, nu in elastic]
    if len(elastic) != 1 or not (_close(elastic[0][0], mat["youngs_mpa"])
                                 and _close(elastic[0][1], mat["poisson"])):
        problems.append(f"*ELASTIC {elastic} is not E {mat['youngs_mpa']} MPa, nu {mat['poisson']}")

    # Supports: a non-empty node set and all three translations held, per face.
    supports = {}
    held = re.findall(r"^\*BOUNDARY\n((?:[^*\n][^\n]*\n)+)", cards, re.M)
    held = sorted(line.strip() for block in held for line in block.splitlines() if line.strip())
    for name in lc["support"]["predicates"]:
        nset = f"Fixed_{name}"
        body = re.search(rf"^\*NSET,NSET={nset}\n((?:[^*\n][^\n]*\n)+)", cards, re.M)
        supports[nset] = len(re.findall(r"\d+", body.group(1))) if body else 0
        if not supports[nset]:
            problems.append(f"support node set {nset} is missing or empty")
        if not re.search(rf"^\*NODE PRINT, NSET={nset}, TOTALS=ONLY\nRF", cards, re.M):
            problems.append(f"no reaction total printed for {nset}")
    expected = sorted(f"{nset},{dof}" for nset in supports for dof in (1, 2, 3))
    if held != expected:
        problems.append(f"*BOUNDARY holds {held}, not exactly {expected}")

    # Rigid pin: reference node at the load point, and the load on that node alone.
    rigid = re.findall(r"^\*RIGID BODY, NSET=(\w+), REF NODE=(\d+), ROT NODE=(\d+)", cards, re.M)
    ref, ref_at = None, None
    if len(rigid) != 1 or rigid[0][0] != "Pin":
        problems.append(f"*RIGID BODY cards {rigid}, not one on Pin")
    else:
        ref = rigid[0][1]
        at = re.search(rf"^{ref},([^,\n]+),([^,\n]+),([^,\n]+)$", cards, re.M)
        ref_at = [float(v) for v in at.groups()] if at else None
        if ref_at is None or not all(_close(a, b) for a, b in zip(ref_at, lc["load"]["applied_at"])):
            problems.append(f"pin reference node at {ref_at}, not {lc['load']['applied_at']}")
    pin_body = re.search(r"^\*NSET,NSET=Pin\n((?:[^*\n][^\n]*\n)+)", cards, re.M)
    pin_nodes = len(re.findall(r"\d+", pin_body.group(1))) if pin_body else 0
    if not pin_nodes:
        problems.append("rigid-body node set Pin is missing or empty")

    cload, elsewhere = [0.0, 0.0, 0.0], []
    for block in re.findall(r"^\*CLOAD\n((?:[^*\n][^\n]*\n)+)", cards, re.M):
        for node, dof, value in re.findall(r"^(\d+),(\d),(\S+)$", block, re.M):
            cload[int(dof) - 1] += float(value)
            if node != ref:
                elsewhere.append(node)
    scale = max(abs(v) for v in lc["load"]["vector_n"])
    if elsewhere or any(abs(a - b) > TOL * scale for a, b in zip(cload, lc["load"]["vector_n"])):
        problems.append(f"*CLOAD sums to {cload} (nodes off the pin reference: {elsewhere}), "
                        f"not {lc['load']['vector_n']} on the reference node")

    steps = len(re.findall(r"^\*STEP", cards, re.M))
    if steps != 1 or not re.search(r"^\*STATIC", cards, re.M):
        problems.append(f"{steps} *STEP cards, or no *STATIC")
    other = sorted(set(re.findall(r"^\*(DLOAD|DSLOAD|TEMPERATURE|EQUATION|MPC|TIE|CONTACT PAIR)", cards, re.M)))
    if other:
        problems.append(f"cards the record does not declare: {other}")

    facts = {"element_types": types, "elastic": elastic, "support_nodes": supports,
             "boundary": held, "pin_nodes": pin_nodes, "pin_reference_at_mm": ref_at,
             "cload_n": cload, "steps": steps}
    return facts, problems


def assemble(params, lc, work, sizes=None, **mesh_options):
    """M3.3: mesh one candidate and write its deck for one load case.

    `sizes` and `mesh_options` go to `gm.mesh_candidate`. An unverified mesh, a
    deck ccxtools would not write, or a deck that disagrees with the record is
    "unverified" and returns no objects.
    """
    validate(lc)
    work = Path(work)
    empty = {"doc": None, "part": None, "mesh": None, "shape": None, "analysis": None,
             "solver": None, "supports": None, "fea": None, "inp": None}
    record = {"task": "M3.3", "load_case": lc["name"], "model_extent": lc["model_extent"],
              "status": "unverified", "diagnostic": "", "timings_s": {}}

    meshed = gm.mesh_candidate(params, work / "mesh", sizes, mesh_groups=True, **mesh_options)
    record["mesh"] = meshed["record"]
    record["timings_s"].update(cad=meshed["record"]["cad_seconds"],
                               mesh=meshed["record"].get("mesh_seconds", 0.0))
    if meshed["record"]["status"] != "ok":
        record["diagnostic"] = f"mesh: {meshed['record']['diagnostic']}"
        return {"record": record, **empty}
    doc, part, mesh, shape = (meshed[k] for k in ("doc", "part", "mesh", "shape"))

    matched = gb.select(shape, dict(params))[0]
    analysis, solver, supports = add_physics(doc, part, matched, lc)
    t = time.perf_counter()
    fea, inp, problems = write_deck(analysis, solver, mesh, work / "ccx")
    record["timings_s"]["write_inp"] = round(time.perf_counter() - t, 2)
    if not problems:
        record["deck"], problems = deck_checks(inp, lc)
        record["deck"].update(inp=inp.name, bytes=inp.stat().st_size)
    if problems:
        record["diagnostic"] = f"deck: {problems}"
        FreeCAD.closeDocument(doc.Name)
        return {"record": record, **empty}
    record["status"] = "ok"
    return {"record": record, "doc": doc, "part": part, "mesh": mesh, "shape": shape,
            "analysis": analysis, "solver": solver, "supports": supports, "fea": fea, "inp": inp}


def run(params, lc, work, sizes=None, **mesh_options):
    """`run_sim`'s body: assemble, label the elements, and solve with ccx.

    Leaves in `work` what `ge_bracket_result.read_result` reads without FreeCAD:
    the deck, .frd and .dat under ccx/, the D-06 element sets, and candidate.json.
    Returns the run record, also written to run.json: `status` "ok" or
    "unverified" with a `diagnostic`. A solve that fails is a value, not an error.
    """
    work = Path(work)
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    built = assemble(params, lc, work, sizes, **mesh_options)
    record = dict(built["record"], task="run_sim",
                  versions={"freecad": ".".join(FreeCAD.Version()[:3])})
    if record["status"] == "ok":
        doc, mesh, shape, fea, inp = (built[k] for k in ("doc", "mesh", "shape", "fea", "inp"))
        fm = mesh.FemMesh
        t = time.perf_counter()
        sets, partition = gl.centroid_labels(fm, gl.femmesh_groups(fm))
        gl.write_elsets(work / "d06_elsets.inp", sets)
        record["timings_s"]["labels"] = round(time.perf_counter() - t, 2)
        record["d06_partition"] = partition
        (work / "candidate.json").write_text(json.dumps({
            "parameters_mm": dict(params), "volume_mm3": shape.Volume,
            "bolt_centres_mm": [list(c) for c in gb.BOLT_CENTRES],
            "regions": list(gb.REGIONS), "load_case": lc["name"]}, indent=2) + "\n")
        fea.setup_ccx()
        record["versions"]["ccx_binary"] = str(getattr(fea, "ccx_binary", ""))
        t = time.perf_counter()
        code = fea.ccx_run()
        record["timings_s"]["ccx"] = round(time.perf_counter() - t, 2)
        FreeCAD.closeDocument(doc.Name)
        frd = inp.with_suffix(".frd")
        record["artifacts"] = {"inp": f"ccx/{inp.name}", "frd": f"ccx/{frd.name}",
                               "dat": f"ccx/{inp.with_suffix('.dat').name}",
                               "d06_elsets": "d06_elsets.inp", "candidate": "candidate.json"}
        if not partition["ok"]:
            record.update(status="unverified", diagnostic=f"D-06 labels are not a partition: {partition}")
        elif code != 0 or not frd.exists():
            record.update(status="unverified", diagnostic=f"ccx exited {code}; .frd present: {frd.exists()}")
    record["timings_s"]["total"] = round(sum(record["timings_s"].values()), 2)
    (work / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def check(bounds):
    """The assembly at the baseline (and each bound), and that the deck check reads the deck."""
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    lc = load_case()
    baseline = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    points = {"baseline": baseline}
    if bounds:
        for name, rec in gb.PARAMS.items():
            for bound in ("min", "max"):
                points[f"{name}={bound}"] = {**baseline, name: rec[bound]}

    def run(label, params, case, **kw):
        result = assemble(params, case, OUT / label.replace("=", "_"), **kw)
        r = result["record"]
        print(f"{label:28} {r['status']:10} write {r['timings_s'].get('write_inp', 0):5.2f} s  "
              f"{r['diagnostic']}", flush=True)
        return result

    report = {"task": "M3.3", "freecad_version": ".".join(FreeCAD.Version()[:3]), "points": {}}
    for label, params in points.items():
        result = run(label, params, lc)
        if result["doc"] is not None:
            FreeCAD.closeDocument(result["doc"].Name)
        report["points"][label] = result["record"]
    checks = {"every_point_ok": all(r["status"] == "ok" for r in report["points"].values())}

    # D-16's wrong-direction mutant: its own deck agrees with its own record, and
    # is caught when read against LC1. The check reads the deck, not the request.
    flipped = json.loads(json.dumps(lc))
    flipped["load"]["vector_n"] = lc["mutant_wrong_direction"]["vector_n"]
    mutant = run("flipped_load", baseline, flipped)
    checks["flipped_deck_matches_its_record"] = mutant["record"]["status"] == "ok"
    if mutant["inp"] is not None:
        against_lc1 = deck_checks(mutant["inp"], lc)[1]
        checks["flipped_deck_fails_against_lc1"] = (
            len(against_lc1) == 1 and against_lc1[0].startswith("*CLOAD"))
        softer = json.loads(json.dumps(flipped))
        softer["material"]["youngs_mpa"] = lc["material"]["youngs_mpa"] * 1e-6  # Pa read as MPa
        against_soft = deck_checks(mutant["inp"], softer)[1]
        checks["wrong_modulus_is_caught"] = any(p.startswith("*ELASTIC") for p in against_soft)
        FreeCAD.closeDocument(mutant["doc"].Name)
        report["flipped_load"] = dict(mutant["record"], against_lc1=against_lc1)

    # An unverified mesh stops the assembly before any deck is written.
    stopped = run("inverting_mesh", baseline, lc, **gm.INVERTING)
    checks["unverified_mesh_writes_no_deck"] = (
        stopped["record"]["status"] == "unverified" and stopped["inp"] is None
        and not (OUT / "inverting_mesh" / "ccx").exists())

    refused = {}
    for label, edit in {"units": lambda c: c["units"].update(stress="Pa"),
                        "pin_model": lambda c: c["load"]["pin_model"].update(choice="half_bore"),
                        "model_extent": lambda c: c.update(model_extent="half")}.items():
        bad = json.loads(json.dumps(lc))
        edit(bad)
        try:
            validate(bad)
            refused[label] = False
        except ValueError:
            refused[label] = True
    checks["unimplemented_records_refused"] = all(refused.values())

    report.update(checks=checks, ok=all(checks.values()))
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, passed in checks.items():
        print(f"{name:40} {'ok' if passed else 'FAIL'}")
    print("ok" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bounds", action="store_true",
                        help="also assemble at each parameter's min and max")
    args = parser.parse_args()
    return check(args.bounds)


if __name__ == "__main__":
    sys.exit(main())

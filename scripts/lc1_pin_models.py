"""M2.2: solve ge_bracket LC1 with each candidate pin-load model.

FreeCAD has no *DISTRIBUTING COUPLING, so SimJEB's RBE3 pin spider has no
direct equivalent. This solves the baseline under LC1 two ways and records
what each does:

- rigid: one Rigid Body Constraint on both pin-bore faces, reference node at
  the pin centre, free in x, y and every rotation, loaded in z (*RIGID BODY).
  The pin is infinitely stiff and ties both bores together.
- half_bore: a Force constraint on the upper half of each bore. The bores are
  split at the pin's horizontal plane; the force spreads by area over them.
  Its direction comes from a reference face: setting DirectionVector from
  Python is silently replaced on recompute (the load went 45 degrees off).

Every run checks the solver's total reaction on the bolt holes against the
declared load vector, the check REQ-VER-006 needs.

Both fix the four bolt-hole faces, as SimJEB's RBE2 spiders plus SPC 123456
do: every node on the hole surface held in all DOF.

Run with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/lc1_pin_models.py [--model rigid|half_bore] [--hmax MM]

Writes each model's deck and results under out/lc1/<model>/ and a summary to
out/lc1/result.json. Exit 0 when every requested model solved, 2 otherwise.
"""

import argparse
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
import Part  # noqa: E402
from FreeCAD import Vector  # noqa: E402
from femmesh.gmshtools import GmshTools  # noqa: E402
from femtools import ccxtools  # noqa: E402

from parts import ge_bracket as gb  # noqa: E402

OUT = ROOT / "out" / "lc1"
RECORD = json.loads((ROOT / "parts" / "ge_bracket_lc1.json").read_text())


def split_bores(shape):
    """Imprint the pin's horizontal plane on both bores, so each bore splits into
    upper and lower faces. The cutter lies in the empty bore, so no volume moves."""
    px, py, pz = gb.PIN
    r = gb.PIN_D / 2
    cutter = Part.makePlane(gb.PIN_D, 400, Vector(px - r, py - 200, pz))
    fused, _ = shape.generalFuse([cutter])
    (solid,) = fused.Solids
    if abs(solid.Volume - shape.Volume) > 1e-6 * shape.Volume:
        raise RuntimeError("splitting the bores changed the volume")
    return solid


def upper_bore_faces(shape):
    px, _, pz = gb.PIN
    out = []
    for i, f in enumerate(shape.Faces, 1):
        s = f.Surface
        if (isinstance(s, Part.Cylinder) and abs(s.Radius - gb.PIN_D / 2) < gb.TOL
                and math.hypot(s.Center.x - px, s.Center.z - pz) < 0.01 and f.CenterOfMass.z > pz):
            out.append(i)
    return out


def region_nodes(femmesh, shape, p, faces_by_name):
    """Surface node ids for each D-06 region, from the predicate-selected faces."""
    out = {}
    for region, names in gb.REGIONS.items():
        ids = set()
        for name in names:
            for i in faces_by_name.get(name, []):
                ids.update(femmesh.getNodesByFace(shape.Faces[i - 1]))
        out[region] = ids
    return out


def reactions(dat, nset):
    """Total reaction force on one node set, from ccx's *NODE PRINT totals. It
    opposes the applied load: a balanced model gives minus the load vector."""
    text = dat.read_text() if dat.exists() else ""
    m = re.findall(rf"total force \(fx,fy,fz\) for set {nset.upper()} and time\s+\S+\s*\n\s*\n?\s*"
                   r"(\S+)\s+(\S+)\s+(\S+)", text)
    return [float(v) for v in m[-1]] if m else None


def written_load(inp):
    """Sum of every *CLOAD value in the deck, per direction."""
    total = [0.0, 0.0, 0.0]
    for block in re.findall(r"\*CLOAD\n(.*?)(?=\n\*[A-Z]|\Z)", inp.read_text(), re.S):
        for node, dof, value in re.findall(r"^(\d+),(\d),(\S+)$", block, re.M):
            total[int(dof) - 1] += float(value)
    return total


def solve(model, hmax):
    work = OUT / model
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    p = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    shape = gb.build_shape(p)
    if model == "half_bore":
        shape = split_bores(shape)
    faces = gb.match(shape, p)  # on the split shape each bore predicate matches its pieces

    doc = FreeCAD.newDocument(f"lc1_{model}")
    part = doc.addObject("Part::Feature", "GeBracket")
    part.Shape = shape
    doc.recompute()
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
    analysis.addObject(solver)

    mat = RECORD["material"]
    material = ObjectsFem.makeMaterialSolid(doc, "Material")
    card = material.Material
    card.update({"Name": mat["name"], "YoungsModulus": f"{mat['youngs_mpa']} MPa",
                 "PoissonRatio": str(mat["poisson"]), "Density": f"{mat['density_kg_m3']} kg/m^3"})
    material.Material = card
    analysis.addObject(material)

    supports = []  # one Fixed per bolt hole, so ccx prints each bolt's reaction
    for n in RECORD["support"]["predicates"]:
        fixed = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{n}")
        fixed.References = [(part, f"Face{faces[n][0]}")]
        analysis.addObject(fixed)
        supports.append(fixed)

    fx, fy, fz = RECORD["load"]["vector_n"]
    if model == "rigid":
        pin = ObjectsFem.makeConstraintRigidBody(doc, "Pin")
        pin.References = [(part, f"Face{faces[n][0]}") for n in ("pin_bore_pos_y", "pin_bore_neg_y")]
        pin.ReferenceNode = Vector(*gb.PIN)
        for axis, value in zip("XYZ", (fx, fy, fz)):
            setattr(pin, f"TranslationalMode{axis}", "Load")
            setattr(pin, f"Force{axis}", f"{value} N")
    else:
        pin = ObjectsFem.makeConstraintForce(doc, "Pin")
        pin.References = [(part, f"Face{i}") for i in upper_bore_faces(shape)]
        pin.Force = f"{math.hypot(fx, fy, fz)} N"
        # Direction from a face whose normal is the load axis: base_top is +z.
        if (fx, fy) != (0.0, 0.0):
            raise NotImplementedError("half_bore handles loads along z only")
        pin.Direction = (part, [f"Face{faces['base_top'][0]}"])
        pin.Reversed = fz < 0
    analysis.addObject(pin)
    doc.recompute()
    if model == "half_bore":
        applied = pin.DirectionVector
        if (applied - Vector(fx, fy, fz).normalize()).Length > 1e-9:
            raise RuntimeError(f"force direction is {applied}, not the declared load")

    mesh = analysis.addObject(ObjectsFem.makeMeshGmsh(doc, "Mesh"))[0]
    mesh.Shape = part
    mesh.ElementOrder = "2nd"
    mesh.HighOrderOptimize = "Optimization"
    mesh.CharacteristicLengthMax = hmax
    mesh.CharacteristicLengthMin = 1.0
    doc.recompute()

    result = {"model": model, "ok": False, "hmax_mm": hmax, "timings_s": {}}
    t = time.perf_counter()
    err = GmshTools(mesh).create_mesh()
    doc.recompute()
    result["timings_s"]["mesh"] = round(time.perf_counter() - t, 2)
    if err:
        raise RuntimeError(f"gmsh: {err}")
    femmesh = mesh.FemMesh
    result["mesh"] = {"nodes": femmesh.NodeCount, "volumes": femmesh.VolumeCount}

    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(str(work), create=True)
    problems = fea.check_prerequisites()
    if problems:
        raise RuntimeError(f"prerequisites: {problems}")
    fea.write_inp_file()
    t = time.perf_counter()
    code = fea.ccx_run()
    result["timings_s"]["solve"] = round(time.perf_counter() - t, 2)
    if code != 0:
        raise RuntimeError(f"ccx exited {code}")
    fea.load_results()
    res = next(o for o in analysis.Group if o.isDerivedFrom("Fem::FemResultObject"))

    nodes = femmesh.Nodes
    vm = dict(zip(res.NodeNumbers, res.vonMises))
    disp = dict(zip(res.NodeNumbers, res.DisplacementVectors))
    if not vm or max(vm.values()) == 0.0:  # D-24's silent failure mode
        raise RuntimeError("all-zero stress field")

    def peak(ids):
        n = max(ids, key=vm.get)
        return {"mpa": round(vm[n], 1), "at_mm": [round(c, 2) for c in nodes[n]]}

    regions = region_nodes(femmesh, shape, p, faces)
    by_region = {r: peak(ids) for r, ids in regions.items() if ids}
    top = max(by_region, key=lambda r: by_region[r]["mpa"])
    free = set(vm) - regions["bolt_boss"]  # every node not on a boss or bolt-hole face
    outside = {r: peak(ids & free) for r, ids in regions.items() if ids & free}
    top_out = max(outside, key=lambda r: outside[r]["mpa"])
    # Support zone: every node within the boss footprint in plan, the whole
    # height. The fixed hole faces are singular (fem-geometry-preparation §13).
    zone_r = gb.BOSS_D / 2
    beyond = {n for n in vm if min(math.hypot(nodes[n].x - x, nodes[n].y - y)
                                   for x, y in gb.BOLT_CENTRES) > zone_r}
    n_beyond = max(beyond, key=vm.get)
    n_disp = max(disp, key=lambda n: disp[n].Length)
    bore_nodes = regions["pin_bore"]
    per_bolt = {f.Name[len("Fixed_"):]: reactions(work / f"{mesh.Name}.dat", f.Name) for f in supports}
    if any(v is None for v in per_bolt.values()):
        raise RuntimeError("no reaction totals in the .dat")
    rf = [sum(v[k] for v in per_bolt.values()) for k in range(3)]
    written = written_load(work / f"{mesh.Name}.inp")
    load = Vector(fx, fy, fz)
    # Direction to 0.1 degree; magnitude to 0.5 %, because FreeCAD's area
    # weighting of a face force loses about 0.12 % on this mesh.
    angle = round(math.degrees((-Vector(*rf)).getAngle(load)), 4)
    error_pct = round(100 * ((-Vector(*rf)).Length - load.Length) / load.Length, 4)
    if angle > 0.1 or abs(error_pct) > 0.5:
        raise RuntimeError(f"reactions {rf} do not balance the load {tuple(load)}")
    result.update({
        "ok": True,
        "peak_vm": {"region": top, **by_region[top]},
        "peak_vm_outside_bolt_boss": {"region": top_out, **outside[top_out]},
        "peak_vm_outside_support_zone": {"zone_radius_mm": zone_r, "mpa": round(vm[n_beyond], 1),
                                         "at_mm": [round(c, 2) for c in nodes[n_beyond]]},
        "peak_vm_by_region": by_region,
        "max_disp_mm": round(disp[n_disp].Length, 4),
        "max_disp_at_mm": [round(c, 2) for c in nodes[n_disp]],
        "pin_bore_mean_uz_mm": round(sum(disp[n].z for n in bore_nodes) / len(bore_nodes), 4),
        "reaction_total_n": [round(v, 2) for v in rf],
        "reaction_by_bolt_n": {k: [round(c, 1) for c in v] for k, v in per_bolt.items()},
        "reaction_angle_deg": angle,
        "reaction_magnitude_error_pct": error_pct,
        "written_cload_n": [round(v, 2) for v in written],
        "inp": str((work / f"{mesh.Name}.inp").relative_to(ROOT)),
    })
    FreeCAD.closeDocument(doc.Name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=("rigid", "half_bore"), action="append")
    parser.add_argument("--hmax", type=float, default=4.0, help="CharacteristicLengthMax, mm")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    runs = []
    for model in args.model or ("rigid", "half_bore"):
        try:
            runs.append(solve(model, args.hmax))
        except Exception as e:  # errors as values
            runs.append({"model": model, "ok": False, "error": f"{type(e).__name__}: {e}"})
    result = {"ok": all(r["ok"] for r in runs), "load_case": RECORD["name"], "runs": runs}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

"""M2.1: build the ge_bracket FreeCAD document and check it at every bound.

Writes parts/ge_bracket.FCStd (the kept document, promoted in M3.1), reopens
it, and drives it only through its Params spreadsheet: the baseline, then each
parameter alone at its min and at its max. At each point it checks that

- the shape is one valid solid;
- every single-face predicate matches exactly one face (REQ-OPT-008);
- every face carries exactly one D-06 region label;
- the thin sections stay at or above the 1.27 mm floor (D-05).

With --corners it also checks all 64 combinations of every parameter at its
min or max (about 80 s).

Run with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/ge_bracket_check.py [--corners]

Writes out/ge_bracket/check.json and prints a summary. Exit 0 when every point
passes, 2 otherwise.
"""

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import FreeCAD  # noqa: E402

from parts import ge_bracket as gb  # noqa: E402

DOC = ROOT / "parts" / "ge_bracket.FCStd"
OUT = ROOT / "out" / "ge_bracket"
MIN_WALL = 1.27


def faces(shape, m, names):
    return [shape.Faces[i - 1] for n in names for i in m[n]]


def gap(shape, m, a, b):
    """Smallest distance between two face sets."""
    return min(fa.distToShape(fb)[0] for fa in faces(shape, m, a) for fb in faces(shape, m, b))


def walls(shape, m, p):
    """The part's thin sections, in mm."""
    g = gb.layout(p)
    bolts = [f"bolt_hole_{i}" for i in (2, 3, 4, 5)]
    pockets = ["pocket_wall"]
    return {
        "pocket_floor": round(p["base_thickness"] - p["base_pocket_depth"], 3),
        "lug_wall": round(g["lug_r"] - gb.PIN_D / 2, 3),
        "boss_wall": round((gb.BOSS_D - gb.BOLT_HOLE_D) / 2, 3),
        "centre_hole_to_base_side": round(gap(shape, m, ["centre_hole"], ["base_side"]), 3),
        "centre_hole_to_fillet": round(gap(shape, m, ["centre_hole"], gb.REGIONS["arm_root_fillet"]), 3),
        "pocket_to_base_side": round(gap(shape, m, pockets, ["base_side"]), 3),
        "pocket_to_bolt_hole": round(gap(shape, m, pockets, bolts), 3),
    }


def check_point(doc, label, values):
    t = time.perf_counter()
    obj = gb.set_params(doc, values)
    rebuild_s = round(time.perf_counter() - t, 3)
    shape, p = obj.Shape, gb.params_of(obj)
    point = {"point": label, "params": p, "rebuild_s": rebuild_s, "problems": []}
    problems = point["problems"]
    if not shape.isValid() or len(shape.Solids) != 1:
        problems.append(f"shape valid={shape.isValid()} solids={len(shape.Solids)}")
        return point
    m = gb.match(shape, p)
    for name in gb.PREDICATES:
        if len(m[name]) != 1:
            problems.append(f"predicate {name} matches {m[name]}")
    for name in ("base_side", "pocket_wall"):  # fillet_corner may be empty
        if not m[name]:
            problems.append(f"set rule {name} matches nothing")
    _, unlabelled, overlap = gb.region_of_faces(shape, p)
    if unlabelled:
        problems.append(f"faces with no region: {unlabelled}")
    if overlap:
        problems.append(f"faces in two regions: {overlap}")
    if not problems:
        point["walls_mm"] = walls(shape, m, p)
        thin = {k: v for k, v in point["walls_mm"].items() if v < MIN_WALL}
        if thin:
            problems.append(f"under {MIN_WALL} mm: {thin}")
    point.update({"faces": len(shape.Faces), "volume_mm3": round(shape.Volume, 1),
                  "mass_g": round(shape.Volume * gb.DENSITY_G_MM3, 1)})
    point["ok"] = not problems
    return point


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corners", action="store_true", help="also check all 2^6 bound corners")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    doc = gb.make_document()
    doc.saveAs(str(DOC))
    FreeCAD.closeDocument(doc.Name)
    doc = FreeCAD.openDocument(str(DOC))  # prove the saved document rebuilds

    baseline = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    points = [check_point(doc, "baseline", baseline)]
    for name, rec in gb.PARAMS.items():
        for bound in ("min", "max"):
            points.append(check_point(doc, f"{name}={bound}", {**baseline, name: rec[bound]}))
    if args.corners:
        for combo in itertools.product(("min", "max"), repeat=len(gb.PARAMS)):
            values = {n: gb.PARAMS[n][b] for n, b in zip(gb.PARAMS, combo)}
            points.append(check_point(doc, "corner " + " ".join(b[1] for b in combo), values))
    gb.set_params(doc, baseline)
    FreeCAD.closeDocument(doc.Name)

    result = {"ok": all(p["ok"] for p in points), "document": str(DOC.relative_to(ROOT)),
              "freecad": ".".join(FreeCAD.Version()[:3]), "points": points}
    (OUT / "check.json").write_text(json.dumps(result, indent=2) + "\n")
    for p in points:
        print(f"{p['point']:32} {'ok  ' if p['ok'] else 'FAIL'} {p.get('mass_g', '-'):>7} g "
              f"{p['rebuild_s']:.2f} s  {'; '.join(p['problems'])}")
    print("ok" if result["ok"] else "FAILED")
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

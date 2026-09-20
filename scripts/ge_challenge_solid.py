"""M2A.8 step 1: the clean GE-challenge bracket solid, from the FVZ outer surface.

Neither frozen candidate is usable for the whole M2A chain. Iteration1 meshes cleanly
but is lightweighted by open pockets cut up from the underside. Bracket_Modified_FVZ has
the continuous underside we want, but its weight is taken out by a sealed internal
cavity whose B-rep cannot be meshed to the M2A.2 thresholds -- and every defect is in
that cavity shell, not in the external surface:

    shell            faces  edges  <1 mm2  zero-length  min face area
    outer               58    166       0            0      46.72 mm2
    inner (cavity)     258    603       8           10       0.0039 mm2

So this keeps FVZ's external surface exactly as it is, drops the cavity, and closes the
outer shell into a solid. The result is the external geometry of the GE challenge part
with a deliberate, fully dense interior: the honest subject for a machining study, and
the base M2A.8 adds internal features to.

Reads the frozen data/simjeb/Bracket_Modified_FVZ.stp (never writes it) after checking
its SHA-256. Writes data/ge_manual/GE_Challenge_Bracket.stp and
out/ge_challenge_solid/solid-check.json.

    vendor/fem-env/bin/python scripts/ge_challenge_solid.py
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
import Part  # noqa: E402

from ge_part import SOURCES  # noqa: E402

DONOR = "Bracket_Modified_FVZ"
SOURCE = ROOT / "data" / "simjeb" / f"{DONOR}.stp"
NAME = "GE_Challenge_Bracket"
TARGET = ROOT / "data" / "ge_manual" / f"{NAME}.stp"
OUT = ROOT / "out" / "ge_challenge_solid"

TINY_FACE_MM2 = 1.0
SHORT_EDGE_MM = 0.3


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(shape):
    faces = shape.Faces
    edges = shape.Edges
    return {
        "solids": len(shape.Solids),
        "shells": len(shape.Solids[0].Shells) if shape.Solids else len(shape.Shells),
        "faces": len(faces),
        "edges": len(edges),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "volume_mm3": round(shape.Volume, 4),
        "area_mm2": round(shape.Area, 4),
        "min_face_area_mm2": round(min(f.Area for f in faces), 6),
        "faces_below_1mm2": sum(1 for f in faces if f.Area < TINY_FACE_MM2),
        "zero_length_edges": sum(1 for e in edges if e.Length < 1e-6),
        "edges_below_0_3mm": sum(1 for e in edges if e.Length < SHORT_EDGE_MM),
        "max_tolerance_mm": round(max(shape.getTolerance(1, t) for t in (Part.Vertex, Part.Edge, Part.Face)), 9),
    }


def bop_flags(shape):
    """BOP checker messages, counted by kind. check(True) prints and returns None."""
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            shape.check(True)
        except Exception as exc:  # a hard failure is itself the finding
            return {"check_raised": str(exc)}
    counts = {}
    for line in buf.getvalue().splitlines():
        line = line.strip()
        if line.startswith("Error in"):
            counts[line] = counts.get(line, 0) + 1
    return counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    actual = sha256(SOURCE)
    if actual != SOURCES[DONOR]:
        sys.exit(f"SOURCE CHECKSUM MISMATCH: {SOURCE}\n  expected {SOURCES[DONOR]}\n  actual   {actual}")

    donor = Part.Shape()
    donor.read(str(SOURCE))
    record = {"donor": str(SOURCE.relative_to(ROOT)), "donor_sha256": actual,
              "freecad_version": ".".join(FreeCAD.Version()[:3]),
              "method": "outer shell of the donor closed into a solid; the sealed cavity shell is dropped",
              "donor_stats": stats(donor)}

    solid_shells = donor.Solids[0].Shells
    outer = max(solid_shells, key=lambda s: s.BoundBox.DiagonalLength)
    record["donor_shells"] = [
        {"faces": len(s.Faces), "edges": len(s.Edges),
         "min_face_area_mm2": round(min(f.Area for f in s.Faces), 6),
         "faces_below_1mm2": sum(1 for f in s.Faces if f.Area < TINY_FACE_MM2),
         "zero_length_edges": sum(1 for e in s.Edges if e.Length < 1e-6),
         "role": "outer" if s.isSame(outer) else "cavity"}
        for s in solid_shells]

    candidates = {"outer_shell_solid": Part.makeSolid(outer)}
    try:
        candidates["removeSplitter"] = candidates["outer_shell_solid"].removeSplitter()
    except Exception as exc:
        record.setdefault("notes", []).append(f"removeSplitter failed: {exc}")

    scored = {}
    for tag, shape in candidates.items():
        st = stats(shape)
        st["bop_flags"] = bop_flags(shape)
        st["bop_flag_total"] = sum(v for v in st["bop_flags"].values() if isinstance(v, int))
        scored[tag] = st
    record["candidates"] = scored

    # Prefer the fewest BOP flags, then the fewest faces, among valid closed solids that
    # keep the donor's outer volume. Volume must not move: the surface is the deliverable.
    ref = scored["outer_shell_solid"]["volume_mm3"]
    ok = [t for t, st in scored.items()
          if st["valid"] and st["closed"] and st["solids"] == 1 and abs(st["volume_mm3"] - ref) < 1e-3]
    chosen = min(ok, key=lambda t: (scored[t]["bop_flag_total"], scored[t]["faces"]))
    shape = candidates[chosen]
    record["chosen"] = chosen

    doc = FreeCAD.newDocument(NAME)
    obj = doc.addObject("Part::Feature", "Bracket")
    obj.Shape = shape
    obj.Label = f"GE challenge bracket (external surface of {DONOR}.stp, solid interior)"
    doc.recompute()
    TARGET.unlink(missing_ok=True)
    obj.Shape.exportStep(str(TARGET))
    FreeCAD.closeDocument(doc.Name)

    back = Part.Shape()
    back.read(str(TARGET))
    record["written"] = {"path": str(TARGET.relative_to(ROOT)), "sha256": sha256(TARGET),
                         "bytes": TARGET.stat().st_size, "roundtrip": stats(back)}
    record["written"]["roundtrip_volume_change_mm3"] = round(back.Volume - shape.Volume, 6)

    # The external surface is the deliverable: prove it did not move.
    dev = max(back.distToShape(Part.Vertex(v.Point))[0] for v in outer.Vertexes)
    record["max_vertex_deviation_from_donor_outer_mm"] = round(dev, 9)
    record["acceptance"] = {
        "valid_closed_single_solid": back.isValid() and back.isClosed() and len(back.Solids) == 1,
        "no_face_below_1mm2": record["written"]["roundtrip"]["faces_below_1mm2"] == 0,
        "no_zero_length_edge": record["written"]["roundtrip"]["zero_length_edges"] == 0,
        "surface_unchanged_within_1e-6mm": dev < 1e-6,
    }
    (OUT / "solid-check.json").write_text(json.dumps(record, indent=2))
    print(json.dumps({k: record[k] for k in ("chosen", "acceptance", "written",
                                             "max_vertex_deviation_from_donor_outer_mm")},
                     indent=2, default=str))


if __name__ == "__main__":
    main()

"""M2.4: does the D-06 label chain survive into the CalculiX deck, at every bound?

The chain REQ-OPT-002 and the prediction score (REQ-OPT-005) rest on:

    geometric predicate -> face -> FEM Mesh Group -> Gmsh physical group
        -> FemMesh group -> .inp element set

This walks it end to end at the baseline and at every parameter's min and max,
and checks the three things the task asks of the deck: every D-06 label present,
non-overlapping, covering the part.

It writes the deck two ways at each point:

- `ccx`  - the pipeline path, FreeCAD's ccxtools writing a full LC1 deck;
- `grp`  - `FemMesh.writeABAQUS(path, 1, True)`, the mesh alone with group data.

and then, because neither gives a volume partition, builds and checks D-06's own
fallback: element-centroid membership, every C3D10 element labelled by the region
of the nearest surface element, written out as one `*ELSET` per region.

There is no CadQuery here and none is planned; D-04 (v0.5) keeps FreeCAD, and the
"CadQuery tags" in the task's original wording predate it.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_bracket_labels.py [--points baseline ...]

Writes out/ge_bracket_labels/labels.json and, per point, the two decks and the
fallback element sets. Exit 0 when every point's chain checks pass, 2 otherwise.
"""

import argparse
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
from FreeCAD import Vector  # noqa: E402
from femtools import ccxtools  # noqa: E402

import ge_bracket_mesh as gm  # noqa: E402  D-24 sizing and the Gmsh runner (M2.3)
from parts import ge_bracket as gb  # noqa: E402

OUT = ROOT / "out" / "ge_bracket_labels"
LC1 = json.loads((ROOT / "parts" / "ge_bracket_lc1.json").read_text())

# FreeCAD 1.1.3 hard-codes this in femsolver/calculix/write_mesh.py; it is why
# no mesh group reaches the ccxtools deck. Checked at run time, not assumed.
CCX_WRITER = ROOT / "vendor" / "fem-env" / "Mod" / "Fem" / "femsolver" / "calculix" / "write_mesh.py"

SET_RE = re.compile(r"^\*(ELSET|NSET)\s*,\s*(?:ELSET|NSET)\s*=\s*([^\s,]+)", re.I | re.M)


def d06_sets(names):
    """Set names in a deck that carry a D-06 region label."""
    return [n for n in names
            if any(n == r or n.startswith(f"{r}_") for r in gb.REGIONS)]


def points(which):
    """The parameter points to walk: the baseline and every bound."""
    baseline = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    out = {"baseline": baseline}
    for name, rec in gb.PARAMS.items():
        for bound in ("min", "max"):
            out[f"{name}={bound}"] = {**baseline, name: rec[bound]}
    return out if which is None else {k: out[k] for k in which}


def cad_labels(shape, p):
    """Per-face D-06 label, with the REQ-OPT-008 and D-06 checks that guard it."""
    m = gb.match(shape, p)
    labels, unlabelled, overlap = gb.region_of_faces(shape, p)
    problems = []
    for name in gb.PREDICATES:
        if len(m[name]) != 1:
            problems.append(f"predicate {name} matches {m[name]}")
    if unlabelled:
        problems.append(f"faces with no D-06 region: {unlabelled}")
    if overlap:
        problems.append(f"faces in two D-06 regions: {overlap}")
    faces = {region: tuple(f"Face{i}" for i, r in sorted(labels.items()) if region in r)
             for region in gb.REGIONS}
    empty = [r for r, f in faces.items() if not f]
    if empty:
        problems.append(f"D-06 regions with no face: {empty}")
    return faces, problems


def add_groups(doc, part, mesh, faces):
    """One FEM Mesh Group per D-06 region, named by the region."""
    for region, names in faces.items():
        g = ObjectsFem.makeMeshGroup(doc, mesh, True, f"MeshGroup_{region}")
        g.Label = region  # UseLabel=True, so this is the name Gmsh and the .unv carry
        g.References = [(part, names)]
    doc.recompute()


def femmesh_groups(fm):
    """The FemMesh's D-06 groups, by region and kind."""
    got = {}
    for gid in fm.Groups:
        name, kind = fm.getGroupName(gid), fm.getGroupElementType(gid)
        for region in gb.REGIONS:
            if name == f"{region}_{kind}s" or name == region:
                got[(region, kind)] = set(fm.getGroupElements(gid))
    return got


def group_checks(fm, got):
    """What the mesh groups are, and what they are not: a volume partition."""
    regions = list(gb.REGIONS)
    missing = [f"{r}_{k}" for r in regions for k in ("Node", "Face") if (r, k) not in got]
    faces = {r: got.get((r, "Face"), set()) for r in regions}
    nodes = {r: got.get((r, "Node"), set()) for r in regions}

    def pairs(sets):
        return {f"{a}|{b}": len(sets[a] & sets[b])
                for i, a in enumerate(regions) for b in regions[i + 1:] if sets[a] & sets[b]}

    covered = set().union(*faces.values()) if faces else set()
    return {
        "groups_missing": missing,
        "surface_elements_per_region": {r: len(v) for r, v in faces.items()},
        "nodes_per_region": {r: len(v) for r, v in nodes.items()},
        "surface_element_overlaps": pairs(faces),
        "node_overlaps": pairs(nodes),
        "surface_elements_covered": len(covered),
        "surface_elements_total": fm.FaceCount,
        "surface_coverage_complete": len(covered) == fm.FaceCount,
        "volume_elements_total": fm.VolumeCount,
        "volume_elements_in_any_group": 0,  # no group has element type Volume
        "is_volume_partition": False,
    }


def deck_sets(path):
    """Set names declared in an .inp, following *INCLUDE one level."""
    text = path.read_text(errors="replace")
    for inc in re.findall(r"^\*INCLUDE\s*,\s*INPUT\s*=\s*(\S+)", text, re.I | re.M):
        p = path.parent / inc
        if p.exists():
            text += "\n" + p.read_text(errors="replace")
    return sorted({name for _, name in SET_RE.findall(text)})


def write_ccx_deck(doc, part, p, work):
    """The pipeline path: a full LC1 deck written by ccxtools."""
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

    names = gb.match(part.Shape, p)
    for n in LC1["support"]["predicates"]:
        fixed = ObjectsFem.makeConstraintFixed(doc, f"Fixed_{n}")
        fixed.References = [(part, f"Face{names[n][0]}")]
        analysis.addObject(fixed)
    fx, fy, fz = LC1["load"]["vector_n"]
    pin = ObjectsFem.makeConstraintRigidBody(doc, "Pin")
    pin.References = [(part, f"Face{names[n][0]}") for n in LC1["load"]["load_faces"]]
    pin.ReferenceNode = Vector(*LC1["load"]["applied_at"])
    for axis, value in zip("XYZ", (fx, fy, fz)):
        setattr(pin, f"TranslationalMode{axis}", "Load")
        setattr(pin, f"Force{axis}", f"{value} N")
    analysis.addObject(pin)
    doc.recompute()

    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    work.mkdir(parents=True, exist_ok=True)  # setup_working_dir warns but does not create
    fea.setup_working_dir(str(work), create=True)
    problems = fea.check_prerequisites()
    if problems:
        raise RuntimeError(f"prerequisites: {problems}")
    t = time.perf_counter()
    fea.write_inp_file()
    return Path(fea.inp_file_name), round(time.perf_counter() - t, 2)


def centroid_labels(fm, got):
    """D-06's fallback: every volume element labelled by the nearest surface element.

    The surface elements come from the D-06 mesh groups themselves, so the label
    still originates at the geometric predicate. Each C3D10 element's corner
    centroid is matched to the closest surface triangle (VTK cell locator), which
    makes the labelling disjoint by construction - one closest cell per element -
    and exhaustive, which is exactly what the group route cannot give.
    """
    import pyvista as pv

    nodes = fm.Nodes
    regions = list(gb.REGIONS)
    tris, tri_region = [], []
    for ri, region in enumerate(regions):
        for eid in sorted(got.get((region, "Face"), ())):
            tris.append(fm.getElementNodes(eid)[:3])  # corner nodes of the Triangle6
            tri_region.append(ri)
    used = sorted({n for t in tris for n in t})
    index = {n: i for i, n in enumerate(used)}
    xyz = np.array([[nodes[n].x, nodes[n].y, nodes[n].z] for n in used])
    cells = np.array([[index[n] for n in t] for t in tris])
    surface = pv.PolyData(xyz, np.c_[np.full(len(cells), 3), cells].ravel())
    tri_region = np.array(tri_region)

    vol_ids = list(fm.Volumes)
    corners = np.array([fm.getElementNodes(e)[:4] for e in vol_ids])
    all_used = sorted({int(n) for row in corners for n in row})
    vindex = {n: i for i, n in enumerate(all_used)}
    vxyz = np.array([[nodes[n].x, nodes[n].y, nodes[n].z] for n in all_used])
    cents = vxyz[np.vectorize(vindex.get)(corners)].mean(axis=1)

    closest = surface.find_closest_cell(cents)
    label = tri_region[np.asarray(closest)]
    sets = {regions[ri]: [vol_ids[i] for i in np.flatnonzero(label == ri)]
            for ri in range(len(regions))}

    union = set()
    overlaps = 0
    for members in sets.values():
        overlaps += len(union & set(members))
        union |= set(members)
    checks = {
        "elements_per_region": {r: len(v) for r, v in sets.items()},
        "labelled": len(union),
        "volume_elements_total": fm.VolumeCount,
        "exhaustive": len(union) == fm.VolumeCount,
        "disjoint": overlaps == 0,
        "every_region_non_empty": all(len(v) > 0 for v in sets.values()),
        "surface_triangles_used": len(tris),
    }
    checks["ok"] = checks["exhaustive"] and checks["disjoint"] and checks["every_region_non_empty"]
    return sets, checks


def write_elsets(path, sets):
    """The fallback as an .inp include: one *ELSET per D-06 region."""
    with path.open("w") as f:
        f.write("** D-06 region labels by element-centroid membership (M2.4 fallback)\n")
        for region, members in sets.items():
            f.write(f"*ELSET,ELSET={region}\n")
            for i in range(0, len(members), 16):
                f.write(", ".join(str(e) for e in members[i:i + 16]) + ",\n")
    return path


def walk(name, p, out):
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    rec = {"point": name, "params": p, "problems": []}

    doc, part, mesh, shape, geom = gm.build(p["arm_root_fillet"], False, params=p)
    rec["faces"] = len(shape.Faces)
    faces, problems = cad_labels(shape, p)
    rec["problems"] += problems
    rec["faces_per_region"] = {r: len(v) for r, v in faces.items()}
    if problems:  # the chain cannot be meaningful if the CAD end is broken
        FreeCAD.closeDocument(doc.Name)
        rec["ok"] = False
        return rec

    add_groups(doc, part, mesh, faces)
    tools, err, elapsed = gm.run_gmsh(mesh, out / "gmsh")
    fm = mesh.FemMesh
    rec["mesh"] = {"nodes": fm.NodeCount, "c3d10": fm.VolumeCount,
                   "surface_elements": fm.FaceCount, "gmsh_s": round(elapsed, 2)}
    got = femmesh_groups(fm)
    rec["mesh_groups"] = group_checks(fm, got)
    if rec["mesh_groups"]["groups_missing"]:
        rec["problems"].append(f"FemMesh groups missing: {rec['mesh_groups']['groups_missing']}")

    grp = out / "mesh_groups.inp"
    fm.writeABAQUS(str(grp), 1, True)
    rec["grp_deck"] = {"file": grp.name, "sets_total": len(deck_sets(grp)),
                       "d06_sets": d06_sets(deck_sets(grp))}
    ccx_inp, write_s = write_ccx_deck(doc, part, p, out / "ccx")
    sets = deck_sets(ccx_inp)
    rec["ccx_deck"] = {"file": ccx_inp.name, "write_s": write_s, "sets": sets,
                       "d06_sets": d06_sets(sets)}

    fallback_sets, checks = centroid_labels(fm, got)
    write_elsets(out / "d06_elsets.inp", fallback_sets)
    rec["fallback"] = checks
    if not checks["ok"]:
        rec["problems"].append(f"centroid fallback not a partition: {checks}")

    doc.saveAs(str(out / f"{name.replace('=', '_')}.FCStd"))
    FreeCAD.closeDocument(doc.Name)
    rec["ok"] = not rec["problems"]
    return rec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", nargs="+", default=None,
                        help="parameter points to walk (default: baseline and every bound)")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    src = CCX_WRITER.read_text()
    report = {"freecad": ".".join(FreeCAD.Version()[:3]), "sizes_mm": gm.SIZES,
              "d06_regions": list(gb.REGIONS),
              "ccx_writer_group_param": re.search(r"group_param\s*=\s*(\w+)", src).group(1),
              "ccx_writer_source": str(CCX_WRITER.relative_to(ROOT)),
              "points": []}

    for name, p in points(args.points).items():
        rec = walk(name, p, OUT / name.replace("=", "_"))
        report["points"].append(rec)
        (OUT / "labels.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name:28} {'ok  ' if rec['ok'] else 'FAIL'} "
              f"c3d10={rec.get('mesh', {}).get('c3d10', '-')} "
              f"grp={len(rec.get('grp_deck', {}).get('d06_sets', []))} "
              f"ccx={len(rec.get('ccx_deck', {}).get('d06_sets', []))} "
              f"fallback={rec.get('fallback', {}).get('ok')} "
              f"{'; '.join(rec['problems'])}", flush=True)

    report["ok"] = all(r["ok"] for r in report["points"])
    (OUT / "labels.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ok" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())

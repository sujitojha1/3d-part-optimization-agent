"""M2.3: hand-mesh the parametric ge_bracket at nominal and minimum arm_root_fillet.

Builds the same objects a person creates by hand in the FEM Workbench — an
Analysis, a `FemMeshGmsh` of the bracket (second-order tetrahedra, C3D10) and
one `MeshRegion` on the `arm_root_fillet` and `pin_bore` faces — with D-24's
CharacteristicLengthMax / CharacteristicLengthMin / region size, at

- nominal `arm_root_fillet` = 5.0 mm, and
- its PARAMS minimum,  `arm_root_fillet` = 3.0 mm,

which is where second-order meshing is expected to invert elements. Every case
is meshed once with `SecondOrderLinear = false`; if Gmsh reports inverted
elements (negative Jacobians) the D-24 retry runs the same case again with
`SecondOrderLinear = true` and both attempts are recorded.

Region faces are chosen by ge_bracket's geometric predicates, never by stored
face index (D-04, REQ-OPT-008), so the same code re-selects them after the
radius changes.

Each case is meshed on the full model and, separately, on the half model cut at
the clevis midplane. The half model is element-count and timing evidence for
the D-13 budget lever only: D-23 (v0.7) keeps the **full model** for analysis,
because the measured bolt pattern is asymmetric about that plane. Nothing here
proposes solving the half model.

Quality comes from the Gmsh 4.15.2 Python API, read back off the .unv Gmsh
wrote, and is judged against THRESHOLDS, fixed here before any mesh is made.

Writes out/ge_bracket_mesh/mesh.json, and per case a work directory with the
FCStd, .geo, .brep and .unv plus a section view through the arm root.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_bracket_mesh.py [--cases nominal_full ...]
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
import Part  # noqa: E402
from FreeCAD import Vector  # noqa: E402
from femmesh.gmshtools import GmshTools  # noqa: E402

from parts import ge_bracket as gb  # noqa: E402

OUT = ROOT / "out" / "ge_bracket_mesh"

# D-24 sizing for ge_bracket, in mm. The region size is the one MeshRegion
# value D-24 allows, applied to the arm_root_fillet and pin_bore faces; it
# cannot go below CharacteristicLengthMin, which Gmsh would clamp. Curvature is
# set explicitly (FreeCAD's default 12 elements per 2*pi puts ~1.6 mm elements
# on the r3 fillet, below the region size and far below what LC1 needs).
# region 1.5 puts about 3 quadratic elements across the quarter-arc of the
# minimum r3 fillet; --region records the 2.0 and 1.0 alternatives beside it.
SIZES = {"max": 4.0, "min": 1.0, "region": 1.5, "curvature": 8}

# The one MeshRegion's faces: D-06 regions arm_root_fillet and pin_bore.
REGION_NAMES = ("arm_root_fillet", "pin_bore")

# Acceptance thresholds, fixed before meshing. Same Gmsh 4.15.2 definitions and
# same values as the M2A manual study (docs/ge-manual-mesh.md section 3).
THRESHOLDS = {
    "inverted_or_zero_volume_elements": 0,     # minDetJac <= 0 or |volume| ~ 0
    "min_scaled_jacobian_min": 0.1,            # Gmsh minSJ, every element
    "min_scaled_jacobian_p0_1": 0.3,           # 0.1th percentile
    "gamma_min": 0.05,                         # Gmsh gamma, every element
    "gamma_below_0_2_fraction_max": 0.001,     # at most 0.1 % of elements
    "aspect_ratio_max": 20.0,                  # maxEdge/minEdge, every element
    "aspect_ratio_p99_9_max": 8.0,
}

# arm_root_fillet values: the baseline, and the PARAMS minimum D-24's retry
# exists for. Every other parameter stays at its baseline.
RADII = {"nominal": gb.PARAMS["arm_root_fillet"]["baseline"],
         "min": gb.PARAMS["arm_root_fillet"]["min"]}

# The four D-24 cases, plus three variants that isolate the two mesher settings
# the thresholds depend on. `no_netgen` drops OptimizeNetgen (not a FreeCAD
# default, and not named in D-24); `no_hoo` drops HighOrderOptimize, the
# setting M2.1 found the baseline inverts without — it is the reproducible
# probe for D-24's negative-Jacobian retry, which the four D-24 cases never
# reach because none of them inverts.
CASES = {f"{r}_{m}": {"radius_key": r, "half": m == "half",
                      "netgen": True, "high_order_optimize": "Optimization"}
         for r in RADII for m in ("full", "half")}
CASES.update({
    f"{r}_full_no_netgen": {"radius_key": r, "half": False,
                            "netgen": False, "high_order_optimize": "Optimization"}
    for r in RADII})
CASES["min_full_no_hoo"] = {"radius_key": "min", "half": False,
                            "netgen": True, "high_order_optimize": "None"}
# Only the four D-24 cases have to meet THRESHOLDS; the three variants exist to
# record what happens when a setting is dropped, so they do not gate the run.
D24_CASES = [f"{r}_{m}" for r in RADII for m in ("full", "half")]

GMSH_PREFS = "User parameter:BaseApp/Preferences/Mod/Fem/Gmsh"
GMSH_THREADS = 1  # repeatable counts; FreeCAD's default (all cores) is not

TET10 = 11  # Gmsh element type: 10-node second-order tetrahedron


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def half_shape(shape):
    """The model cut at the clevis midplane y = PIN[1], keeping +y."""
    box = Part.makeBox(1000, 1000, 1000, Vector(-500, gb.PIN[1] - 1000, -500))
    return shape.cut(box).removeSplitter()


def region_faces(shape, p, half):
    """FaceN names for the MeshRegion, and the per-predicate match counts."""
    m = gb.match(shape, p)
    names = [n for r in REGION_NAMES for n in gb.REGIONS[r]]
    matched = {n: m[n] for n in names}
    faces = tuple(f"Face{i}" for n in names for i in m[n])
    # REQ-OPT-008 holds on the full model: every single-face predicate matches
    # exactly one face. `fillet_corner` is a set rule, so any count is legal,
    # and the half model legitimately loses the -y predicates to the cut.
    bad = {n: v for n, v in m.items() if len(v) != 1 and n in gb.PREDICATES}
    return faces, matched, ({} if half else bad)


def build(radius, half, netgen=True, high_order_optimize="Optimization", region_size=None):
    """Document, part object and Gmsh mesh object for one case, unmeshed."""
    p = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    p["arm_root_fillet"] = radius
    shape = gb.build_shape(p)
    if half:
        shape = half_shape(shape)
    faces, matched, bad = region_faces(shape, p, half)

    doc = FreeCAD.newDocument(f"ge_bracket_mesh_{radius}_{'half' if half else 'full'}")
    part = doc.addObject("Part::Feature", "GeBracket")
    part.Shape = shape
    doc.recompute()
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    mesh = analysis.addObject(ObjectsFem.makeMeshGmsh(doc, "Mesh"))[0]
    mesh.Shape = part
    mesh.ElementDimension = "3D"
    mesh.ElementOrder = "2nd"
    mesh.SecondOrderLinear = False
    mesh.HighOrderOptimize = high_order_optimize
    mesh.CharacteristicLengthMax = SIZES["max"]
    mesh.CharacteristicLengthMin = SIZES["min"]
    mesh.MeshSizeFromCurvature = SIZES["curvature"]
    # Not a FreeCAD default and not named in D-24. Without it the bolt-boss
    # side walls carry minSJ 0.089 < 0.1 at both radii (cases *_no_netgen).
    mesh.OptimizeNetgen = netgen
    region = ObjectsFem.makeMeshRegion(doc, mesh, region_size or SIZES["region"],
                                       "Region_arm_root_pin_bore")
    region.References = [(part, faces)]
    doc.recompute()
    geom = {"parameters_mm": p, "solid": {"volume_mm3": round(shape.Volume, 3),
                                          "area_mm2": round(shape.Area, 3),
                                          "faces": len(shape.Faces), "edges": len(shape.Edges),
                                          "solids": len(shape.Solids)},
            "mass_g": round(shape.Volume * gb.DENSITY_G_MM3, 2),
            "mesh_region_size_mm": region.CharacteristicLength.getValueAs("mm").Value,
            "mesh_region_faces": list(faces),
            "mesh_region_face_count": len(faces),
            "predicate_matches": {k: v for k, v in matched.items()},
            "predicates_not_matching_one_face": bad}
    return doc, part, mesh, shape, geom


def settings(mesh):
    names = ["ElementDimension", "ElementOrder", "SecondOrderLinear", "HighOrderOptimize",
             "CharacteristicLengthMax", "CharacteristicLengthMin", "Algorithm2D", "Algorithm3D",
             "OptimizeStd", "OptimizeNetgen", "MeshSizeFromCurvature", "RecombineAll",
             "GeometryTolerance", "CoherenceMesh", "SubdivisionAlgorithm"]
    out = {}
    for n in names:
        if hasattr(mesh, n):
            v = getattr(mesh, n)
            out[n] = str(v) if hasattr(v, "UserString") else v
    return out


def run_gmsh(mesh, workdir):
    """FreeCAD's GmshTools pipeline, single-threaded, in a directory we keep."""
    prefs = FreeCAD.ParamGet(GMSH_PREFS)
    had = "NumOfThreads" in prefs.GetInts()
    old = prefs.GetInt("NumOfThreads")
    prefs.SetInt("NumOfThreads", GMSH_THREADS)
    try:
        tools = GmshTools(mesh)
        tools.load_properties()
        tools.update_mesh_data()
        tools.get_tmp_file_paths(str(workdir), create=True)
        tools.get_gmsh_command()
        tools.write_gmsh_input_files()
        t = time.perf_counter()
        err = tools.run_gmsh_with_geo()
        elapsed = time.perf_counter() - t
        tools.read_and_set_new_mesh()
        return tools, err or "", elapsed
    finally:
        if had:
            prefs.SetInt("NumOfThreads", old)
        else:
            prefs.RemInt("NumOfThreads")


def quality(unv):
    """Per-element quality of the tet10 elements in a .unv, via the Gmsh API."""
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.merge(str(unv))
    types, tags, nodes = gmsh.model.mesh.getElements(3)
    k = list(types).index(TET10)
    tags, conn = np.array(tags[k]), np.array(nodes[k]).reshape(-1, 10)
    q = {name: np.array(gmsh.model.mesh.getElementQualities(tags, name))
         for name in ("minDetJac", "minSJ", "gamma", "minEdge", "maxEdge", "volume")}
    ntags, coords, _ = gmsh.model.mesh.getNodes()
    xyz = np.zeros((int(ntags.max()) + 1, 3))
    xyz[ntags.astype(int)] = np.array(coords).reshape(-1, 3)
    counts = {gmsh.model.mesh.getElementProperties(t)[0]: len(e)
              for t, e in zip(*gmsh.model.mesh.getElements()[:2])}
    version = gmsh.__version__
    gmsh.finalize()
    q["aspect"] = q["maxEdge"] / q["minEdge"]
    return tags, conn, xyz, q, counts, version


def summarise(tags, conn, xyz, q, radius):
    def dist(a):
        return {"min": float(a.min()), "p0_1": float(np.percentile(a, 0.1)),
                "p1": float(np.percentile(a, 1)), "p5": float(np.percentile(a, 5)),
                "median": float(np.median(a)), "max": float(a.max())}

    centroid = xyz[conn[:, :4]].mean(axis=1)
    zero_vol = np.abs(q["volume"]) < 1e-9 * np.abs(q["volume"]).mean()
    inverted = q["minDetJac"] <= 0
    asp = dist(q["aspect"])
    s = {
        "elements_tet10": int(len(tags)),
        "inverted_min_det_jac_le_0": int(inverted.sum()),
        "zero_volume": int(zero_vol.sum()),
        "min_scaled_jacobian": dist(q["minSJ"]),
        "gamma": dist(q["gamma"]),
        "gamma_below_0_2_fraction": float((q["gamma"] < 0.2).mean()),
        "gamma_below_threshold_count": int((q["gamma"] < THRESHOLDS["gamma_min"]).sum()),
        "aspect_ratio": {"min": asp["min"], "median": asp["median"],
                         "p99": float(np.percentile(q["aspect"], 99)),
                         "p99_9": float(np.percentile(q["aspect"], 99.9)), "max": asp["max"]},
        "worst_by_min_scaled_jacobian": [
            {"element": int(tags[i]), "minSJ": round(float(q["minSJ"][i]), 4),
             "gamma": round(float(q["gamma"][i]), 4), "aspect": round(float(q["aspect"][i]), 2),
             "min_det_jac": float(q["minDetJac"][i]),
             "centroid_deck": centroid[i].round(2).tolist()}
            for i in np.argsort(q["minSJ"])[:10]],
        "inverted_element_centroids_deck": centroid[inverted][:20].round(2).tolist(),
    }
    t = THRESHOLDS
    s["acceptance"] = {
        "inverted_or_zero_volume":
            s["inverted_min_det_jac_le_0"] + s["zero_volume"] <= t["inverted_or_zero_volume_elements"],
        "min_scaled_jacobian_min": s["min_scaled_jacobian"]["min"] >= t["min_scaled_jacobian_min"],
        "min_scaled_jacobian_p0_1": s["min_scaled_jacobian"]["p0_1"] >= t["min_scaled_jacobian_p0_1"],
        "gamma_min": s["gamma"]["min"] >= t["gamma_min"],
        "gamma_below_0_2_fraction": s["gamma_below_0_2_fraction"] <= t["gamma_below_0_2_fraction_max"],
        "aspect_ratio_max": s["aspect_ratio"]["max"] <= t["aspect_ratio_max"],
        "aspect_ratio_p99_9": s["aspect_ratio"]["p99_9"] <= t["aspect_ratio_p99_9_max"],
    }
    s["accepted"] = all(s["acceptance"].values())
    # Elements whose centroid sits within one radius of the arm-root fillet
    # band: the concentration the MeshRegion exists for, and where second-order
    # inversion is expected. z = base_top +- radius, in the two arm bands.
    p = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    p["arm_root_fillet"] = radius
    g = gb.layout(p)
    near = np.abs(centroid[:, 2] - g["base_top"]) < radius
    in_band = np.zeros(len(centroid), bool)
    for ylo, yhi in [(g["y_in"][0], g["y_out"][0] + radius), (g["y_out"][1] - radius, g["y_in"][1])]:
        in_band |= (centroid[:, 1] > min(ylo, yhi) - radius) & (centroid[:, 1] < max(ylo, yhi) + radius)
    band = near & in_band
    s["arm_root_band"] = {
        "elements": int(band.sum()),
        "min_scaled_jacobian_min": float(q["minSJ"][band].min()) if band.any() else None,
        "gamma_min": float(q["gamma"][band].min()) if band.any() else None,
        "inverted": int((inverted & band).sum()),
    }
    return s, centroid


def section_view(out, case, radius, conn, xyz, q, shape):
    """Look at the mesh in the arm root: a crinkle clip through the fillet."""
    import pyvista as pv

    corners = conn[:, :4]
    used, inv = np.unique(corners, return_inverse=True)
    grid = pv.UnstructuredGrid(
        np.c_[np.full(len(corners), 4), inv.reshape(-1, 4)].ravel(),
        np.full(len(corners), pv.CellType.TETRA), xyz[used])
    grid.cell_data["minSJ"] = q["minSJ"]
    p = {k: r["baseline"] for k, r in gb.PARAMS.items()}
    p["arm_root_fillet"] = radius
    g = gb.layout(p)
    origin = ((g["x0"] + g["x1"]) / 2, g["y_out"][0], g["base_top"])
    clipped = grid.clip(normal=(1, 0, 0), origin=origin, crinkle=True)
    pl = pv.Plotter(off_screen=True, window_size=(1300, 950))
    pl.set_background("white")
    pl.add_mesh(clipped, scalars="minSJ", cmap="viridis", clim=(0, 1), show_edges=True,
                edge_color="#333333", line_width=0.3)
    pl.add_text(f"{case}: arm_root_fillet r{radius} mm, clip x={origin[0]:.1f}; colour = minSJ",
                font_size=11, color="black")
    pl.camera_position = [(origin[0] - 250, origin[1], origin[2]), origin, (0, 0, 1)]
    pl.enable_parallel_projection()
    pl.reset_camera()
    pl.camera.zoom(3.0)
    pl.screenshot(str(out / "section_arm_root.png"))
    pl.close()


def attempt(case, spec, radius, work, second_order_linear):
    """One mesh of one case at one SecondOrderLinear setting."""
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    doc, part, mesh, shape, geom = build(radius, spec["half"], spec["netgen"],
                                         spec["high_order_optimize"], spec.get("region_size"))
    mesh.SecondOrderLinear = second_order_linear
    doc.recompute()
    tools, err, elapsed = run_gmsh(mesh, work)
    fem = mesh.FemMesh
    rec = {"second_order_linear": second_order_linear, "geometry": geom,
           "settings": settings(mesh), "gmsh_binary": tools.gmsh_bin,
           "gmsh_stderr_tail": err.strip().splitlines()[-20:],
           "gmsh_reports_negative_jacobian": any(
               s in err.lower() for s in ("negative jacobian", "invalid element", "inverted")),
           "mesh_seconds": round(elapsed, 2),
           "femmesh": {"nodes": fem.NodeCount, "volumes": fem.VolumeCount, "faces": fem.FaceCount,
                       "edges": fem.EdgeCount, "tetra": fem.TetraCount}}
    unv = Path(tools.temp_file_mesh)
    doc.saveAs(str(work / f"{case}.FCStd"))
    FreeCAD.closeDocument(doc.Name)
    rec["files"] = {f.name: sha256(f) for f in sorted(work.iterdir())
                    if f.is_file() and f.suffix != ".FCBak"}
    tags, conn, xyz, q, counts, version = quality(unv)
    rec["gmsh_api_version"] = version
    rec["unv_element_counts_by_type"] = counts
    rec["counts_match_femmesh"] = len(tags) == fem.VolumeCount
    rec["connectivity_sha256"] = hashlib.sha256(
        np.ascontiguousarray(conn, dtype=np.int64).tobytes()).hexdigest()
    summary, _ = summarise(tags, conn, xyz, q, radius)
    rec["quality"] = summary
    return rec, (conn, xyz, q, shape)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--region", type=float, default=None,
                        help="override the MeshRegion size (mm); records the run under "
                             "<case>_region<size> instead of replacing the case")
    parser.add_argument("--force-retry", nargs="*", choices=list(CASES), default=[],
                        metavar="CASE",
                        help="run D-24's SecondOrderLinear retry on these cases even though "
                             "they do not invert, to exercise and record the retry path")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "mesh.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report.update({"freecad_version": ".".join(FreeCAD.Version()[:3]), "sizes_mm": SIZES,
                   "thresholds": THRESHOLDS, "gmsh_threads": GMSH_THREADS,
                   "mesh_region_regions": list(REGION_NAMES), "radii_mm": RADII,
                   "cases_defined": CASES})
    failures = []

    for case in args.cases:
        spec = CASES[case]
        radius = RADII[spec["radius_key"]]
        # A forced retry is recorded beside the case, never in place of it.
        forced = case in args.force_retry
        if args.region is not None:
            spec = dict(spec, region_size=args.region)
        key = (f"{case}_region{args.region:g}".replace(".", "p") if args.region is not None
               else f"{case}_forced_retry" if forced else case)
        out = OUT / key
        out.mkdir(parents=True, exist_ok=True)
        work = out / "work"
        rec, art = attempt(key, spec, radius, work, False)
        entry = {"radius_mm": radius, "half_model": spec["half"], "attempts": [rec]}
        q = rec["quality"]
        inverted = q["inverted_min_det_jac_le_0"] + q["zero_volume"]
        # D-24: one retry with SecondOrderLinear = true when elements invert.
        entry["d24_retry_forced"] = forced
        if inverted or rec["gmsh_reports_negative_jacobian"] or forced:
            retry, art = attempt(key, spec, radius, out / "work_retry", True)
            entry["attempts"].append(retry)
            entry["d24_retry_ran"] = True
            rec = retry
            q = rec["quality"]
            inverted = q["inverted_min_det_jac_le_0"] + q["zero_volume"]
        else:
            entry["d24_retry_ran"] = False
        entry["final"] = {"second_order_linear": rec["second_order_linear"],
                          "nodes": rec["femmesh"]["nodes"], "c3d10": rec["femmesh"]["volumes"],
                          "mesh_seconds": rec["mesh_seconds"], "inverted": int(inverted),
                          "accepted": q["accepted"]}
        # D-24's second failure: the candidate would be `unverified`.
        entry["d24_outcome"] = ("ok" if not inverted else
                                "unverified_mesh_failure" if entry["d24_retry_ran"] else "inverted")
        section_view(out, key, radius, art[0], art[1], art[2], art[3])
        report.setdefault("cases", {})[key] = entry
        report_path.write_text(json.dumps(report, indent=2))
        print(key, json.dumps(entry["final"]), entry["d24_outcome"],
              json.dumps(q["acceptance"]), flush=True)
        if key in D24_CASES and not q["accepted"]:
            failures.append(key)

    report["d24_cases"] = D24_CASES
    report["d24_cases_not_accepted"] = failures
    report_path.write_text(json.dumps(report, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())

"""M2A.2: mesh the frozen GE working copy at three levels and report mesh quality.

Opens data/ge_manual/Iteration1_manual.FCStd (M2A.1), and for each level builds
the same objects a person creates by hand in the FEM Workbench: an Analysis, a
Gmsh mesh of `Bracket` (second-order tetrahedra, C3D10) and four MeshRegions,
whose faces are chosen by geometric predicate:

- pin_bore:     both lug bores (r 9.557) and their chamfer cones;
- arm_root:     curved blend faces where the clevis arms meet the body;
- nut_seat:     the four nut-seat annuli, bolt-hole walls and seat blends;
- thin_section: faces within 1 mm of the thinnest wall samples from M2A.1.

Gmsh is run through FreeCAD's own GmshTools (same .geo as the GUI). The .unv it
writes is then read into the Gmsh API for quality: signed Jacobian, scaled
Jacobian, gamma and edge aspect ratio per element, judged against thresholds
fixed in THRESHOLDS before any mesh is generated.

Writes, per level, data/ge_manual/mesh/<level>/ (FCStd with Analysis + mesh,
.geo, .brep, .unv; gitignored, derived from licensed CAD) and
out/ge_manual_mesh/<level>/ (histogram, section and worst-element views), plus
out/ge_manual_mesh/mesh-quality.json.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/ge_manual_mesh.py [--levels L1 L2 L3]
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import FreeCAD  # noqa: E402
import ObjectsFem  # noqa: E402
import Part  # noqa: E402
from femmesh.gmshtools import GmshTools  # noqa: E402

WORKING = ROOT / "data" / "ge_manual" / "Iteration1_manual.FCStd"
GEOMETRY_CHECK = ROOT / "out" / "ge_manual_geometry" / "geometry-check.json"
DATA = ROOT / "data" / "ge_manual" / "mesh"
OUT = ROOT / "out" / "ge_manual_mesh"

# Sizes in mm; curvature is Gmsh elements per 2*pi of radius. L1 starts from the
# M2 evidence (max 4, min 1) at L2; each level refines every size by 1.25-1.5x.
# FreeCAD's default curvature of 12 alone puts ~1 mm elements on all 151 r2
# fillets (982k nodes at max 4), so curvature is a level parameter too. L3 is
# capped near 0.85M nodes: this ccx links SPOOLES only and the host has 16 GB.
# A region size below the global minimum would be clamped.
LEVELS = {
    "L1": {"max": 5.0, "min": 1.0, "region": 2.0, "curvature": 4},
    "L2": {"max": 4.0, "min": 1.0, "region": 1.5, "curvature": 6},
    "L3": {"max": 3.0, "min": 0.75, "region": 1.0, "curvature": 9},
}

# Acceptance thresholds, fixed before meshing (Gmsh 4.15.2 definitions, see doc).
THRESHOLDS = {
    "inverted_or_zero_volume_elements": 0,     # minDetJac <= 0 or |volume| ~ 0
    "min_scaled_jacobian_min": 0.1,            # Gmsh minSJ, every element
    "min_scaled_jacobian_p0_1": 0.3,           # 0.1th percentile
    "gamma_min": 0.05,                         # Gmsh gamma, every element
    "gamma_below_0_2_fraction_max": 0.001,     # at most 0.1 % of elements
    "aspect_ratio_max": 20.0,                  # maxEdge/minEdge, every element
    "aspect_ratio_p99_9_max": 8.0,
}

GMSH_PREFS = "User parameter:BaseApp/Preferences/Mod/Fem/Gmsh"
GMSH_THREADS = 1

TET10 = 11  # Gmsh element type: 10-node second-order tetrahedron


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vec(v):
    return np.array([v.x, v.y, v.z])


def select_regions(shape, geom):
    """Face names (1-based FreeCAD FaceN) for each MeshRegion, by predicate."""
    pin_ref = np.array(geom["frame"]["pin_ref_in_deck_frame"])
    pin_axis = np.array(geom["frame"]["pin_axis_in_deck_frame"])
    bolts = [np.array(b["axis_xy_deck"]) for b in geom["bolts"]]
    seat_z = geom["bolts"][0]["nut_seat"]["height_above_base_bottom_mm"]
    thin = [np.array(p[:3]) for p in geom["wall_thickness_sampled"]["thinnest_locations_deck"]]

    def radial_to_pin(p):
        d = p - pin_ref
        return np.linalg.norm(d - np.dot(d, pin_axis) * pin_axis)

    regions = {"pin_bore": [], "arm_root": [], "nut_seat": [], "thin_section": []}
    for i, f in enumerate(shape.Faces, 1):
        s, c = f.Surface, vec(f.CenterOfMass)
        kind = s.__class__.__name__
        name = f"Face{i}"
        near_bolt = min(np.linalg.norm(c[:2] - b) for b in bolts)
        if (kind == "Cylinder" and abs(s.Radius - 9.557) < 0.01) or (kind == "Cone" and radial_to_pin(c) < 12.0):
            regions["pin_bore"].append(name)
        elif kind != "Plane" and -97 < c[1] < -52 and -40 < c[0] < 40 and 10 < c[2] < 40:
            regions["arm_root"].append(name)
        if near_bolt < 12.0 and c[2] < 12.0 and (
            (kind == "Cylinder" and s.Radius < 6.0)
            or (kind == "Plane" and abs(c[2] - seat_z) < 0.01)
            or kind == "Toroid"
        ):
            regions["nut_seat"].append(name)
        if any(f.distToShape(Part.Vertex(FreeCAD.Vector(*p)))[0] < 1.0 for p in thin):
            regions["thin_section"].append(name)
    return regions


def build(level, sizes, regions):
    """Analysis + Gmsh mesh + MeshRegions in a fresh copy of the working document."""
    doc = FreeCAD.openDocument(str(WORKING))
    part = doc.getObject("Bracket")
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    mesh = ObjectsFem.makeMeshGmsh(doc, "Mesh")
    analysis.addObject(mesh)
    mesh.Shape = part
    mesh.ElementDimension = "3D"
    mesh.ElementOrder = "2nd"
    mesh.SecondOrderLinear = False
    mesh.HighOrderOptimize = "Optimization"
    mesh.CharacteristicLengthMax = sizes["max"]
    mesh.CharacteristicLengthMin = sizes["min"]
    mesh.MeshSizeFromCurvature = sizes["curvature"]
    # Not the FreeCAD default. Without it every level failed the minSJ/gamma
    # thresholds on slivers at the file's tiny B-spline faces (see the doc).
    mesh.OptimizeNetgen = True
    for name, faces in regions.items():
        mr = ObjectsFem.makeMeshRegion(doc, mesh, sizes["region"], f"Region_{name}")
        mr.References = [(part, tuple(faces))]
    doc.recompute()
    return doc, mesh


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
    """FreeCAD's GmshTools pipeline, with the working directory under our control.

    Gmsh runs single-threaded: with FreeCAD's default (all cores) the same input
    gave 321,322 then 321,501 nodes. The thread count is a FreeCAD preference
    (FEM > Gmsh), so it is set for this run and restored afterwards.
    """
    prefs = FreeCAD.ParamGet(GMSH_PREFS)
    had = "NumOfThreads" in prefs.GetInts()
    old = prefs.GetInt("NumOfThreads")
    prefs.SetInt("NumOfThreads", GMSH_THREADS)
    try:
        return _run_gmsh(mesh, workdir)
    finally:
        if had:
            prefs.SetInt("NumOfThreads", old)
        else:
            prefs.RemInt("NumOfThreads")


def _run_gmsh(mesh, workdir):
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
    return tools, err, elapsed


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
    counts = {gmsh.model.mesh.getElementProperties(t)[0]: len(e) for t, e in zip(*gmsh.model.mesh.getElements()[:2])}
    version = gmsh.__version__
    gmsh.finalize()
    q["aspect"] = q["maxEdge"] / q["minEdge"]
    return tags, conn, xyz, q, counts, version


def summarise(tags, conn, xyz, q):
    def dist(a):
        return {"min": float(a.min()), "p0_1": float(np.percentile(a, 0.1)), "p1": float(np.percentile(a, 1)),
                "p5": float(np.percentile(a, 5)), "median": float(np.median(a)), "max": float(a.max())}

    centroid = xyz[conn[:, :4]].mean(axis=1)
    zero_vol = np.abs(q["volume"]) < 1e-9 * np.abs(q["volume"]).mean()
    worst = np.argsort(q["minSJ"])[:10]
    s = {
        "elements_tet10": int(len(tags)),
        "inverted_min_det_jac_le_0": int((q["minDetJac"] <= 0).sum()),
        "zero_volume": int(zero_vol.sum()),
        "min_scaled_jacobian": dist(q["minSJ"]),
        "gamma": dist(q["gamma"]),
        "gamma_below_0_2_fraction": float((q["gamma"] < 0.2).mean()),
        "gamma_below_threshold_count": int((q["gamma"] < THRESHOLDS["gamma_min"]).sum()),
        "aspect_ratio": {k: float(v) for k, v in dist(-q["aspect"]).items()},
        "worst_by_min_scaled_jacobian": [
            {"element": int(tags[i]), "minSJ": round(float(q["minSJ"][i]), 4), "gamma": round(float(q["gamma"][i]), 4),
             "aspect": round(float(q["aspect"][i]), 2), "centroid_deck": centroid[i].round(2).tolist()} for i in worst],
        "worst_by_gamma": [
            {"element": int(tags[i]), "minSJ": round(float(q["minSJ"][i]), 4), "gamma": round(float(q["gamma"][i]), 4),
             "aspect": round(float(q["aspect"][i]), 2), "min_edge_mm": round(float(q["minEdge"][i]), 4),
             "centroid_deck": centroid[i].round(2).tolist()} for i in np.argsort(q["gamma"])[:10]],
    }
    # dist() on -aspect gives (-max, ..., -min); flip back into ascending aspect terms.
    a = s["aspect_ratio"]
    s["aspect_ratio"] = {"min": -a["max"], "median": -a["median"], "p99": -a["p1"], "p99_9": -a["p0_1"], "max": -a["min"]}
    t = THRESHOLDS
    s["acceptance"] = {
        "inverted_or_zero_volume": s["inverted_min_det_jac_le_0"] + s["zero_volume"] <= t["inverted_or_zero_volume_elements"],
        "min_scaled_jacobian_min": s["min_scaled_jacobian"]["min"] >= t["min_scaled_jacobian_min"],
        "min_scaled_jacobian_p0_1": s["min_scaled_jacobian"]["p0_1"] >= t["min_scaled_jacobian_p0_1"],
        "gamma_min": s["gamma"]["min"] >= t["gamma_min"],
        "gamma_below_0_2_fraction": s["gamma_below_0_2_fraction"] <= t["gamma_below_0_2_fraction_max"],
        "aspect_ratio_max": s["aspect_ratio"]["max"] <= t["aspect_ratio_max"],
        "aspect_ratio_p99_9": s["aspect_ratio"]["p99_9"] <= t["aspect_ratio_p99_9_max"],
    }
    s["accepted"] = all(s["acceptance"].values())
    return s, centroid


def plots(level, out, conn, xyz, q, summary, part_shape):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyvista as pv

    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for a, (key, label, thr) in zip(ax, [("minSJ", "min scaled Jacobian (Gmsh minSJ)", THRESHOLDS["min_scaled_jacobian_min"]),
                                         ("gamma", "gamma (Gmsh)", THRESHOLDS["gamma_min"]),
                                         ("aspect", "aspect ratio maxEdge/minEdge", THRESHOLDS["aspect_ratio_max"])]):
        a.hist(q[key], bins=100, color="#4a78b5", log=True)
        a.axvline(thr, color="#b2182b", ls="--", label=f"threshold {thr}")
        a.set_xlabel(label)
        a.set_ylabel("elements (log)")
        a.legend()
    fig.suptitle(f"{level}: {len(q['minSJ'])} C3D10 elements")
    fig.tight_layout()
    fig.savefig(out / "quality_histograms.png", dpi=110)
    plt.close(fig)

    # Linear (corner-node) tets for display, coloured by minSJ.
    corners = conn[:, :4]
    used, inv = np.unique(corners, return_inverse=True)
    grid = pv.UnstructuredGrid(np.c_[np.full(len(corners), 4), inv.reshape(-1, 4)].ravel(),
                               np.full(len(corners), pv.CellType.TETRA), xyz[used])
    grid.cell_data["minSJ"] = q["minSJ"]
    sections = {
        "lug_bore": ((0, 1, 0), (-21.0, -60.48, 44.7)),
        "arm_root": ((1, 0, 0), (-12.0, -74.8, 20.0)),
        "bolt_B2_B1": ((0, 1, 0), (0.0, 0.0, 4.0)),
        "thin_wall_z21": ((0, 0, 1), (10.0, -74.0, 21.0)),
    }
    for name, (normal, origin) in sections.items():
        clipped = grid.clip(normal=normal, origin=origin, crinkle=True)
        p = pv.Plotter(off_screen=True, window_size=(1300, 950))
        p.set_background("white")
        p.add_mesh(clipped, scalars="minSJ", cmap="viridis", clim=(0, 1), show_edges=True, edge_color="#333333", line_width=0.3)
        p.add_text(f"{level} section '{name}': clip normal {normal} at {origin}; colour = minSJ", font_size=11, color="black")
        p.camera_position = [np.array(origin) + np.array(normal) * -250, origin, (0, 0, 1) if normal[2] == 0 else (0, 1, 0)]
        p.enable_parallel_projection()
        p.reset_camera()
        p.screenshot(str(out / f"section_{name}.png"))
        p.close()

    verts, tris = part_shape.tessellate(0.2)
    surf = pv.PolyData(np.array([[v.x, v.y, v.z] for v in verts]), np.c_[np.full(len(tris), 3), np.array(tris)].ravel())
    worst = summary["worst_by_min_scaled_jacobian"]
    idx = [int(np.where(q["_tags"] == w["element"])[0][0]) for w in worst]
    p = pv.Plotter(off_screen=True, window_size=(1400, 1000))
    p.set_background("white")
    p.add_mesh(surf, color="#cccccc", opacity=0.25)
    p.add_mesh(grid.extract_cells(idx), color="#b2182b", show_edges=True)
    p.add_point_labels(np.array([w["centroid_deck"] for w in worst]),
                       [f"#{w['element']} SJ={w['minSJ']}" for w in worst], font_size=12, point_size=6, always_visible=True)
    p.view_isometric()
    p.add_text(f"{level}: 10 worst elements by minSJ", font_size=12, color="black")
    p.screenshot(str(out / "worst_elements.png"))
    p.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", nargs="+", default=list(LEVELS))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    geom = json.loads(GEOMETRY_CHECK.read_text())
    report_path = OUT / "mesh-quality.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report.update({"working_copy": str(WORKING.relative_to(ROOT)), "working_copy_sha256": sha256(WORKING),
                   "freecad_version": ".".join(FreeCAD.Version()[:3]), "thresholds": THRESHOLDS,
                   "gmsh_threads": GMSH_THREADS,
                   "levels_defined": LEVELS})

    probe = FreeCAD.openDocument(str(WORKING))
    shape = probe.getObject("Bracket").Shape.copy()
    regions = select_regions(shape, geom)
    FreeCAD.closeDocument(probe.Name)
    report["regions"] = {k: {"faces": v, "count": len(v)} for k, v in regions.items()}

    for level in args.levels:
        sizes = LEVELS[level]
        work, out = DATA / level, OUT / level
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        out.mkdir(parents=True, exist_ok=True)
        doc, mesh = build(level, sizes, regions)
        tools, err, elapsed = run_gmsh(mesh, work)
        fem = mesh.FemMesh
        rec = {"sizes_mm": sizes, "settings": settings(mesh), "gmsh_binary": tools.gmsh_bin,
               "gmsh_stderr": err.strip().splitlines()[-20:], "elapsed_s": round(elapsed, 1),
               "femmesh": {"nodes": fem.NodeCount, "volumes": fem.VolumeCount, "faces": fem.FaceCount,
                           "edges": fem.EdgeCount, "tetra": fem.TetraCount}}
        unv = Path(tools.temp_file_mesh)
        doc.saveAs(str(work / f"Iteration1_mesh_{level}.FCStd"))
        FreeCAD.closeDocument(doc.Name)
        rec["files"] = {p.name: sha256(p) for p in sorted(work.iterdir()) if p.is_file() and p.suffix != ".FCBak"}

        tags, conn, xyz, q, counts, version = quality(unv)
        rec["gmsh_api_version"] = version
        rec["unv_element_counts_by_type"] = counts
        rec["counts_match_femmesh"] = len(tags) == fem.VolumeCount
        # Reruns reproduce counts and connectivity exactly, but node coordinates
        # differ by up to ~1e-5 mm, so the .unv bytes (and sha256) do not repeat.
        rec["connectivity_sha256"] = hashlib.sha256(np.ascontiguousarray(conn, dtype=np.int64).tobytes()).hexdigest()
        summary, _ = summarise(tags, conn, xyz, q)
        rec["quality"] = summary
        q["_tags"] = tags
        plots(level, out, conn, xyz, q, summary, shape)
        report.setdefault("levels", {})[level] = rec
        report_path.write_text(json.dumps(report, indent=2))
        print(level, json.dumps({k: rec[k] for k in ("elapsed_s", "femmesh", "counts_match_femmesh")}),
              json.dumps(summary["acceptance"]), "accepted" if summary["accepted"] else "REJECTED", flush=True)


if __name__ == "__main__":
    main()

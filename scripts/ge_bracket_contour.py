"""M2.6: render the LC1 contour by hand and judge whether it is readable.

REQ-OPT-001 is normative and has two halves: a **fixed camera set** and a
**legend range locked across all iterations of a run**. requirements.md section
8 also fixes the ordering - the camera set, image size, colormap and legend
scheme are settled in M2, by eye on `ge_bracket`, before any renderer is
written. This script is that judgement, not the renderer it will justify.

The question the issue asks is narrow: at this image size, camera count and
colormap, can an engineer tell `arm_root_fillet` from `clevis_arm` from
`bolt_boss`? That is answered with two measurements rather than an impression,
because "it looks fine to me" is not a setting anyone can re-derive later:

- **visibility** - each region's visible pixel count per camera, from a flat
  region-id pass. A region no camera shows cannot be judged at all, and that is
  a camera-set finding, not a colormap one.
- **separation** - the CIE Lab distance between regions' median rendered
  colours, over the pixels each region actually occupies. Two regions whose
  colours land within a just-noticeable difference are not distinguishable
  however pretty the image is.

Reads the solved field from out/lc1_solve (M2.5), cached as field.npz so the
43 MB document is opened once. Run with the FEM environment's Python
(scripts/fem_env.py finds it):

    $FEM_PYTHON scripts/ge_bracket_contour.py extract
    $FEM_PYTHON scripts/ge_bracket_contour.py study
    $FEM_PYTHON scripts/ge_bracket_contour.py render [--scheme allowable] [--cmap turbo]

Writes out/ge_bracket_contour/. Exit 0 when the stage completed, 2 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "out" / "ge_bracket_contour"
FIELD = OUT / "field.npz"
SOLVE = ROOT / "out" / "lc1_solve"

# The LC1 record's allowable, which every legend scheme is anchored to.
ALLOWABLE_MPA = 602.1

# A Triangle6 carries a quadratic field; its three corners do not. Splitting each
# into four linear triangles keeps the surface peak - taking corners alone reads
# 616.7 MPa where the solve found 630.6.
TRI6_SUBDIVISION = [(0, 3, 5), (3, 1, 4), (5, 4, 2), (3, 4, 5)]

# The three regions the issue names, in the order it names them.
JUDGED = ("arm_root_fillet", "clevis_arm", "bolt_boss")

# A just-noticeable difference in CIE Lab is about 2.3; below that two colours
# are the same colour to a viewer. 10 is the floor for "reads as different at a
# glance", which is the bar a contour has to clear.
DELTA_E_JND = 2.3
DELTA_E_GLANCE = 10.0

# A region needs enough pixels for its median colour to mean anything. Held as a
# fraction of the frame so it means the same at both image sizes: 0.05 % is
# 960 px at 1600x1200 and 240 px at 800x600. Below it the region is recorded as
# not shown and the row is not scored - a camera that cannot see a region must
# not win on the pairs it happens to have, which is what an unguarded minimum
# over present pairs does. The `top` camera showed exactly that: zero bolt_boss
# pixels, one pair instead of three, and the best score in the table.
MIN_REGION_FRACTION = 0.0005


def camera_set(bounds):
    """The fixed camera set: (name, direction, up) with an explicit view vector.

    Directions are fixed in part coordinates and never re-derived per iteration,
    so two iterations of one run frame the part identically even if the geometry
    moves. `iso` matches the convention ge_geometry_compare.py already uses.
    """
    return [
        ("iso", (-1, -1, 1), (0, 0, 1)),
        ("front", (0, -1, 0), (0, 0, 1)),
        ("top", (0, 0, 1), (0, 1, 0)),
        ("arm_root", (1, -0.35, 0.25), (0, 0, 1)),
    ]


def legend_schemes(vm):
    """Candidate locked ranges. Every one is a constant of the run, not the frame.

    `allowable` is the only scheme whose colour means something physical on its
    own - red is at the limit - but it spends most of the bar on stresses the
    part never reaches. The others trade that meaning for resolution where the
    field actually lives.
    """
    return {
        "allowable": (0.0, ALLOWABLE_MPA),
        "allowable_half": (0.0, ALLOWABLE_MPA / 2),
        "p99": (0.0, float(np.percentile(vm, 99))),
        "log_allowable": (1.0, ALLOWABLE_MPA),
    }


def srgb_to_lab(rgb):
    """sRGB 0-255 to CIE Lab, D65. Vectorised over the last axis."""
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(a, b):
    """CIE76 distance. Coarser than CIEDE2000 but never flatters a difference."""
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def extract():
    """Cache the solved surface field and its D-06 region labels from M2.5."""
    import FreeCAD

    import ge_bracket_labels as gl
    from parts import ge_bracket as gb

    doc = FreeCAD.openDocument(str(SOLVE / "lc1_solve.FCStd"))
    fm = doc.getObject("Mesh").FemMesh
    res = doc.getObject("CCX_Results")
    vm_by_node = dict(zip(res.NodeNumbers, res.vonMises))
    disp_by_node = dict(zip(res.NodeNumbers, res.DisplacementVectors))

    # The surface triangles come from the D-06 groups, so a triangle's region
    # label still originates at the geometric predicate (D-04, REQ-OPT-008).
    # M2.4 measured these groups as a clean partition of the surface: every
    # triangle covered, no element in two regions.
    got = gl.femmesh_groups(fm)
    regions = list(gb.REGIONS)
    tris, tri_region, tri6 = [], [], {}
    for ri, region in enumerate(regions):
        ids = sorted(got.get((region, "Face"), ()))
        tri6[region] = len(ids)
        for eid in ids:
            n = fm.getElementNodes(eid)
            if len(n) != 6:
                raise RuntimeError(f"element {eid} has {len(n)} nodes, expected a Triangle6")
            for a, b, c in TRI6_SUBDIVISION:
                tris.append((n[a], n[b], n[c]))
                tri_region.append(ri)

    nodes = fm.Nodes
    used = sorted({n for t in tris for n in t})
    index = {n: i for i, n in enumerate(used)}
    xyz = np.array([[nodes[n].x, nodes[n].y, nodes[n].z] for n in used])
    cells = np.array([[index[n] for n in t] for t in tris], dtype=np.int64)
    vm = np.array([vm_by_node[n] for n in used])
    disp = np.array([disp_by_node[n].Length for n in used])

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FIELD, xyz=xyz, cells=cells, vm=vm, disp=disp,
                        tri_region=np.array(tri_region, dtype=np.int64),
                        regions=np.array(regions),
                        tri6_counts=np.array([tri6[r] for r in regions]))
    FreeCAD.closeDocument(doc.Name)

    # The cache has to reproduce M2.5's headline numbers exactly, or the contour
    # is of a different field than the one the milestone reported.
    solved = json.loads((SOLVE / "result.json").read_text())["result"]
    checks = {
        "surface_vm_max_mpa": round(float(vm.max()), 1),
        "solve_raw_peak_mpa": solved["raw_peak_vm"]["mpa"],
        "surface_disp_max_mm": round(float(disp.max()), 4),
        "solve_max_disp_mm": solved["max_disp_mm"],
        "surface_nodes": len(xyz), "triangles": len(cells),
        "tri6_per_region": tri6,
    }
    checks["matches_solve"] = (
        checks["surface_vm_max_mpa"] == checks["solve_raw_peak_mpa"]
        and checks["surface_disp_max_mm"] == checks["solve_max_disp_mm"])
    return checks


def load_field():
    if not FIELD.exists():
        raise SystemExit(f"no cached field at {FIELD}; run `extract` first")
    d = np.load(FIELD, allow_pickle=True)
    return (d["xyz"], d["cells"], d["vm"], d["tri_region"], [str(r) for r in d["regions"]])


def surface(xyz, cells):
    import pyvista as pv
    return pv.PolyData(xyz, np.c_[np.full(len(cells), 3), cells].ravel())


def frame(plotter, mesh, direction, up, zoom=1.15):
    """Point the camera down a fixed direction under parallel projection.

    Parallel projection is not cosmetic: under perspective, apparent size tracks
    how close the camera sits, so two iterations of one run would not be
    comparable even with the same camera position.
    """
    centre = np.array(mesh.center)
    span = float(mesh.length)
    plotter.camera_position = [centre + np.array(direction, dtype=float) * span, centre, up]
    plotter.enable_parallel_projection()
    plotter.reset_camera()
    plotter.camera.zoom(zoom)


def region_mask_pass(xyz, cells, tri_region, regions, cam, size):
    """Flat region-id render: which pixels each region owns, per camera.

    Rendered with lighting off and one exact colour per region, so a pixel's
    colour is a region id and not a shaded approximation of one.
    """
    import pyvista as pv

    mesh = surface(xyz, cells)
    # Distinct, exactly-recoverable colours; 8 regions fit in the low bits.
    ids = np.array([[(i + 1) * 40, 255 - (i + 1) * 30, (i + 1) * 20] for i in range(len(regions))])
    mesh.cell_data["rgb"] = ids[tri_region].astype(np.uint8)

    pv.OFF_SCREEN = True
    plotter = pv.Plotter(off_screen=True, window_size=size)
    plotter.set_background("black")
    plotter.add_mesh(mesh, scalars="rgb", rgb=True, lighting=False, show_scalar_bar=False)
    frame(plotter, mesh, cam[1], cam[2])
    image = np.asarray(plotter.screenshot(return_img=True))
    plotter.close()

    masks = {}
    for ri, region in enumerate(regions):
        masks[region] = np.all(np.abs(image.astype(int) - ids[ri]) <= 2, axis=-1)
    return masks, image.shape[0] * image.shape[1]


def contour_pass(xyz, cells, vm, cam, size, cmap, clim, log):
    """The contour as the pipeline would render it, at one camera."""
    import pyvista as pv

    mesh = surface(xyz, cells)
    mesh.point_data["vm"] = vm
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(off_screen=True, window_size=size)
    plotter.set_background("white")
    plotter.add_mesh(mesh, scalars="vm", cmap=cmap, clim=clim, log_scale=log,
                     smooth_shading=True, show_scalar_bar=False)
    frame(plotter, mesh, cam[1], cam[2])
    image = np.asarray(plotter.screenshot(return_img=True))
    plotter.close()
    return image


def study(sizes, cmaps, scheme_names):
    """Measure visibility and separation over every candidate setting."""
    xyz, cells, vm, tri_region, regions = load_field()
    schemes = legend_schemes(vm)
    cams = camera_set(None)
    report = {"regions": regions, "judged": list(JUDGED),
              "allowable_mpa": ALLOWABLE_MPA,
              "delta_e": {"jnd": DELTA_E_JND, "glance": DELTA_E_GLANCE},
              "cameras": [c[0] for c in cams],
              "schemes": {k: [round(v[0], 1), round(v[1], 1)] for k, v in schemes.items()},
              "visibility": {}, "separation": []}

    # Visibility depends on the camera and the image size, never on the colormap.
    masks_by = {}
    for size in sizes:
        key = f"{size[0]}x{size[1]}"
        report["visibility"][key] = {}
        for cam in cams:
            masks, pixels = region_mask_pass(xyz, cells, tri_region, regions, cam, size)
            masks_by[(key, cam[0])] = masks
            report["visibility"][key][cam[0]] = {
                r: {"pixels": int(m.sum()), "percent": round(100 * m.sum() / pixels, 3)}
                for r, m in masks.items()}

    for size in sizes:
        key = f"{size[0]}x{size[1]}"
        for cmap in cmaps:
            for name in scheme_names:
                clim = schemes[name]
                log = name.startswith("log")
                for cam in cams:
                    image = contour_pass(xyz, cells, vm, cam, size, cmap,
                                         (max(clim[0], 1e-6), clim[1]) if log else clim, log)
                    masks = masks_by[(key, cam[0])]
                    floor = MIN_REGION_FRACTION * size[0] * size[1]
                    med, missing = {}, []
                    for region in JUDGED:
                        pix = image[masks[region]]
                        if len(pix) >= floor:
                            med[region] = np.median(pix[:, :3], axis=0)
                        else:
                            missing.append(region)
                    row = {"size": key, "cmap": cmap, "scheme": name, "camera": cam[0],
                           "pairs": {}, "not_shown": missing, "min_delta_e": None}
                    lab = {r: srgb_to_lab(c) for r, c in med.items()}
                    for i, a in enumerate(JUDGED):
                        for b in JUDGED[i + 1:]:
                            if a in lab and b in lab:
                                row["pairs"][f"{a}|{b}"] = round(delta_e(lab[a], lab[b]), 1)
                    # Scored only when every judged region is actually on screen.
                    if not missing:
                        row["min_delta_e"] = min(row["pairs"].values())
                    report["separation"].append(row)
    return report


def render(scheme, cmap, size, tag=None):
    """Write the contour at every camera in the set, with the legend locked."""
    import pyvista as pv

    xyz, cells, vm, tri_region, regions = load_field()
    clim = legend_schemes(vm)[scheme]
    log = scheme.startswith("log")
    mesh = surface(xyz, cells)
    mesh.point_data["vm"] = vm
    out = OUT / (tag or f"{scheme}_{cmap}")
    out.mkdir(parents=True, exist_ok=True)

    written = []
    for name, direction, up in camera_set(None):
        pv.OFF_SCREEN = True
        plotter = pv.Plotter(off_screen=True, window_size=size)
        plotter.set_background("white")
        plotter.add_mesh(mesh, scalars="vm", cmap=cmap,
                         clim=(max(clim[0], 1e-6), clim[1]) if log else clim,
                         log_scale=log, smooth_shading=True,
                         scalar_bar_args={"title": "von Mises (MPa)", "vertical": True,
                                          "position_x": 0.88, "position_y": 0.2,
                                          "height": 0.6, "width": 0.06,
                                          "fmt": "%.0f", "color": "black",
                                          "n_labels": 6})
        plotter.add_text(f"ge_bracket LC1 | {name} | legend {clim[0]:.0f}-{clim[1]:.0f} MPa "
                         f"locked | {cmap}", font_size=10, color="black")
        frame(plotter, mesh, direction, up)
        plotter.show_axes()
        png = out / f"{name}.png"
        plotter.screenshot(str(png))
        plotter.close()
        written.append(str(png.relative_to(ROOT)))
    return {"scheme": scheme, "clim_mpa": [round(c, 1) for c in clim], "cmap": cmap,
            "size": list(size), "log": log, "images": written}


SIMJEB = ROOT / "data" / "simjeb"
SIMJEB_DESIGN = 148
SIMJEB_LOAD_CASES = {"ver": "LC1 vertical", "hor": "LC2 horizontal",
                     "dia": "LC3 diagonal", "tor": "LC4 torsion"}
# The CSV's `surf` code is the only region-like label design 148 carries: 1 is
# free surface, 2 the bolt-hole surfaces, 3 the pin bore. Coarser than D-06, but
# it is the same question - can a viewer tell one named area from another.
SIMJEB_CLASSES = {1: "free_surface", 2: "bolt_holes", 3: "pin_bore"}


def simjeb_field(load_case):
    """Design 148's surface nodes and von Mises for one load case, with classes."""
    csv = SIMJEB / f"{SIMJEB_DESIGN}field.csv"
    header = csv.open().readline().strip().split(",")
    cols = [header.index(c) for c in ("surf", "x", "y", "z", f"{load_case}_stress")]
    table = np.loadtxt(csv, delimiter=",", skiprows=1, usecols=cols)
    surface = table[table[:, 0] != 0]
    return surface[:, 1:4], surface[:, 4], surface[:, 0].astype(int)


def simjeb(scheme_clim, cmap, size):
    """Apply the frozen ge_bracket settings to design 148, all four load cases.

    The issue calls this the harder test: a real bracket with a complex load
    path. A setting that only reads well on the simple part is a finding, so
    what this reports is whether the frozen legend still spans 148's field, not
    whether 148 can be made to look good with some other legend.
    """
    import pyvista as pv
    import vtk

    mesh = pv.read(SIMJEB / f"{SIMJEB_DESIGN}.obj")
    out = OUT / f"simjeb{SIMJEB_DESIGN}"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for lc, label in SIMJEB_LOAD_CASES.items():
        points, stress, klass = simjeb_field(lc)
        cloud = vtk.vtkPolyData()
        cloud.SetPoints(pv.vtk_points(points))
        locator = vtk.vtkStaticPointLocator()
        locator.SetDataSet(cloud)
        locator.BuildLocator()
        idx = np.array([locator.FindClosestPoint(p) for p in mesh.points])
        field, node_class = stress[idx], klass[idx]
        mesh.point_data["vm"] = field

        # How much of the frozen bar the field actually uses, and how much of the
        # field the bar cannot show at all.
        lo, hi = scheme_clim
        rows.append({
            "load_case": lc, "name": label,
            "median_mpa": round(float(np.median(field)), 1),
            "p99_mpa": round(float(np.percentile(field, 99)), 1),
            "max_mpa": round(float(field.max()), 1),
            "above_clim_percent": round(100 * float((field > hi).mean()), 2),
            "class_median_mpa": {name: round(float(np.median(field[node_class == code])), 1)
                                 for code, name in SIMJEB_CLASSES.items()
                                 if (node_class == code).any()},
        })

        pv.OFF_SCREEN = True
        plotter = pv.Plotter(off_screen=True, window_size=size)
        plotter.set_background("white")
        plotter.add_mesh(mesh, scalars="vm", cmap=cmap, clim=(lo, hi), smooth_shading=True,
                         scalar_bar_args={"title": "von Mises (MPa)", "vertical": True,
                                          "position_x": 0.88, "position_y": 0.2,
                                          "height": 0.6, "width": 0.06, "fmt": "%.0f",
                                          "color": "black", "n_labels": 6})
        plotter.add_text(f"SimJEB {SIMJEB_DESIGN} | {label} | legend {lo:.0f}-{hi:.0f} MPa "
                         f"locked | {cmap}", font_size=10, color="black")
        frame(plotter, mesh, (-1, -1, 1), (0, 0, 1))
        plotter.show_axes()
        plotter.screenshot(str(out / f"{lc}_iso.png"))
        plotter.close()
    return {"design": SIMJEB_DESIGN, "clim_mpa": [round(c, 1) for c in scheme_clim],
            "cmap": cmap, "size": list(size), "load_cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("extract", help="cache the solved surface field from M2.5")
    s = sub.add_parser("study", help="measure visibility and separation over the candidates")
    s.add_argument("--sizes", nargs="+", default=["1600x1200", "800x600"])
    s.add_argument("--cmaps", nargs="+", default=["turbo", "viridis", "coolwarm"])
    s.add_argument("--schemes", nargs="+", default=list(legend_schemes(np.array([1.0]))))
    r = sub.add_parser("render", help="write the contour at every camera")
    r.add_argument("--scheme", default="allowable")
    r.add_argument("--cmap", default="turbo")
    r.add_argument("--size", default="1600x1200")
    r.add_argument("--tag", default=None)
    j = sub.add_parser("simjeb", help="apply the frozen settings to SimJEB 148")
    j.add_argument("--clim", default="0x301", help="locked legend range, lo x hi in MPa")
    j.add_argument("--cmap", default="turbo")
    j.add_argument("--size", default="800x600")
    args = parser.parse_args()

    def wh(text):
        w, h = text.lower().split("x")
        return (int(w), int(h))

    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "extract":
        result = extract()
        (OUT / "extract.json").write_text(json.dumps(result, indent=2) + "\n")
        ok = result["matches_solve"]
        print(json.dumps(result, indent=2))
        print("ok  " if ok else "FAIL", "cache reproduces M2.5's peak and displacement")
    elif args.stage == "study":
        result = study([wh(s) for s in args.sizes], args.cmaps, args.schemes)
        (OUT / "study.json").write_text(json.dumps(result, indent=2) + "\n")
        rows = sorted((r for r in result["separation"] if r["min_delta_e"] is not None),
                      key=lambda r: -r["min_delta_e"])
        blind = sorted({(r["camera"], tuple(r["not_shown"]))
                        for r in result["separation"] if r["not_shown"]})
        for camera, absent in blind:
            print(f"note   camera {camera} never shows {', '.join(absent)}; "
                  f"its rows are unscored")
        print(f"{'size':>9} {'cmap':>9} {'scheme':>15} {'camera':>9}   min dE")
        for row in rows[:12]:
            print(f"{row['size']:>9} {row['cmap']:>9} {row['scheme']:>15} "
                  f"{row['camera']:>9}   {row['min_delta_e']:.1f}")
        ok = any(r["min_delta_e"] >= DELTA_E_GLANCE for r in rows)
        print("ok  " if ok else "FAIL", "some setting separates the three judged regions")
    elif args.stage == "simjeb":
        lo, hi = (float(v) for v in args.clim.lower().split("x"))
        result = simjeb((lo, hi), args.cmap, wh(args.size))
        (OUT / "simjeb.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        # The frozen bar has to span the harder part's field, not just this one's.
        ok = all(r["above_clim_percent"] < 1.0 for r in result["load_cases"])
        print("ok  " if ok else "FAIL",
              "the frozen legend spans design 148's field on every load case")
    else:
        result = render(args.scheme, args.cmap, wh(args.size), args.tag)
        print(json.dumps(result, indent=2))
        ok = True
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()

"""Gate 2a (M1.4): render a SimJEB stress field to PNG off-screen with pyvista.

Maps the von Mises field of SimJEB design 148 from its nodal CSV onto its
surface mesh and renders it with no window, the way the pipeline will render
contour images for the vision model.

Run with the FEM environment's Python, after scripts/fetch_simjeb.py:
    vendor/fem-env/bin/python scripts/render_field.py [--load-case ver|hor|dia|tor]

Writes out/gate2a/148_<lc>_stress.png and prints a JSON result. Exit 0 when
the image was written and is not blank, 2 otherwise.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "simjeb"
OUT = ROOT / "out" / "gate2a"
DESIGN = 148
MATCH_TOL = 1e-3  # mm; OBJ vertices are the CSV's surface nodes, rewritten
LOAD_CASES = {"ver": "LC1 vertical", "hor": "LC2 horizontal", "dia": "LC3 diagonal", "tor": "LC4 torsion"}


def load_field(load_case):
    """Surface nodes' coordinates and von Mises stress (MPa) for one load case.

    `surf` is 0 for interior nodes, 1 for free surface, 2 for the bolt-hole
    surfaces and 3 for the pin bore. The peak stress sits on the bolt holes,
    so every nonzero code is surface.
    """
    csv = DATA / f"{DESIGN}field.csv"
    header = csv.open().readline().strip().split(",")
    cols = [header.index(c) for c in ("surf", "x", "y", "z", f"{load_case}_stress")]
    table = np.loadtxt(csv, delimiter=",", skiprows=1, usecols=cols)
    surface = table[table[:, 0] != 0]
    return surface[:, 1:4], surface[:, 4]


def map_to_mesh(mesh, points, values):
    """Give each mesh vertex the value of the node at its position."""
    cloud = vtk.vtkPolyData()
    cloud.SetPoints(pv.vtk_points(points))
    locator = vtk.vtkStaticPointLocator()
    locator.SetDataSet(cloud)
    locator.BuildLocator()
    idx = np.array([locator.FindClosestPoint(p) for p in mesh.points])
    dist = np.linalg.norm(mesh.points - points[idx], axis=1)
    if dist.max() > MATCH_TOL:
        raise RuntimeError(f"{(dist > MATCH_TOL).sum()} mesh vertices have no node within "
                           f"{MATCH_TOL} mm (max {dist.max():.3g} mm)")
    return values[idx], float(dist.max())


def render(mesh, field, label, png):
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 1200))
    plotter.add_mesh(mesh, scalars=field, cmap="turbo", smooth_shading=True,
                     scalar_bar_args={"title": "MPa", "vertical": True, "position_x": 0.88,
                                      "position_y": 0.2, "height": 0.6, "width": 0.06,
                                      "fmt": "%.0f", "color": "black"})
    plotter.add_text(f"SimJEB design {DESIGN}: von Mises stress, {label}", font_size=12,
                     color="black")
    plotter.view_isometric()
    plotter.camera.zoom(1.1)
    plotter.set_background("white")
    plotter.show_axes()
    plotter.screenshot(str(png))
    plotter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--load-case", choices=LOAD_CASES, default="ver")
    args = parser.parse_args()
    lc = args.load_case
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{DESIGN}_{lc}_stress.png"
    result = {"design": DESIGN, "load_case": LOAD_CASES[lc], "ok": False, "timings_s": {},
              "pyvista": pv.__version__, "vtk": vtk.vtkVersion.GetVTKVersion()}
    timings = result["timings_s"]
    try:
        t = time.perf_counter()
        points, stress = load_field(lc)
        mesh = pv.read(DATA / f"{DESIGN}.obj")
        timings["read"] = round(time.perf_counter() - t, 3)

        t = time.perf_counter()
        field, max_dist = map_to_mesh(mesh, points, stress)
        timings["map"] = round(time.perf_counter() - t, 3)

        t = time.perf_counter()
        render(mesh, field, LOAD_CASES[lc], png)
        timings["render"] = round(time.perf_counter() - t, 3)

        image = pv.read(png).point_data.active_scalars
        if image is None or np.asarray(image).std() < 1.0:
            raise RuntimeError("rendered image is blank")
        result.update({
            "png": str(png.relative_to(ROOT)),
            "surface_nodes": len(points),
            "mesh_vertices": mesh.n_points,
            "mesh_faces": mesh.n_cells,
            "match_max_dist_mm": max_dist,
            "stress_max_mpa": round(float(field.max()), 1),
            "stress_max_mpa_csv_surface": round(float(stress.max()), 1),
            "ok": True,
        })
    except Exception as e:  # errors as values
        result["error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

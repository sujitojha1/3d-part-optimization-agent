"""Gate 3 (M1.7): FreeCAD's bundled CalculiX cantilever solves headless.

Builds FreeCAD's *CalculiX Cantilever 3D* example (femexamples
ccx_cantilever_faceload: an 8000 x 1000 x 1000 mm steel box, one end face
fixed, 9 MN in -z on the other) and solves it through femtools.ccxtools the
way the pipeline will: check_prerequisites -> write_inp_file -> ccx_run ->
load_results, with the conda-forge ccx on PATH.

- bundled: the example's own Tet10 mesh. The gate: it must reproduce the
  published tip z-displacement, -86.93 mm.
- gmsh_<order>: the same analysis re-meshed by FemMeshGmsh at its default size.
  Recorded, not gated: these show what the published number depends on.

Run with the FEM environment's Python:
    vendor/fem-env/bin/python scripts/gate3_ccx.py

Writes each case's .inp/.frd/.dat under out/gate3/<case>/ and a JSON result to
out/gate3/result.json. Exit 0 when the bundled case reproduces -86.93 mm, 2
otherwise.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "gate3"
PUBLISHED_DZ_MM = -86.93  # FEM CalculiX Cantilever 3D, freecad-tutorials.md §4.3
TOL_MM = 0.005  # the published value's rounding
CLOSED_FORM_DZ_MM = -87.77  # F L^3 / 3 E I, Euler-Bernoulli


def mesh_object(doc):
    return next(o for o in doc.Objects if o.isDerivedFrom("Fem::FemMeshObject"))


def solve(case, remesh_order=None):
    """Build the example, optionally re-mesh with Gmsh, and solve it."""
    from femexamples.ccx_cantilever_faceload import setup
    from femmesh.gmshtools import GmshTools
    from femtools import ccxtools

    result = {"case": case, "ok": False, "timings_s": {}}
    timings = result["timings_s"]
    work = OUT / case
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    t = time.perf_counter()
    # test_mode=True only makes setup() load the bundled mesh instead of meshing.
    doc = setup(test_mode=True)
    mesh = mesh_object(doc)
    if remesh_order:
        mesh.ElementOrder = remesh_order
        error = GmshTools(mesh).create_mesh()
        if error:
            raise RuntimeError(f"gmsh: {error}")
        doc.recompute()
    timings["setup_mesh"] = round(time.perf_counter() - t, 3)
    femmesh = mesh.FemMesh
    result["mesh"] = {"source": f"gmsh {remesh_order}" if remesh_order else "bundled",
                      "nodes": femmesh.NodeCount, "volumes": femmesh.VolumeCount,
                      "nodes_per_element": len(femmesh.getElementNodes(femmesh.Volumes[0]))}

    fea = ccxtools.FemToolsCcx(doc.Analysis, doc.CalculiXCcxTools)
    fea.update_objects()
    fea.setup_working_dir(str(work), create=True)
    problems = fea.check_prerequisites()
    if problems:
        raise RuntimeError(f"prerequisites: {problems}")

    t = time.perf_counter()
    fea.write_inp_file()
    timings["write_inp"] = round(time.perf_counter() - t, 3)
    # A failed write can leave inp_file_name empty although the file exists, so
    # check the file on disk, not the return value (freecad-tutorials §4.2).
    written = sorted(work.glob("*.inp"))
    if not written:
        raise RuntimeError(f"no .inp written in {work} (returned {fea.inp_file_name!r})")
    result["inp"] = str(written[0].relative_to(ROOT))

    t = time.perf_counter()
    exit_code = fea.ccx_run()
    timings["ccx_run"] = round(time.perf_counter() - t, 3)
    result["ccx_binary"] = fea.ccx_binary
    result["ccx_exit_code"] = exit_code
    if exit_code != 0:
        raise RuntimeError(f"ccx exited {exit_code}: {(fea.ccx_stderr or '')[-500:]}")

    t = time.perf_counter()
    fea.load_results()
    timings["load_results"] = round(time.perf_counter() - t, 3)
    res = next(o for o in doc.Analysis.Group if o.isDerivedFrom("Fem::FemResultObject"))
    result["min_dz_mm"] = round(min(v.z for v in res.DisplacementVectors), 4)
    result["max_von_mises_mpa"] = round(max(res.vonMises), 2)
    result["ok"] = True
    return result


def main():
    # femtools.ccxtools finds ccx through the FreeCAD preference, else PATH.
    os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"
    import FreeCAD

    OUT.mkdir(parents=True, exist_ok=True)
    pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Ccx")
    result = {"ok": False, "freecad": ".".join(FreeCAD.Version()[:3]),
              "ccx_binary_preference": pref.GetString("ccxBinaryPath", ""),
              "published_dz_mm": PUBLISHED_DZ_MM, "closed_form_dz_mm": CLOSED_FORM_DZ_MM,
              "cases": []}
    for case, order in (("bundled", None), ("gmsh_1st", "1st"), ("gmsh_2nd", "2nd")):
        try:
            result["cases"].append(solve(case, order))
        except Exception as e:  # errors as values
            result["cases"].append({"case": case, "ok": False, "error": f"{type(e).__name__}: {e}"})

    bundled = result["cases"][0]
    result["ok"] = bool(bundled["ok"]
                        and abs(bundled["min_dz_mm"] - PUBLISHED_DZ_MM) <= TOL_MM
                        and Path(bundled["ccx_binary"]).resolve().is_relative_to(ROOT))
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

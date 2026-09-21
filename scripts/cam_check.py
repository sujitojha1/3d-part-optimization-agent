"""Headless FreeCAD CAM check on one Gate 4 test block (M1.11, D-11).

Builds the block, a CAM Job with Profile, Adaptive and Drilling operations
from the committed ToolBit library, runs Sanity Check, post-processes G-code
with a pinned post processor, replays the toolpaths through PathSimulator and
measures the stock left above the part.

Run with the FEM environment's Python (scripts/fem_env.py finds it), one block per process:
    $FEM_PYTHON scripts/cam_check.py clean|undercut [--resolution MM]

Writes out/gate4/<block>/{result.json,<block>.ngc,sanity.html} and prints the
result as JSON. Exit 0 when every step ran, whatever the residual stock; exit 2
when a step failed, with the error in the result.
"""

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path as FsPath

import FreeCAD
import Part
import Path
import PathSimulator
import numpy as np
from FreeCAD import Vector

import Path.Main.Job as PathJob
import Path.Op.Adaptive as PathAdaptive
import Path.Op.Drilling as PathDrilling
import Path.Op.Profile as PathProfile
import Path.Tool.Controller as PathToolController
from Path.Main.Sanity import Sanity
from Path.Post.Processor import PostProcessorFactory
from Path.Tool.toolbit import ToolBit
from PathScripts import PathUtils

ROOT = FsPath(__file__).resolve().parent.parent
TOOLING = ROOT / "tooling"
OUT = ROOT / "out" / "gate4"

POST_PROCESSOR = "refactored_linuxcnc"  # ships with FreeCAD 1.1.3, pinned by the lock
STOCK_MARGIN = 2.0  # mm around the part in x and y; flush in z
RESIDUAL_TOL = 0.5  # mm of material left above the part in one column


# --- Test blocks -------------------------------------------------------------


def make_block(undercut: bool) -> Part.Shape:
    """60 x 40 x 20 mm block: a filleted pocket, a through hole, optional undercut.

    The pocket's vertical corners have a 4 mm fillet, above the 3 mm radius of
    the 6 mm endmill, so a 3-axis mill can reach every face of the clean block.
    The undercut is a 4 mm slot cut into the +x wall under a 10 mm overhang,
    which no tool coming from +z can reach.
    """
    body = Part.makeBox(60, 40, 20)
    pocket = Part.makeBox(30, 20, 8, Vector(5, 10, 12))
    pocket = pocket.makeFillet(4, [e for e in pocket.Edges if _is_vertical(e)])
    hole = Part.makeCylinder(2.5, 20, Vector(48, 20, 0))
    shape = body.cut(pocket).cut(hole)
    if undercut:
        shape = shape.cut(Part.makeBox(6, 30, 4, Vector(54, 5, 6)))
    return shape.removeSplitter()


def _is_vertical(edge) -> bool:
    a, b = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
    return abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and abs(a.z - b.z) > 1e-6


def face_name(shape, predicate) -> str:
    """Select a face by geometry, never by a stored index (D-04)."""
    matches = [f"Face{i + 1}" for i, f in enumerate(shape.Faces) if predicate(f)]
    if len(matches) != 1:
        raise LookupError(f"expected one face, found {matches}")
    return matches[0]


def is_pocket_floor(f) -> bool:
    return f.Surface.TypeId == "Part::GeomPlane" and abs(f.BoundBox.ZMin - 12) < 1e-6 \
        and abs(f.BoundBox.ZMax - 12) < 1e-6


def is_hole_wall(f) -> bool:
    return f.Surface.TypeId == "Part::GeomCylinder" and abs(f.Surface.Radius - 2.5) < 1e-6


# --- CAM Job -----------------------------------------------------------------


class _HeadlessInput:
    """Stands in for the GUI's tool-controller prompt.

    FreeCAD 1.1.3's PathUtils.findToolController leaves `tc` unbound when a
    Job has several tool controllers and no GUI is up. Each operation's
    ToolController is set explicitly right after Create, so the choice made
    here never sticks.
    """

    @staticmethod
    def selectedToolController():
        return None

    @staticmethod
    def chooseToolController(controllers):
        return controllers[0]


def add_tool_controller(job, bit_file, number, feed, plunge, rpm):
    bit = ToolBit.from_file(TOOLING / "Bit" / bit_file)
    tc = PathToolController.Create(f"TC: {bit.label}", bit.attach_to_doc(doc=job.Document), number)
    tc.HorizFeed = f"{feed} mm/min"
    tc.VertFeed = f"{plunge} mm/min"
    tc.SpindleSpeed = rpm
    job.Proxy.addToolController(tc)
    return tc


def build_job(doc, model):
    PathUtils.UserInput = _HeadlessInput
    job = PathJob.Create("Job", [model], None)
    for ext in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos"):
        setattr(job.Stock, ext, STOCK_MARGIN)
    job.Stock.ExtZneg = 0.0
    job.Stock.ExtZpos = 0.0

    # Job.Create adds a default 5 mm endmill; use the committed library instead.
    for tc in list(job.Tools.Group):
        doc.removeObject(tc.Tool.Name)
        doc.removeObject(tc.Name)
    endmill = add_tool_controller(job, "6mm_Endmill.fctb", 1, feed=600, plunge=200, rpm=8000)
    drill = add_tool_controller(job, "5mm_Drill.fctb", 3, feed=150, plunge=150, rpm=3000)
    base = job.Model.Group[0]

    profile = PathProfile.Create("Profile")
    profile.ToolController = endmill

    adaptive = PathAdaptive.Create("Adaptive")
    adaptive.ToolController = endmill
    adaptive.Base = [(base, [face_name(base.Shape, is_pocket_floor)])]

    drilling = PathDrilling.Create("Drilling")
    drilling.ToolController = drill
    drilling.Base = [(base, [face_name(base.Shape, is_hole_wall)])]
    drilling.ExtraOffset = "Drill Tip"  # clear the tip cone through the bottom face

    doc.recompute()
    for op in job.Operations.Group:
        if not op.Path.Commands:
            raise RuntimeError(f"operation {op.Label} produced no path")
    return job, base


def sanity_check(job, out_dir):
    report = Sanity.CAMSanity(job, output_file=str(out_dir / "sanity.html"))
    squawks = [
        {"type": q["squawkType"], "note": q["Note"]}
        for section in report.data.values()
        if isinstance(section, dict)
        for q in section.get("squawkData", [])
    ]
    # CAUTION and WARNING are missing values in the Job: the check is invalid.
    errors = [q for q in squawks if q["type"] in ("CAUTION", "WARNING")]
    if errors:
        raise RuntimeError(f"sanity check: {errors}")
    return squawks


def post_process(job, out_file):
    job.PostProcessorOutputFile = ""
    post = PostProcessorFactory.get_post_processor(job, POST_PROCESSOR)
    gcode = "".join(g for _, g in post.export())
    if not gcode.strip():
        raise RuntimeError("post processor wrote no G-code")
    out_file.write_text(gcode)
    return len(gcode.splitlines())


# --- Simulation --------------------------------------------------------------


def simulate(job, resolution):
    """Replay each operation's commands on a heightmap stock.

    Follows the legacy CAM simulator (Path/Main/Gui/Simulator.py): arcs are
    split into chords no longer than the resolution, and canned drill cycles
    are expanded into plain moves, because ApplyCommand handles lines only.
    """
    stock = job.Stock.Shape
    sim = PathSimulator.PathSim()
    sim.BeginSimulation(stock, resolution)
    pos = FreeCAD.Placement(Vector(0, 0, stock.BoundBox.ZMax), FreeCAD.Rotation())
    moves = 0
    for op in job.Operations.Group:
        sim.SetToolShape(op.ToolController.Tool.Shape, resolution / 5)
        retract = None
        for cmd in PathUtils.getPathWithPlacement(op).Commands:
            for move in _linear_moves(pos, cmd, resolution, retract):
                pos = sim.ApplyCommand(pos, move)
                moves += 1
            if cmd.Name in ("G81", "G82", "G83", "G73"):
                retract = cmd.r
            elif cmd.Name == "G80":
                retract = None
    top, inner = sim.GetResultMesh()
    return top, inner, moves


def _linear_moves(pos, cmd, resolution, retract):
    name = cmd.Name
    if name in ("G0", "G00", "G1", "G01"):
        yield cmd
    elif name in ("G2", "G02", "G3", "G03"):
        yield from _arc_chords(pos, cmd, resolution)
    elif name in ("G81", "G82", "G83", "G73"):
        p = cmd.Parameters
        x, y, z, r = p.get("X", pos.Base.x), p.get("Y", pos.Base.y), p["Z"], p["R"]
        if retract is None:
            yield Path.Command("G0", {"Z": r})
        yield Path.Command("G0", {"X": x, "Y": y, "Z": r})
        yield Path.Command("G1", {"X": x, "Y": y, "Z": z})
        yield Path.Command("G1", {"X": x, "Y": y, "Z": r})


def _arc_chords(pos, cmd, resolution):
    p = cmd.Parameters
    start = pos.Base
    end = Vector(p.get("X", start.x), p.get("Y", start.y), p.get("Z", start.z))
    cx, cy = start.x + p.get("I", 0.0), start.y + p.get("J", 0.0)
    a0 = math.atan2(start.y - cy, start.x - cx)
    a1 = math.atan2(end.y - cy, end.x - cx)
    sweep = a1 - a0
    if cmd.Name in ("G3", "G03"):
        sweep %= 2 * math.pi
    else:
        sweep = -((-sweep) % (2 * math.pi))
    if abs(sweep) < 1e-9:  # full circle
        sweep = 2 * math.pi if cmd.Name in ("G3", "G03") else -2 * math.pi
    r = math.hypot(start.x - cx, start.y - cy)
    n = max(1, math.ceil(abs(sweep) * r / resolution))
    for i in range(1, n + 1):
        a = a0 + sweep * i / n
        z = start.z + (end.z - start.z) * i / n
        yield Path.Command("G1", {"X": cx + r * math.cos(a), "Y": cy + r * math.sin(a), "Z": z})


# --- Residual stock ----------------------------------------------------------


def column_grid(bbox, resolution):
    nx = int(round(bbox.XLength / resolution))
    ny = int(round(bbox.YLength / resolution))
    # Shift centres off round coordinates so none lands exactly on a mesh edge.
    x = bbox.XMin + (np.arange(nx) + 0.5) * resolution + 1.37e-4
    y = bbox.YMin + (np.arange(ny) + 0.5) * resolution + 1.37e-4
    return x, y


def rasterize(points, triangles, x, y, mode):
    """Per-column value over triangles seen from +z.

    mode "top": highest surface point (the heightmap of the simulated stock).
    mode "material": solid length along the column, as the sum of z over
    up-facing hits minus down-facing hits of a closed, outward mesh.
    """
    grid = np.zeros((len(x), len(y)))
    res = x[1] - x[0]
    x0, y0 = x[0], y[0]
    for tri in triangles:
        a, b, c = points[tri[0]], points[tri[1]], points[tri[2]]
        area2 = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area2) < 1e-12:
            continue  # vertical facet: no column crosses it
        lo = np.minimum(np.minimum(a, b), c)
        hi = np.maximum(np.maximum(a, b), c)
        i0, i1 = max(0, math.ceil((lo[0] - x0) / res)), min(len(x) - 1, math.floor((hi[0] - x0) / res))
        j0, j1 = max(0, math.ceil((lo[1] - y0) / res)), min(len(y) - 1, math.floor((hi[1] - y0) / res))
        if i0 > i1 or j0 > j1:
            continue
        px, py = np.meshgrid(x[i0:i1 + 1], y[j0:j1 + 1], indexing="ij")
        w1 = ((px - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (py - a[1])) / area2
        w2 = ((b[0] - a[0]) * (py - a[1]) - (px - a[0]) * (b[1] - a[1])) / area2
        inside = (w1 >= 0) & (w2 >= 0) & (w1 + w2 <= 1)
        if not inside.any():
            continue
        z = a[2] + w1 * (b[2] - a[2]) + w2 * (c[2] - a[2])
        view = grid[i0:i1 + 1, j0:j1 + 1]
        if mode == "top":
            view[inside] = np.maximum(view[inside], z[inside])
        else:
            view[inside] += np.sign(area2) * z[inside]
    return grid


def residual_stock(part, sim_meshes, stock_bbox, resolution):
    """Material the toolpaths left above the part, column by column.

    A column's residual is the simulated stock height minus the part's solid
    length in that column. It is positive where stock was never cut: left on
    a face the tool missed, or trapped under an overhang no +z tool can reach.
    Cells within one cell of a wall differ only by where the grid falls (the
    simulator's mesh also stops half a cell short of each wall), so a cell
    counts only when it and its four neighbours are all beyond tolerance.
    """
    x, y = column_grid(stock_bbox, resolution)
    pts, tris = part.tessellate(resolution / 10)
    material = rasterize(np.array([tuple(p) for p in pts]), tris, x, y, "material")
    height = np.zeros_like(material)
    for mesh in sim_meshes:
        p = np.array([tuple(v) for v in mesh.Topology[0]])
        height = np.maximum(height, rasterize(p, mesh.Topology[1], x, y, "top"))
    residual = height - material

    left = _interior(residual > RESIDUAL_TOL)
    gouged = _interior(residual < -RESIDUAL_TOL)
    cell = resolution * resolution
    return {
        "residual_volume_mm3": round(float(residual[left].sum() * cell), 1),
        "residual_area_mm2": round(float(left.sum() * cell), 1),
        "max_residual_mm": round(float(residual[left].max()) if left.any() else 0.0, 3),
        # A toolpath that cut into the part, or a simulation that removed too
        # much, shows here. Nonzero makes the check invalid, not a pass.
        "overcut_area_mm2": round(float(gouged.sum() * cell), 1),
        "part_volume_mm3": round(part.Volume, 1),
    }


def _interior(mask):
    """Cells whose four neighbours are also set: drops one-cell wall aliasing."""
    core = mask.copy()
    core[1:, :] &= mask[:-1, :]
    core[:-1, :] &= mask[1:, :]
    core[:, 1:] &= mask[:, :-1]
    core[:, :-1] &= mask[:, 1:]
    return core


# --- Driver ------------------------------------------------------------------


def run(block_name, resolution):
    out_dir = OUT / block_name
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"block": block_name, "resolution_mm": resolution, "residual_tol_mm": RESIDUAL_TOL,
              "post_processor": POST_PROCESSOR, "freecad": ".".join(FreeCAD.Version()[:3]),
              "timings_s": {}, "ok": False}
    timings = result["timings_s"]

    def step(name, fn, *args):
        t = time.perf_counter()
        value = fn(*args)
        timings[name] = round(time.perf_counter() - t, 3)
        return value

    try:
        doc = FreeCAD.newDocument("gate4")
        model = doc.addObject("Part::Feature", "Block")
        model.Shape = make_block(undercut=block_name == "undercut")
        doc.recompute()

        job, base = step("job_and_ops", build_job, doc, model)
        result["operations"] = {op.Label: len(op.Path.Commands) for op in job.Operations.Group}
        result["sanity_notes"] = step("sanity_check", sanity_check, job, out_dir)
        gcode_file = out_dir / f"{block_name}.ngc"
        result["gcode_lines"] = step("post_process", post_process, job, gcode_file)
        result["gcode_file"] = str(gcode_file.relative_to(ROOT))
        top, inner, moves = step("simulate", simulate, job, resolution)
        result["simulated_moves"] = moves
        result.update(step("residual", residual_stock, base.Shape, (top, inner),
                           job.Stock.Shape.BoundBox, resolution))
        if result["overcut_area_mm2"] > 0:
            raise RuntimeError(f"simulated stock cuts into the part: {result['overcut_area_mm2']} mm2")
        result["residual_stock"] = result["residual_area_mm2"] > 0
        result["ok"] = True
    except Exception as e:  # errors as values: the caller reads result.json
        result["error"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()
    result["timings_s"]["total"] = round(sum(timings.values()), 3)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("block", choices=["clean", "undercut"])
    parser.add_argument("--resolution", type=float, default=0.25, help="heightmap cell, mm")
    args = parser.parse_args()
    result = run(args.block, args.resolution)
    print(json.dumps({k: v for k, v in result.items() if k != "traceback"}, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

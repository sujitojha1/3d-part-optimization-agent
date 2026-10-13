# ge_bracket result reader — .frd to mass, stress, displacement and peak region (M3.4)

| | |
| --- | --- |
| Task | M3.4 ([#14](https://github.com/sujitojha1/3d-part-optimization-agent/issues/14)) · [plan](plan.md) M3 step 4 |
| Date | 2026-10-13 |
| Part and load case | The parametric `ge_bracket` under LC1 (`parts/ge_bracket_lc1.json`) |
| Tools | FreeCAD 1.1.3 and its bundled CalculiX **2.22** for the solve, on the Windows machine (D-17 pins 2.23 on the Mac). The reader itself uses numpy only |
| Scripts | `ge_bracket_analysis.run` solves; `ge_bracket_result.read_result` reads. `$FEM_PYTHON scripts/ge_bracket_result.py --check` (about 2 min, two solves) writes `out/ge_bracket_result/result_check.json` |
| Status | **Done.** The reader returns the section-5 `read_result` contract, agrees with M2.5's record on every reported number, and every invalid fixture is `invalid`. The contour image reference is empty until M3.7 |

## 1. The two halves

**`run(params, lc, work)`** in `scripts/ge_bracket_analysis.py` is the body of `run_sim`: the M3.3 assembly, the
D-06 element labels, then `ccx`. It returns a run record (also `run.json`) with `status` `ok` or `unverified`,
and leaves four things in the run directory:

| File | Holds |
| --- | --- |
| `ccx/Mesh.frd` | Nodes, C3D10 elements, displacement and stress |
| `ccx/Mesh.dat` | Each support's reaction total |
| `d06_elsets.inp` | The D-06 label of every element, by element-centroid membership ([M2.4](ge-bracket-labels.md)) |
| `candidate.json` | Parameters, CAD volume and the bolt axes |

**`read_result(run_dir, lc)`** in `scripts/ge_bracket_result.py` reads only those files. It imports no FreeCAD,
mesher or solver, so a stored run can be read again with all three disabled (the route M5.9's offline rescoring
needs). It parses the `.frd` itself and takes 1.1 s on the baseline, against about 13 s for FreeCAD's loader plus
re-labelling in M2.5.

## 2. What it returns

| Field | Definition |
| --- | --- |
| `validity` | `valid` or `invalid`, with the reasons in `problems` |
| `mass_g` | CAD solid volume × the record's density, for the full part. The meshed volume is reported beside it as a check |
| `max_vm` | Largest nodal von Mises outside the 10 mm support zone about each bolt axis, in MPa, with its node, position and region |
| `raw_max_vm` | Largest nodal von Mises anywhere, flagged as the support singularity. Reported, never used |
| `max_disp` | Largest nodal displacement magnitude, in mm |
| `peak_region` | The D-06 label of the largest von Mises outside the 25 mm region-scoring zone. It is what a region claim is scored against, not the stress check (owner, 22 Sep; [exchange record §4](m2-exchange.md)) |
| `max_vm_by_region` | The largest von Mises in each D-06 region |
| `element_counts_by_type`, `nodes` | The sanity check the task names |
| `reactions` | Each support's reaction, the total, and its angle and magnitude error against the load |
| `contour_png` | Empty; M3.7 renders it |

A node takes the label its elements agree on. A node on a boundary between two regions has none, and if `max_vm`
or `peak_region` falls on one the result is `invalid` rather than guessed.

**Invalid, never a pass (REQ-VER-004):** a missing file; an element type other than C3D10; a non-finite field; an
all-zero stress or displacement field; element sets that do not partition the mesh; a support with no reaction
total; reactions more than 0.1° or 0.5 % off the load; a meshed volume more than 1 % off the CAD volume. The 1 %
is a gross-error guard, not OD-C's mass tolerance, which is still open.

## 3. Results (13 Oct, Windows)

| Run | Mass | `max_vm` | `raw_max_vm` | `max_disp` | `peak_region` | Mesh |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline, Ti-6Al-4V | 1,198.77 g | 435.8 MPa in `base_plate` | 618.1 MPa | 0.4515 mm | `arm_root_fillet` | 43,430 C3D10, 72,046 nodes |
| Same geometry, Al 7075-T6 card | 760.39 g | 435.3 MPa | — | 0.7150 mm | `arm_root_fillet` | 43,430 C3D10, 72,046 nodes |

| Check | Result |
| --- | --- |
| Against M2.5's record | The reader was run on M2.5's own stored run (`out/lc1_solve`, 22 Sep), which M2.5 read with FreeCAD's `.frd` loader. Mass, both peaks and their nodes and regions, the five per-region maxima, maximum displacement and its node, the reaction total and the element count are **equal**. The meshed volume agrees to 1.4 × 10⁻⁷: the `.frd` holds coordinates to six significant figures |
| Material-only change | Element and node counts unchanged. Mass follows density exactly. Displacement rises 1.5836× against a modulus ratio of 1.5872; stress moves −0.11 % |
| Invalid fixtures | All-zero field, a NaN, a dropped element set, flipped reactions, no reaction totals and a missing run directory are each `invalid` with a reason |
| Evaluation time | Baseline 59.4 s from parameters to a solved run, of which `ccx` is 38.5 s; reading it back 1.1 s. Provisional: Windows, one run |

## 4. What this does not establish

- **`max_vm` versus the raw peak is still an open acceptance question.** The reader reports both and takes the
  zone peak as `max_vm`, as the LC1 record says. Whether that is what REQ-VER-002 passes on is for M5.1.
- **The second material is a test card, not the library.** Its values are handbook figures typed into the check;
  the cited D-10 library is M4.8.
- **The half-model mass rule is not implemented.** D-23 does not hold, the assembly refuses a half model, and so
  the ×2 in the issue text has nothing to apply to.
- **No timeout.** `ccx` is run to completion; D-13's 180 s per-tool limit is not enforced here.
- **Not run on the D-17 machine**, and the solver here is CalculiX 2.22, not the pinned 2.23.
- **The tolerances are M2.5's and a guard.** OD-C has not declared the numeric tolerances.

# M2 — one part, one load case, walked by hand: what it proved (M2.10)

| | |
| --- | --- |
| Task | M2.10 ([#53](https://github.com/sujitojha1/3d-part-optimization-agent/issues/53)) · [plan](plan.md) |
| Date | 2026-09-22 |
| Milestone | M2 — one part, one load case, walked by hand |
| Status | **M2 is half walked.** Every engineering step is done and recorded; every agent-integration step is not. That split is the finding, section 1 |

M2's purpose is not a number the project reports. It is to force the decisions M1 and M3 would
otherwise make silently, at the point where they are still reversible. This page says which ones
it forced, which it could not, and what changes in `requirements.md` and
`solution-architecture.md` as a result.

## 1. The split, which is the headline

| Done and recorded | Not done |
| --- | --- |
| M2.1 part, M2.2 loads, M2.3 mesh, M2.4 labels, M2.5 solve, M2.6 render, M2.7 exchange (22 Sep, [record](m2-exchange.md)) | **M2.9** the LLM integration spec |

The pipeline half of the hand pass is complete: a parametric part that holds at every parameter
bound, a frozen load record with a hand calculation, a mesh with a measured sizing study, a
region-label route that works after the intended one failed, a solve with parsed results, and
render settings chosen by measurement. **Nothing about the agent has been exercised at all.**

That is why the three architecture questions M2 owns are all still open (section 5), and it is a
more useful statement of M2's state than any per-task percentage: the project has a working
simulation pipeline and no evidence yet that an agent can read its output.

## 2. What the pass proved

- **The part survives its own parameter space.** All 64 corners of the six-parameter space give
  one valid solid, every single-face predicate matches exactly one face, and the 1.27 mm floor
  (D-05) holds. [Record](ge-bracket-part.md).
- **The solve runs end to end and the part passes.** 445.8 MPa against a 602.1 MPa allowable is
  **1.35×** on LC1, with the raw 630.6 MPa peak reported and flagged as the fixed-bolt-hole
  singularity rather than dropped. [Record](ge-bracket-lc1-solve.md).
- **A contour can distinguish the regions that matter**, once the legend is chosen against
  measurement instead of intuition. [Record](ge-bracket-contour.md).

## 3. What broke

- **The D-06 label chain does not reach the CalculiX deck.** FreeCAD 1.1.3 hard-codes
  `group_param = False` in `femsolver/calculix/write_mesh.py`, so 501 named sets in the group
  deck become 0 in the ccxtools deck. M2.4's element-centroid fallback replaces it and is a
  disjoint, exhaustive partition — but the labels now originate at a fallback, not at the
  designed route. Re-checked against the Windows FreeCAD in M2.6 and still `False`.
  [Record](ge-bracket-labels.md).
- **The hand calculation disagrees with the FE by 2.56×** on governing von Mises — 174 against
  445.8 MPa. Bolt reaction *signs* all agree; magnitudes do not. This is unresolved, and it is
  the single largest open technical question M2 leaves behind.
- **The 60 s cut trigger fired.** 92.13 s to mesh and solve at D-24's MeshRegion 1.5.
- **The obvious legend is unreadable.** Locking the colour bar to the allowable — the only
  scheme whose colour means something physical on its own — renders the part as one navy mass.
- **`pin_bore` is not converged**, climbing 189.9 → 277.4 MPa across the mesh sweep and still
  rising at the accepted size.
- **The pipeline could not start off the D-17 machine.** Three scripts hard-coded the
  `vendor/fem-env` macOS prefix; the environment is now resolved through `scripts/fem_env.py`.

## 4. The frozen records and the measured timings

The part ([ge-bracket-part.md](ge-bracket-part.md)) and the LC1 load record
([ge-bracket-lc1.md](ge-bracket-lc1.md)) are frozen and unchanged by this milestone. The
measured numbers, all from the full model at D-24 MeshRegion 1.5 (the size M2 ran at; see section 5
for the 2.0 re-run that is now the record):

| | |
| --- | --- |
| Full-part mass | 1,198.77 g |
| Governing von Mises, outside the support zone | 445.8 MPa → **1.35×** |
| Raw peak (flagged singularity) | 630.6 MPa |
| Max displacement | 0.4516 mm |
| Mesh + solve | **92.13 s** (12.02 Gmsh + 80.11 ccx) |
| CAD → parsed result | **111.23 s** |

**Every timing is provisional.** All of it was measured on Windows-AMD64 with FreeCAD 1.1.3,
Gmsh 4.15.0 and ccx 2.22, not the D-17 `vendor/fem-env` environment (Gmsh 4.15.2, ccx 2.23).
Gmsh runs 3.1× slower here. The stresses, mass and labels are not platform-sensitive in any way
these runs can detect; the wall times are, and the cut-trigger decision rests on them.

## 5. The decision delta

### D-13, the budget — first measurement, and it is tight

D-13 allows 8 evaluations or 20 minutes. The simulation half of one evaluation is **111.23 s**,
so 8 evaluations are **14.8 min of the 20**, leaving 5.2 min for the D-11 CAM jobs that M3.8 has
not timed yet. At MeshRegion 2.0, now applied, the same 8 evaluations are **8.9 min**. D-13's own wording
applies the levers in order once a nominal solve passes 60 s: D-23 half model, then D-24 minimum
size. The first lever is unavailable (below), so the second is the one on the table.

### D-23, the half model — confirmed closed

Unavailable, and correctly so: the measured bolt pattern is asymmetric about the clevis
midplane. No change; recorded because D-13 names it as the first lever and it can now be struck
off definitively rather than reconsidered each time the clock is tight.

### D-24, the mesh sizing — applied at 2.0

| MeshRegion | Mesh + solve | Governing peak | Arm-root fillet | Pin bore | Max disp |
| --- | --- | --- | --- | --- | --- |
| **1.5** (current) | 92.13 s | 445.8 MPa | 261.5 | 277.4 | 0.4516 |
| **2.0** (proposed) | **48.63 s** | 435.8 MPa | 259.3 | 232.6 | 0.4515 |

2.0 clears the 60 s trigger and moves the governing peak 2.2 % at the same location in the same
region. **Applied by the owner on 22 Sep** (`SIZES` in `scripts/ge_bracket_mesh.py`). The
canonical `out/lc1_solve` record was re-run at 2.0: 72,046 nodes, mesh + solve **47.06 s**
(7.58 Gmsh + 39.48 ccx), CAD → result **66.45 s**, so 8 evaluations are **8.9 min**. Governing
peak 435.8 MPa → **1.38×**, raw (flagged) peak 618.1 MPa, max displacement 0.4515 mm, mass
unchanged. The M2.6 contour study re-run on it leaves the proposed freeze standing: the worst
ΔE for `turbo`, 800 × 600, allowable/2 is 9.1 at `iso` (was 9.6), `front` and `arm_root`
unchanged, and the ranking of legend schemes is the same. Do not go past 2.0: `pin_bore`
under-reads by 23 % at 3.0, and while it does not govern under LC1, any load case that makes the
bore govern re-opens the mesh study.

**The `L_bracket` fallback should not be taken.** The trigger fired on a setting with a measured,
answer-preserving alternative, not on the part.

### The pin-load model — closed by M2.2, exercised by M2.5

Rigid pin, four fixed bolt holes. Unchanged, and now run end to end.

### `REQ-OPT-001`, the render settings — accepted

`requirements.md` section 8 makes the ordering normative: the camera set, image size, colormap
and legend scheme are fixed in M2 *by eye*, before any renderer is written. M2.6 proposed, and
the owner accepted on 22 Sep,
`turbo`, 800 × 600, a linear legend locked at 0 → allowable/2, three cameras (`iso`, `front`,
`arm_root`), parallel projection. Two findings ride with it: a log legend scores best on
separation and misreads the part, and the frozen bar **saturates on 22 % of SimJEB 148's surface**
under its vertical case — so the transferable thing is the anchoring rule, not the MPa constant.
[Record](ge-bracket-contour.md).

### Architecture questions 1, 2 and 6 — all still open

`solution-architecture.md` section 9 assigns these to M2, "by experiment and measurement, not by
argument". None can be answered yet:

| # | Question | Assigned to | State |
| --- | --- | --- | --- |
| 1 | Numbers before or after the picture? | M2.7 (M2.8 merged into it) | **Answered 22 Sep** — the numbers moved 0 of 18 claims, but in a second turn the model attaches the governing number to its own claimed region (5 of 9). Two turns kept, and prose never locates a number ([record](m2-exchange.md) §3) |
| 2 | Does the proposal step live in a planner node or a capability? | M2.9 | **Open** — to be decided against a real transcript |
| 6 | Does the agent get code-editing capability at all? | M2.9 | **Open** |

Question 1 is the one section 9 calls the most consequential: if the model anchors on `max_vm`
before reading the contour, the contour becomes decorative and the project's central claim is
hollow while every metric still looks fine. **M2 has produced the contour it needs and has not
run the experiment.**

### Part brief §7 — what M2 settled of it

[Part brief section 7](ge-jet-engine-bracket.md) lists the challenge's clashes with fixed
decisions. M2 closes four of them in practice:

- **D-04 free-form STEP** — resolved as the brief suggests: a parametric rebuild, not an edit of
  the challenge STEP.
- **D-08 four load cases** — option (a) taken: LC1 vertical only, one task per case. LC1 governs
  318 of 381 SimJEB designs.
- **SF and displacement limit** — the project's choice of SF 1.5 on 903 MPa, allowable 602.1 MPa,
  is now exercised and is what the 1.35× is measured against.
- **Geometry source** — SimJEB interface coordinates, licensed data fetched and never committed.

Unchanged and still owner-facing: the **D-11 `metal_am` profile** (min-wall only for now) and the
**D-09 yield override** for the material-led variant.

## 6. What M2 hands to M3

1. ~~**Run M2.7.**~~ Done 22 Sep ([record](m2-exchange.md)): closed-set label and complete D-07 in 36 of 36
   calls. The model's region (`arm_root_fillet`) and the stress check's (`base_plate`, a converged
   peak 17.7 mm from a fixed bolt axis) disagreed. Settled the same day: region claims are scored
   outside a 25 mm zone, and the stress check keeps 10 mm (§4). Region hit is now 12 of 12.
2. ~~**Answer D-24's 1.5 → 2.0.**~~ Done 22 Sep: 2.0 applied, leaving about 11 of D-13's 20 min for the CAM jobs.
3. **Re-measure the timings under D-17**, then re-read the cut trigger against them.
4. **Resolve the 2.56× hand-versus-FE disagreement**, or record why it is accepted.
5. ~~**Accept or amend M2.6's render freeze.**~~ Accepted as proposed on 22 Sep.

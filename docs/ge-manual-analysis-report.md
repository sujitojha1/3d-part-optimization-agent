# GE manual analysis report — 5 materials × 4 load cases on L1 (M2A.6)

> **21 Sep status:** This document contains historical Iteration1 study evidence. Current scripts select `GE_Challenge_Bracket`; current mesh quality is rejected (gamma minimum 0.014993 < 0.05), and replacement acceptance is open in #66/#60. See [the current audit](progress-review-2026-09-21.md) for geometry hashes, progress and remaining checks. Do not treat the older geometry/face IDs/numeric results below as verification of the replacement.
> The linked CSV already contains the current 2052.2 g Ti baseline; the 1256.9 g narrative below is the earlier study and has not yet been regenerated for the replacement.

| | |
| --- | --- |
| Task | M2A.6 ([#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19 |
| Geometry | `data/ge_manual/Iteration1_partitioned.FCStd`, SHA-256 `b025011c…790af6` ([M2A.1](ge-manual-geometry.md), with the [M2A.4](ge-manual-boundary-conditions.md) partition) |
| Mesh | **L1**: 155,203 nodes and 90,353 C3D10 elements, connectivity SHA-256 `342e0de4…280b83` ([M2A.2](ge-manual-mesh.md)) |
| Setup | Supports and rigid pin from [M2A.4](ge-manual-boundary-conditions.md); LC1–LC4 from [M2A.5](ge-manual-load-cases.md); cards from [M2A.3](ge-manual-materials.md) |
| Tools | FreeCAD 1.1.3 FEM (CalculiX solver object) writes each deck; CalculiX 2.23 (SPOOLES) solves it |
| Script | `vendor/fem-env/bin/python scripts/ge_manual_matrix.py` (about 20 min). `--report-only` rebuilds the tables and maps from the saved results |
| Data | [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) (20 rows); `out/ge_manual_matrix/matrix.json`; maps in `out/ge_manual_matrix/maps/` |
| Status | **20 of 20 runs solved and valid.** Every support force and moment balance is within 0.02 N and 1.7 N·mm. **Open quality issue: no mesh-convergence evidence** (L1 only; section 7). The stress results are screening values, not verified peaks |

## Summary

- **Ti-6Al-4V, the challenge baseline:** passes the project screen in every case.
  - Outside the exclusion zones, the peak von Mises stress is **427 MPa (LC1)**, a safety factor of 2.11 on GE's
    903.2 MPa yield.
  - The maximum displacement is **0.414 mm (LC1)**.
  - The mass is **1,256.9 g**.
- **The governing case is LC1 (vertical) for every material,** for both stress and displacement.
- **The stress field barely depends on the material.** The supports are fixed displacements, so the stress
  depends only on Poisson's ratio. Peaks outside the exclusions vary by 1.6 % across the five cards. Displacement
  scales with 1/E.
- **Two alternatives fail the stress screen:**
  - **Al 7075-T651** exceeds yield in LC1 (428.5 MPa against 421.3 MPa), and its LC3 safety factor is 1.03.
  - **Al 6061-T651** exceeds yield in LC1 and LC3, and its LC2 safety factor is 1.12.
  - A yield exceedance in a linear-elastic solve is a **failed screening result**, not a prediction of plastic
    collapse.
- **Both aluminium alloys also fail the project displacement limit,** 1.1 × Ti, at 1.58–1.65 × Ti.
- **17-4PH H1025 and AISI 4140 Q&T pass both screens,** with minimum safety factors of 2.30 and 1.59, but weigh
  2,214.8 g, 1.76 × Ti.
- **The alternatives are project comparisons, not challenge-compliant designs:** GE fixes Ti-6Al-4V.
  - Ti uses GE's 903.2 MPa yield; the others use specification minimums ([M2A.3 §1](ge-manual-materials.md)).
- **Raw peaks exceed yield in almost every run.** They sit at idealised support and pin boundaries, where the
  stress is singular: up to 1,818 MPa at a fixed-patch edge. They are reported but not used for screening
  (section 5).

## 1. How each run was made

Each of the 20 runs is its own FreeCAD document, built from a fresh copy of the L1 mesh document:

- the CalculiX solver;
- one material card on the whole solid;
- `Fixed_B1`–`B4` on the nut-contact patches;
- the rigid body `Pin` on both lug bores, carrying that case's force or moment at the pin reference point
  (−20.974, −74.760, 44.725).

This is the M2A.5 setup, with the material varied. Each deck is re-checked before solving: supports and pin node
sets, no extra restraints, the `*CLOAD` cards, and the `*ELASTIC` line against the card.

**One deck edit.** FreeCAD writes `*NODE FILE` with `U` only. The deck is changed to `U, RF`, so the `.frd` holds
nodal reactions and the moment balance can be checked. By hand: open the `.inp` written by the solver task panel,
change that line, then run `ccx -i <job>`. Nothing else in the deck changes.

**Stress extraction.** This is ccx's default nodal stress: it is extrapolated from the integration points, then
averaged over the elements that share each node. Von Mises is computed from that averaged tensor, and every map
and table uses it. Displacement is the magnitude of the nodal translation. The rigid body's two extra nodes are
not part of the mesh and are left out.

**Mass** is the B-rep volume, 283,729.678 mm³, times the card density, the same as M2A.3. It is identical across
LC1–LC4 for each material by construction.

## 2. Acceptance criteria

| Item | Definition | Origin |
| --- | --- | --- |
| Valid run | ccx exits 0 with no `*ERROR`; `DISP`, `STRESS` and `FORC` cover every node; all deck checks pass; balance within tolerance | This task |
| Balance | Reaction force and moment summed over the four fixed patches, taken **about the pin reference point**, plus the applied load. Each residual must be ≤ 0.5 % of the applied load. For scale, a force converts to a moment with L = 100 mm, about the bolt-to-pin distance | [Mesh record §6](ge-manual-mesh.md) (0.5 %) |
| Stress screen | Peak von Mises **outside the exclusion zones** against yield, with a safety factor of 1.5 | [M2A.3 §5](ge-manual-materials.md): the SF is a project choice; GE prescribes none |
| Displacement screen | Maximum displacement ≤ 1.1 × the Ti value for the same case | [M2A.3 §5](ge-manual-materials.md), project choice |

**Exclusion zones.** Raw peaks are always reported. The stress screen uses the peak outside two zones:

- **Bolt zone:** plan distance from a bolt axis < **10 mm**, full height. It covers the fixed-patch edge at
  Ø 14.173 and the hole. The same radius was used for M2's LC1.
- **Pin zone:** within **3 mm of the lug bore and chamfer faces**, Face35–46, the M2A.2 `pin_bore` mesh region.
  This is where the rigid pin meets the part.

  **This definition was amended after the first results.** The first definition was an axial slab: 11.1125 ≤
  |axial| ≤ 17.4625 mm from the pin reference point, radius < 12.557 mm. It missed two things:
  - Nodes on the lug faces: the fitted pin axis leaves them ±0.015 mm outside the slab.
  - The chamfer cones on the outer ends of the bores.

  As a result, LC2's and LC4's first "outside" peaks sat on a bore edge (Face46 and its chamfer Face42) in every
  material. That is the rigid-bore artefact the zone was meant to cover, so the definition was corrected. LC1
  and LC3 are unchanged; LC2 and LC4 change as follows:

  | Case | First definition, Ti (MPa) | Corrected, Ti (MPa) | Corrected peak location |
  | --- | --- | --- | --- |
  | LC2 | 224.8, bore edge of the −y lug | **214.8** | Recess fillet (toroid Face29) round B1's boss, 10.3 mm from its axis |
  | LC4 | 392.9, bore/chamfer edge of the −y lug | **154.6** | R 3.175 arm-root fillet (Face96/97) of the +y lug, 4.4 mm from the pin faces |

  The other materials change in the same way. Each LC2 and LC4 run keeps its first value in its `result.json`,
  as `stress_first_definition`. The correction doesn't change any material's overall verdict. It does change two
  runs: under the first definition, Al 7075 LC4 and Al 6061 LC4 had safety factors below 1.5 (1.07 and 0.61).

## 3. Results, all 20 runs

**Safety factor** = yield ÷ peak von Mises.
- **SF raw** uses the raw maximum, which is usually at a singularity.
- **SF outside** uses the maximum outside the exclusion zones.
- Entries in bold fail the screen.

| Material | LC | Status | Wall (s) | Raw max vM (MPa), zone | vM outside exclusions (MPa) | Yield (MPa) | SF raw / outside | Max disp (mm) | ÷ Ti | Residual F (N) / M (N·mm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (baseline) | LC1 | valid | 50.9 | 1,717.2 (bolt) | 427.2 | 903.2 | 0.53 / 2.11 | 0.4142 | 1.000 | 0.011 / 0.7 |
| **Ti-6Al-4V** (baseline) | LC2 | valid | 51.3 | 995.2 (bolt) | 214.8 | 903.2 | 0.91 / 4.21 | 0.2094 | 1.000 | 0.004 / 0.2 |
| **Ti-6Al-4V** (baseline) | LC3 | valid | 51.2 | 946.7 (bolt) | 407.2 | 903.2 | 0.95 / 2.22 | 0.2742 | 1.000 | 0.004 / 0.2 |
| **Ti-6Al-4V** (baseline) | LC4 | valid | 51.2 | 392.9 (pin) | 154.6 | 903.2 | 2.30 / 5.84 | 0.0531 | 1.000 | 0.001 / 0.0 |
| Al 7075-T651 | LC1 | valid | 50.4 | 1,735.2 (bolt) | 428.5 | 421.3 | 0.24 / **0.98 (> yield)** | 0.6563 | **1.585** | 0.018 / 0.4 |
| Al 7075-T651 | LC2 | valid | 51.2 | 1,003.0 (bolt) | 214.9 | 421.3 | 0.42 / 1.96 | 0.3312 | **1.582** | 0.003 / 0.2 |
| Al 7075-T651 | LC3 | valid | 50.5 | 954.0 (bolt) | 408.8 | 421.3 | 0.44 / **1.03 (< 1.5)** | 0.4348 | **1.586** | 0.006 / 0.3 |
| Al 7075-T651 | LC4 | valid | 49.7 | 394.0 (pin) | 155.8 | 421.3 | 1.07 / 2.70 | 0.0841 | **1.584** | 0.000 / 0.1 |
| Al 6061-T651 | LC1 | valid | 50.3 | 1,735.2 (bolt) | 428.5 | 241.3 | 0.14 / **0.56 (> yield)** | 0.6826 | **1.648** | 0.018 / 0.4 |
| Al 6061-T651 | LC2 | valid | 50.5 | 1,003.0 (bolt) | 214.9 | 241.3 | 0.24 / **1.12 (< 1.5)** | 0.3444 | **1.645** | 0.003 / 0.2 |
| Al 6061-T651 | LC3 | valid | 50.3 | 954.0 (bolt) | 408.8 | 241.3 | 0.25 / **0.59 (> yield)** | 0.4522 | **1.649** | 0.006 / 0.3 |
| Al 6061-T651 | LC4 | valid | 50.6 | 394.0 (pin) | 155.8 | 241.3 | 0.61 / 1.55 | 0.0874 | **1.646** | 0.000 / 0.1 |
| 17-4PH H1025 | LC1 | valid | 50.7 | 1,817.5 (bolt) | 434.1 | 999.7 | 0.55 / 2.30 | 0.2332 | 0.563 | 0.014 / 1.7 |
| 17-4PH H1025 | LC2 | valid | 50.2 | 1,038.9 (bolt) | 216.6 | 999.7 | 0.96 / 4.62 | 0.1166 | 0.557 | 0.004 / 0.5 |
| 17-4PH H1025 | LC3 | valid | 50.2 | 987.1 (bolt) | 415.6 | 999.7 | 1.01 / 2.40 | 0.1549 | 0.565 | 0.005 / 0.3 |
| 17-4PH H1025 | LC4 | valid | 50.5 | 398.9 (pin) | 161.5 | 999.7 | 2.51 / 6.19 | 0.0298 | 0.561 | 0.000 / 0.1 |
| AISI 4140 Q&T | LC1 | valid | 50.3 | 1,792.7 (bolt) | 432.4 | 689.5 | 0.39 / 1.59 | 0.2339 | 0.565 | 0.019 / 0.6 |
| AISI 4140 Q&T | LC2 | valid | 50.1 | 1,028.0 (bolt) | 216.0 | 689.5 | 0.67 / 3.19 | 0.1173 | 0.560 | 0.006 / 0.3 |
| AISI 4140 Q&T | LC3 | valid | 50.2 | 977.2 (bolt) | 413.6 | 689.5 | 0.71 / 1.67 | 0.1553 | 0.566 | 0.008 / 0.5 |
| AISI 4140 Q&T | LC4 | valid | 50.1 | 397.4 (pin) | 159.7 | 689.5 | 1.74 / 4.32 | 0.0299 | 0.563 | 0.000 / 0.0 |

- **Balance.** The largest residuals are 0.019 N and 1.7 N·mm. Relative to the applied load that is 0.0001 %,
  far inside the 0.5 % tolerance.
- **Solver messages.** ccx logged no warnings and no errors in any run.
- **Timing.** Every solve took 49.7–51.3 s.
- **Files per run.** The CSV links each row's deck, `.frd` and map. Each run's folder also holds the FreeCAD
  document, the ccx log and the `.dat`.

## 4. Governing cases and screening, per material

| Material | Mass (g) | Governing stress case | vM outside exclusions (MPa) | Min SF outside | Meets SF 1.5 (all LCs) | Yield exceeded outside exclusions | Governing displacement case | Max disp (mm) | Within 1.1 × Ti (all LCs) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (baseline) | 1,256.9 | LC1 | 427.2 | 2.11 | yes | none | LC1 | 0.4142 | yes (reference) |
| Al 7075-T651 | 797.3 | LC1 | 428.5 | 0.98 | **no** | LC1 | LC1 | 0.6563 | **no** |
| Al 6061-T651 | 766.1 | LC1 | 428.5 | 0.56 | **no** | LC1, LC3 | LC1 | 0.6826 | **no** |
| 17-4PH H1025 | 2,214.8 | LC1 | 434.1 | 2.30 | yes | none | LC1 | 0.2332 | yes |
| AISI 4140 Q&T | 2,214.8 | LC1 | 432.4 | 1.59 | yes | none | LC1 | 0.2339 | yes |

**Al 7075's LC1 failure is marginal.** 428.5 MPa is 1.7 % above its 421.3 MPa specification minimum. It sits at a
fillet whose peak has not been checked for mesh convergence (section 7), so it could move either way with a finer
mesh. Its LC3 safety factor, 1.03, fails the project's 1.5 regardless.

## 5. Where the peaks are

Deck-frame coordinates in mm. The locations are the same for every material.

| Case | Raw maximum | Maximum outside exclusions | Maximum displacement |
| --- | --- | --- | --- |
| LC1 | B3 fixed-patch edge (Face16/Face15 boundary at Ø 14.173), (−6.11, −144.51, 7.85) | R 3.175 arm-root fillet (Face48) outside the −y lug, 21 mm below the pin axis, (−25.90, −94.33, 23.20) | −x tip of the +y lug, (−38.71, −59.19, 49.00) |
| LC2 | B2 seat next to the fixed-patch edge (r 7.3 mm against the edge's 7.09 mm), (−4.65, −5.69, 7.85) | Recess fillet round B1's boss (Face29), (53.73, −8.68, 9.40). **This is 0.3 mm outside the bolt zone, so it is still close to the support** | Top of the −y lug, (−29.88, −91.14, 59.82) |
| LC3 | B3 fixed-patch edge, (−6.11, −144.51, 7.85) | Same fillet as LC1, (−26.47, −94.62, 22.73) | **Bottom edge of the unsupported −x side wall** under the lugs, (−23.35, −75.58, 1.24) |
| LC4 | Bore/chamfer edge of the −y lug (pin zone), (−14.85, −92.05, 36.98) | R 3.175 arm-root fillet (Face96/97) of the +y lug, (−15.42, −56.49, 31.46) | −x tip of the −y lug, (−37.61, −92.80, 45.02) |

- **Raw peaks are support artefacts.** Each sits exactly at an idealised boundary: the fixed-patch edge
  (LC1–LC3; LC2's is one node off it) or the rigid bore (LC4), which are the risks listed in [M2A.4 §6](ge-manual-boundary-conditions.md).
  Peaks like these keep growing as the mesh is refined and are **not** used for screening. They still exceed the Ti yield in LC1–LC3,
  as they do for every material.
- **LC3's maximum displacement is on the base's −x side wall,** at its bottom edge. The base bottom isn't
  supported in this model: there is no contact with the mating surface ([M2A.4 §6](ge-manual-boundary-conditions.md)).
  With that contact, this wall would be held.

## 6. Maps

`out/ge_manual_matrix/maps/<card>_<LC>.png`: one image per run, 20 in all. Each is a 2 × 2 grid:

- **Top row:** von Mises on the undeformed part.
- **Bottom row:** displacement magnitude on the deformed part.
- **Cameras:** the left column is the fixed isometric camera (+x, +y, +z); the right column is the fixed lug-side
  camera (−x, −y, +z). Both use the same parallel scale in every image.
- **Legend ranges are common across the five materials for each load case:**

  | Case | Stress range (MPa) | Displacement range (mm) | Deformation scale |
  | --- | --- | --- | --- |
  | LC1 | 0–434.1 | 0–0.6826 | × 11.7 |
  | LC2 | 0–216.6 | 0–0.3444 | × 23.2 |
  | LC3 | 0–415.6 | 0–0.4522 | × 17.7 |
  | LC4 | 0–161.5 | 0–0.0874 | × 91.5 |

  The stress top is the largest peak outside the exclusions among the five materials; anything above it is
  **magenta**, which in practice means only the excluded zones. The displacement top is the largest maximum
  among the five materials.
- **Markers:** a red sphere marks the raw peak and a black sphere the peak outside the exclusions.
- **Labels:** each image states the units, the view, the deformation scale and the range.

The maps are gitignored with the rest of `out/`. `--report-only` rebuilds them in about 15 s.

## 7. Open quality issues

1. **No mesh-convergence evidence.** The workflow expects convergence checks before this matrix. Only L1 is
   used: L2 ran out of memory with this SPOOLES-only CalculiX, and L2 and L3 were dropped
   ([mesh record §6](ge-manual-mesh.md)).
   - **Displacements and reactions** are probably close; displacement converges quickly.
   - **The screening stresses are at R 3.175 fillets meshed at about 2 mm,** so they may be under-resolved and
     probably low.
   - **The M2A matrix is complete but not fully verified.** The Al 7075 LC1 verdict and the 4140 LC1 margin
     (SF 1.59) are the results most sensitive to this.
2. **Idealised supports.** The nut patches carry uplift, the base bottom has no contact and there is no bolt
   preload ([M2A.4 §6](ge-manual-boundary-conditions.md)). This affects the stresses near the seats and LC3's
   side-wall displacement.
3. **The rigid pin with no contact** overstates bore stiffness and spreads bearing load all round the bore.
4. **The pin exclusion zone was amended after seeing results** (section 2). The first values are kept.
5. **The GUI has not been walked through once.** The runs come from the script; M2A.3–M2A.5 each still need one
   manual pass as well.

## 8. Status against the M2A.6 checklist

| Requirement | Status |
| --- | --- |
| 20 analyses in FreeCAD FEM/CalculiX; documents, decks, logs and results retained | Done: `data/ge_manual/matrix/L1/<card>/<LC>/` (gitignored, about 1.8 GB) |
| Per run: status and warnings, time, mesh ID, material, mass, max von Mises and location, max displacement and location | Done (sections 3 and 5, CSV) |
| Support forces **and moments** against the applied load about a common origin, with tolerances | Done. Origin: the pin reference point; tolerance 0.5 %; every run passes (section 3) |
| No failed solve reported as a pass | No run failed. The script marks any failure as INVALID, with the reason and no metrics |
| Stress and displacement maps for every pair; units, view, deformation scale, consistent extraction; fixed cameras; common ranges | Done (sections 1 and 6) |
| Raw maxima alongside stress excluding a defined singularity zone; exclusion and convergence evidence visible | Done for raw values and exclusions (sections 2 and 5). **Convergence evidence is missing** (section 7) |
| Report and a 20-row CSV | This page and [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) |
| Mass repeated and identical across LC1–LC4 | Done |
| Governing case per material; Ti labelled as the baseline; no alternative called challenge-compliant; yield exceedance labelled as failed screening | Done (summary, section 4) |

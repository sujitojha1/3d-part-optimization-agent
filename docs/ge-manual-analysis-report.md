# GE manual analysis report — 5 materials × 4 load cases on L1 (M2A.6)

> **23 Sep:** regenerated for the current part, `GE_Challenge_Bracket`, from `out/ge_manual_matrix/matrix.json`
> and the CSV beside it. The Iteration1 study this page used to describe (Ti 1,256.9 g) is in git history only.
> **Solver-valid is not engineering-verified:** the L1 mesh is not yet accepted
> ([#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60): one element fails the gamma threshold),
> there is no convergence evidence, and the LC1/LC2 screening peaks sit 0.34 mm outside the bolt exclusion (section 5).

| | |
| --- | --- |
| Task | M2A.6 ([#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19; regenerated 2026-09-23 |
| Geometry | `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`, SHA-256 `10e5c43fa30958f088b04507b95d658e9d3049588b91fd71fead68ae4de3b758` (the [M2A.4](ge-manual-boundary-conditions.md) partition) |
| Mesh | **L1**: 93,659 nodes and 57,835 C3D10 elements, connectivity SHA-256 `5e6a3c41…ee71cf6` ([M2A.2](ge-manual-mesh.md)). **Not accepted**: gamma min 0.0150 < 0.05 on one element at the bottom edge of hole B2 |
| Setup | Supports and rigid pin from [M2A.4](ge-manual-boundary-conditions.md); LC1–LC4 from [M2A.5](ge-manual-load-cases.md); cards from [M2A.3](ge-manual-materials.md) |
| Tools | FreeCAD 1.1.3 FEM (CalculiX solver object) writes each deck; CalculiX 2.23 (SPOOLES) solves it |
| Script | `$FEM_PYTHON scripts/ge_manual_matrix.py` (about 15 min). `--report-only` rebuilds the CSV, `matrix.json` and maps from the saved results |
| Data | [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) (20 rows); `out/ge_manual_matrix/matrix.json`; maps in `out/ge_manual_matrix/maps/` |
| Status | **20 of 20 runs solved and valid.** Every support force and moment balance is within 0.009 N and 1.2 N·mm. **Not verified:** mesh not accepted, no convergence evidence, and the LC1/LC2 screen hinges on the exclusion radius (section 7). The stress results are screening values, not verified peaks |

## Summary

- **Ti-6Al-4V, the challenge baseline:** passes the project screen in every case.
  - Outside the exclusion zones, the peak von Mises stress is **336.5 MPa (LC1)**, a safety factor of 2.68 on GE's
    903.2 MPa yield.
  - The maximum displacement is **0.2278 mm (LC1)**.
  - The mass is **2,052.2 g**.
- **The governing case is LC1 (vertical) for every material,** for both stress and displacement.
- **The stress field barely depends on the material.** The supports are fixed displacements, so the stress
  depends only on Poisson's ratio. Peaks outside the exclusions vary by 0.7 % across the five cards. Displacement
  scales with 1/E.
- **Two alternatives fail the stress screen at the 10 mm exclusion:**
  - **Al 7075-T651:** LC1 safety factor 1.25 (336.7 MPa against 421.3 MPa), below the project's 1.5. Yield is not
    exceeded. **This verdict flips at a 10.5 mm exclusion** (SF 1.73): see section 5.
  - **Al 6061-T651** exceeds yield in LC1 (SF 0.72), and its LC2 and LC3 safety factors are 1.15 and 1.11. It still
    exceeds yield in LC1 at 10.5 mm (243.4 against 241.3 MPa).
  - A yield exceedance in a linear-elastic solve is a **failed screening result**, not a prediction of plastic
    collapse.
- **Both aluminium alloys also fail the project displacement limit,** 1.1 × Ti, at 1.58–1.65 × Ti.
- **17-4PH H1025 and AISI 4140 Q&T pass both screens,** with minimum safety factors of 2.95 and 2.04, but weigh
  3,616.2 g, 1.76 × Ti.
- **The alternatives are project comparisons, not challenge-compliant designs:** GE fixes Ti-6Al-4V.
  - Ti uses GE's 903.2 MPa yield; the others use specification minimums ([M2A.3 §1](ge-manual-materials.md)).
- **Raw peaks exceed yield in almost every run.** They sit at idealised support and pin boundaries, where the
  stress is singular: up to 1,633 MPa at a fixed-patch edge. They are reported but not used for screening
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

**Mass** is the B-rep volume, 463,257.576 mm³, times the card density, the same as M2A.3. It is identical across
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
- **Pin zone:** within **3 mm of the lug bore and chamfer faces**, Face38–43 on the current part, the M2A.2 `pin_bore` mesh region.
  This is where the rigid pin meets the part.

  **This definition was amended after the first results.** The first definition was an axial slab: 11.1125 ≤
  |axial| ≤ 17.4625 mm from the pin reference point, radius < 12.557 mm. It missed two things:
  - Nodes on the lug faces: the fitted pin axis leaves them ±0.015 mm outside the slab.
  - The chamfer cones on the outer ends of the bores.

  On Iteration1 this put LC2's and LC4's first "outside" peaks on a bore edge in every material, so the
  definition was corrected before the current part was run. The current part was run with the corrected zone
  only; the Iteration1 before/after values are in git history.

## 3. Results, all 20 runs

**Safety factor** = yield ÷ peak von Mises.
- **SF raw** uses the raw maximum, which is usually at a singularity.
- **SF outside** uses the maximum outside the exclusion zones.
- Entries in bold fail the screen.

| Material | LC | Status | Wall (s) | Raw max vM (MPa), zone | vM outside exclusions (MPa) | Yield (MPa) | SF raw / outside | Max disp (mm) | ÷ Ti | Residual F (N) / M (N·mm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (baseline) | LC1 | valid | 40.4 | 1,521.8 (bolt) | 336.5 | 903.2 | 0.59 / 2.68 | 0.2278 | 1.000 | 0.004 / 1.2 |
| **Ti-6Al-4V** (baseline) | LC2 | valid | 41.1 | 1,030.9 (bolt) | 209.8 | 903.2 | 0.88 / 4.30 | 0.1731 | 1.000 | 0.004 / 0.4 |
| **Ti-6Al-4V** (baseline) | LC3 | valid | 40.4 | 922.4 (bolt) | 217.6 | 903.2 | 0.98 / 4.15 | 0.0918 | 1.000 | 0.005 / 0.5 |
| **Ti-6Al-4V** (baseline) | LC4 | valid | 40.4 | 373.1 (pin) | 151.2 | 903.2 | 2.42 / 5.97 | 0.0387 | 1.000 | 0.001 / 0.0 |
| Al 7075-T651 | LC1 | valid | 40.4 | 1,540.5 (bolt) | 336.7 | 421.3 | 0.27 / **1.25 (< 1.5)** | 0.3604 | **1.582** | 0.009 / 0.5 |
| Al 7075-T651 | LC2 | valid | 40.8 | 1,042.0 (bolt) | 210.6 | 421.3 | 0.40 / 2.00 | 0.2738 | **1.582** | 0.003 / 0.3 |
| Al 7075-T651 | LC3 | valid | 40.8 | 931.9 (bolt) | 217.2 | 421.3 | 0.45 / 1.94 | 0.1453 | **1.583** | 0.008 / 0.5 |
| Al 7075-T651 | LC4 | valid | 40.5 | 374.1 (pin) | 152.4 | 421.3 | 1.13 / 2.76 | 0.0612 | **1.581** | 0.001 / 0.0 |
| Al 6061-T651 | LC1 | valid | 41.1 | 1,540.5 (bolt) | 336.7 | 241.3 | 0.16 / **0.72 (> yield)** | 0.3748 | **1.645** | 0.009 / 0.5 |
| Al 6061-T651 | LC2 | valid | 40.2 | 1,042.0 (bolt) | 210.6 | 241.3 | 0.23 / **1.15 (< 1.5)** | 0.2847 | **1.645** | 0.003 / 0.3 |
| Al 6061-T651 | LC3 | valid | 40.7 | 931.9 (bolt) | 217.2 | 241.3 | 0.26 / **1.11 (< 1.5)** | 0.1511 | **1.646** | 0.008 / 0.5 |
| Al 6061-T651 | LC4 | valid | 39.7 | 374.1 (pin) | 152.4 | 241.3 | 0.65 / 1.58 | 0.0637 | **1.646** | 0.001 / 0.0 |
| 17-4PH H1025 | LC1 | valid | 39.5 | 1,633.4 (bolt) | 338.7 | 999.7 | 0.61 / 2.95 | 0.1269 | 0.557 | 0.003 / 0.3 |
| 17-4PH H1025 | LC2 | valid | 39.5 | 1,093.5 (bolt) | 214.8 | 999.7 | 0.91 / 4.65 | 0.0964 | 0.557 | 0.004 / 0.4 |
| 17-4PH H1025 | LC3 | valid | 39.6 | 978.3 (bolt) | 215.7 | 999.7 | 1.02 / 4.63 | 0.0514 | 0.560 | 0.004 / 0.2 |
| 17-4PH H1025 | LC4 | valid | 39.6 | 378.6 (pin) | 157.9 | 999.7 | 2.64 / 6.33 | 0.0215 | 0.556 | 0.000 / 0.0 |
| AISI 4140 Q&T | LC1 | valid | 39.9 | 1,604.3 (bolt) | 337.9 | 689.5 | 0.43 / 2.04 | 0.1276 | 0.560 | 0.004 / 0.5 |
| AISI 4140 Q&T | LC2 | valid | 39.5 | 1,077.9 (bolt) | 213.4 | 689.5 | 0.64 / 3.23 | 0.0970 | 0.560 | 0.005 / 0.3 |
| AISI 4140 Q&T | LC3 | valid | 39.5 | 963.8 (bolt) | 216.1 | 689.5 | 0.72 / 3.19 | 0.0516 | 0.562 | 0.003 / 0.1 |
| AISI 4140 Q&T | LC4 | valid | 39.8 | 377.3 (pin) | 156.2 | 689.5 | 1.83 / 4.41 | 0.0217 | 0.561 | 0.000 / 0.0 |

- **Balance.** The largest residuals are 0.009 N and 1.2 N·mm. Relative to the applied load that is 0.0001 %,
  far inside the 0.5 % tolerance.
- **Solver messages.** ccx logged no warnings and no errors in any run.
- **Timing.** Every solve took 39.5–41.1 s.
- **Files per run.** The CSV links each row's deck, `.frd` and map. Each run's folder also holds the FreeCAD
  document, the ccx log and the `.dat`.

## 4. Governing cases and screening, per material

| Material | Mass (g) | Governing stress case | vM outside exclusions (MPa) | Min SF outside | Meets SF 1.5 (all LCs) | Yield exceeded outside exclusions | Governing displacement case | Max disp (mm) | Within 1.1 × Ti (all LCs) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (baseline) | 2,052.2 | LC1 | 336.5 | 2.68 | yes | none | LC1 | 0.2278 | yes (reference) |
| Al 7075-T651 | 1,301.8 | LC1 | 336.7 | 1.25 | **no** | none | LC1 | 0.3604 | **no** |
| Al 6061-T651 | 1,250.8 | LC1 | 336.7 | 0.72 | **no** | LC1 | LC1 | 0.3748 | **no** |
| 17-4PH H1025 | 3,616.2 | LC1 | 338.7 | 2.95 | yes | none | LC1 | 0.1269 | yes |
| AISI 4140 Q&T | 3,616.2 | LC1 | 337.9 | 2.04 | yes | none | LC1 | 0.1276 | yes |

**Al 7075's stress failure depends on the exclusion radius** (section 5). At 10 mm its LC1 peak is 336.7 MPa, SF
1.25. At 10.5 mm it is 243.4 MPa, SF 1.73, and LC3 (217.2 MPa, SF 1.94) is next; it would then pass the stress
screen. It fails the displacement screen either way.

## 5. Where the peaks are

Deck-frame coordinates in mm. The locations are the same for every material.

| Case | Raw maximum | Maximum outside exclusions | Maximum displacement |
| --- | --- | --- | --- |
| LC1 | B2 fixed-patch edge (r 6.9 mm against the edge's 7.09), (−1.49, −7.00, 7.85) | **Fillet ring round B2's boss, r 10.34 mm from its axis**, (−1.20, −10.34, 9.39): 0.34 mm outside the bolt zone | −x tip of the +y lug, (−37.74, −57.16, 52.00) |
| LC2 | Same B2 patch-edge node | **Fillet ring round B1's boss, r 10.34 mm**, (57.24, −7.40, 9.39): 0.34 mm outside the bolt zone | Top of the +y lug, (−33.76, −57.04, 57.62) |
| LC3 | Same B2 patch-edge node | Arm root of the −y lug, (−13.59, −92.88, 30.46), 57 mm from any bolt | −x tip of the +y lug, (−39.06, −57.20, 47.59) |
| LC4 | Bore edge of the +y lug (pin zone), (−16.74, −57.16, 36.44) | Arm root of the −y lug, (−13.67, −92.65, 31.76) | −x tip of the −y lug, (−38.11, −93.39, 42.98) |

- **Raw peaks are support artefacts.** Each sits at an idealised boundary: the B2 fixed-patch edge (LC1–LC3) or
  the rigid bore (LC4), which are the risks listed in [M2A.4 §6](ge-manual-boundary-conditions.md). Peaks like
  these keep growing as the mesh is refined and are **not** used for screening.
- **The LC1 and LC2 screening peaks sit on the edge of the exclusion.** Both are on the fillet ring round a bolt
  boss at r 10.34 mm, about 3 mm from the singular fixed-patch edge at r 7.09 mm, where the L1 node spacing is
  about 1 mm. It is a ring, not one node: in Ti LC1, 41 nodes between r 10 and 10.5 mm exceed the next peak.
  Widening the bolt zone moves the screening peak (Ti shown; the other materials follow within 1 %):

  | Bolt exclusion radius (mm) | 10 | 10.5 | 11 | 12 | 15 | 20 |
  | --- | --- | --- | --- | --- | --- | --- |
  | LC1 peak outside (MPa) | 336.5 | 244.0 | 244.0 | 244.0 | 244.0 | 244.0 |
  | LC2 peak outside (MPa) | 209.8 | 155.9 | 137.0 | 127.0 | 127.0 | 127.0 |

  From 10.5 mm the LC1 peak is at (−17.37, −56.30, 29.21), the arm root of the +y lug, and it holds out to 20 mm.
  Whether the r 10.34 mm ring is real stress or the tail of the patch-edge singularity cannot be told from L1
  alone; that needs the convergence study (section 7). M2's parametric part had a similar case, where the peak
  just outside 10 mm converged ([M2.7 §4](m2-exchange.md)), but its supports are different.

## 6. Maps

`out/ge_manual_matrix/maps/<card>_<LC>.png`: one image per run, 20 in all. Each is a 2 × 2 grid:

- **Top row:** von Mises on the undeformed part.
- **Bottom row:** displacement magnitude on the deformed part.
- **Cameras:** the left column is the fixed isometric camera (+x, +y, +z); the right column is the fixed lug-side
  camera (−x, −y, +z). Both use the same parallel scale in every image.
- **Legend ranges are common across the five materials for each load case:**

  | Case | Stress range (MPa) | Displacement range (mm) | Deformation scale |
  | --- | --- | --- | --- |
  | LC1 | 0–338.7 | 0–0.3748 | × 21.3 |
  | LC2 | 0–214.8 | 0–0.2847 | × 28.1 |
  | LC3 | 0–217.6 | 0–0.1511 | × 52.9 |
  | LC4 | 0–157.9 | 0–0.0637 | × 125.6 |

  The stress top is the largest peak outside the exclusions among the five materials; anything above it is
  **magenta**, which in practice means only the excluded zones. The displacement top is the largest maximum
  among the five materials.
- **Markers:** a red sphere marks the raw peak and a black sphere the peak outside the exclusions.
- **Labels:** each image states the units, the view, the deformation scale and the range.

The maps are gitignored with the rest of `out/`. `--report-only` rebuilds them in about 15 s.

## 7. Open quality issues

1. **The L1 mesh is not accepted.** One element fails gamma ≥ 0.05 (0.0150), at the bottom edge of hole B2
   ([#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60)). Every run here is on that mesh.
2. **No mesh-convergence evidence.** Only L1 is used: L2 ran out of memory with this SPOOLES-only CalculiX on the
   16 GB host, and L2 and L3 were dropped ([mesh record §6](ge-manual-mesh.md)).
   - **Displacements and reactions** are probably close; displacement converges quickly.
   - **The screening stresses are not verified.** LC1 and LC2 sit 0.34 mm outside the bolt zone, and the LC1
     verdict for Al 7075 flips between 10 and 10.5 mm (section 5).
   - **The M2A matrix is complete but not verified.**
3. **Idealised supports.** The nut patches carry uplift, the base bottom has no contact and there is no bolt
   preload ([M2A.4 §6](ge-manual-boundary-conditions.md)).
4. **The rigid pin with no contact** overstates bore stiffness and spreads bearing load all round the bore.
5. **The GUI has not been walked through once.** The runs come from the script; M2A.3–M2A.5 each still need one
   manual pass as well.

## 8. Status against the M2A.6 checklist

| Requirement | Status |
| --- | --- |
| 20 analyses in FreeCAD FEM/CalculiX; documents, decks, logs and results retained | Done: `data/ge_manual/matrix/GE_Challenge_Bracket/L1/<card>/<LC>/` (gitignored) |
| Per run: status and warnings, time, mesh ID, material, mass, max von Mises and location, max displacement and location | Done (sections 3 and 5, CSV) |
| Support forces **and moments** against the applied load about a common origin, with tolerances | Done. Origin: the pin reference point; tolerance 0.5 %; every run passes (section 3) |
| No failed solve reported as a pass | No run failed. The script marks any failure as INVALID, with the reason and no metrics |
| Stress and displacement maps for every pair; units, view, deformation scale, consistent extraction; fixed cameras; common ranges | Done (sections 1 and 6) |
| Raw maxima alongside stress excluding a defined singularity zone; exclusion and convergence evidence visible | Done for raw values and exclusions, with the radius sensitivity (sections 2 and 5). **Convergence evidence is missing, and the mesh is not accepted** (section 7) |
| Report and a 20-row CSV | This page and [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) |
| Mass repeated and identical across LC1–LC4 | Done |
| Governing case per material; Ti labelled as the baseline; no alternative called challenge-compliant; yield exceedance labelled as failed screening | Done (summary, section 4) |

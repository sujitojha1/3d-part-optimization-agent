# GE manual analysis report — 5 materials × 4 load cases on the frozen L2 mesh (M2A.6)

> **4 Oct:** re-run on the repaired source (M2A.8, [#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66):
> the B2 bolt hole rebuilt) and its re-frozen **L2** mesh. Everything here comes from the current
> `out/ge_manual_matrix/matrix.json` and the CSV beside it. Earlier versions of this page (L1 on 23 Sep, the
> pre-repair L2 on 3 Oct) are in git history; their outputs are kept in `out/before-m2a8-repair/`.
> **What is and isn't verified:** displacement and the arm-root stresses are converged (L2 → L3r within 4.5 %). The
> LC1 and LC2 screening peaks at the 10 mm exclusion are **not**: they sit on the edge of the bolt zone (section 5).

| | |
| --- | --- |
| Task | M2A.6 ([#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19; regenerated 2026-09-23; re-run on L2 2026-10-03; re-run on the repaired source 2026-10-04 |
| Geometry | `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`, SHA-256 `435c6724cf8e1c87296bde2b95d696621a0b45fd19d7fc116a35b2bc8308897d` (the [M2A.4](ge-manual-boundary-conditions.md) partition of the [M2A.8 source](ge-manual-geometry.md)) |
| Mesh | **L2, frozen**: 170,937 nodes and 108,293 C3D10 elements, connectivity SHA-256 `e836f7dc…73b6c8ae` ([M2A.2](ge-manual-mesh.md)). Accepted: all seven quality rules pass (gamma min 0.187) |
| Setup | Supports and rigid pin from [M2A.4](ge-manual-boundary-conditions.md); LC1–LC4 from [M2A.5](ge-manual-load-cases.md); cards from [M2A.3](ge-manual-materials.md) |
| Tools | FreeCAD 1.1.3 FEM (CalculiX solver object) writes each deck; CalculiX 2.23 (SPOOLES) solves it. All 20 runs on the D-17 Mac |
| Script | `$FEM_PYTHON scripts/ge_manual_matrix.py` (about 1 h 45 min; about 5 GB per solve). It stops if the mesh on disk is not the frozen one. `--report-only` rebuilds the CSV, `matrix.json` and maps from the saved results |
| Data | [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) (20 rows); `out/ge_manual_matrix/matrix.json`; maps in `out/ge_manual_matrix/maps/` |
| Status | **20 of 20 runs solved and valid** on the accepted, frozen mesh. Every support force and moment balance is within 0.008 N and 0.8 N·mm. **Converged:** displacement, and the LC3 and LC4 screening stresses (arm root). **Not converged:** the LC1 and LC2 screening peaks at the 10 mm bolt zone, so the Al 7075 LC1 verdict still hinges on the exclusion radius (sections 5 and 7) |

## Summary

- **Ti-6Al-4V, the challenge baseline:** passes the project screen in every case.
  - Outside the exclusion zones, the peak von Mises stress is **396.0 MPa (LC1)**, a safety factor of 2.28 on GE's
    903.2 MPa yield. That peak is on the edge of the bolt zone and is not a converged stress. The converged
    governing stress is at the arm roots, **266.3 MPa** on L2 (264.0 on L3r), a safety factor of 3.4.
  - The maximum displacement is **0.2288 mm (LC1)**, converged to 0.0 % against L3r.
  - The mass is **2,052.2 g**.
- **The governing case is LC1 (vertical) for every material,** for both stress and displacement.
- **The stress field barely depends on the material.** The supports are fixed displacements, so the stress
  depends only on Poisson's ratio. LC1 peaks outside the exclusions vary by 0.8 % across the five cards (up to
  4 % in LC4). Displacement scales with 1/E.
- **Two alternatives fail the stress screen at the 10 mm exclusion:**
  - **Al 7075-T651:** LC1 safety factor 1.06 (396.3 MPa against 421.3 MPa), below the project's 1.5. Yield is not
    exceeded. **This verdict flips at a 10.5 mm exclusion** (SF 1.50), and at 11 mm the peak is the converged arm
    root (265.7 MPa, SF 1.59): see section 5.
  - **Al 6061-T651** exceeds yield in LC1 and LC2 (SF 0.61 and 0.94), and its LC3 safety factor is 1.04. **It fails
    at any exclusion radius:** the LC1 arm root alone (265.7 MPa) exceeds its 241.3 MPa yield, and LC3's 232.7 MPa
    is a converged arm-root stress.
  - A yield exceedance in a linear-elastic solve is a **failed screening result**, not a prediction of plastic
    collapse.
- **Both aluminium alloys also fail the project displacement limit,** 1.1 × Ti, at 1.58–1.65 × Ti.
- **17-4PH H1025 and AISI 4140 Q&T pass both screens,** with minimum safety factors of 2.51 and 1.73, but weigh
  3,616.2 g, 1.76 × Ti.
- **The alternatives are project comparisons, not challenge-compliant designs:** GE fixes Ti-6Al-4V.
  - Ti uses GE's 903.2 MPa yield; the others use specification minimums ([M2A.3 §1](ge-manual-materials.md)).
- **Raw peaks exceed yield in most runs.** They sit at idealised support and pin boundaries, where the stress is
  singular: up to 1,245 MPa at a fixed-patch edge. They are reported but not used for screening (section 5).
- **Against the pre-repair L2 matrix (3 Oct):** no pass/fail verdict changed. Displacements moved by 0.1 % or
  less. The LC1 zone-edge peak fell 5 % (417.9 → 396.0 MPa for Ti), most likely because the mesh round the rebuilt
  B2 hole differs; the arm-root and LC2–LC4 screening values moved by 2.2 % or less.

## 1. How each run was made

Each of the 20 runs is its own FreeCAD document, built from a fresh copy of the frozen L2 mesh document:

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
| **Ti-6Al-4V** (baseline) | LC1 | valid | 390.2 | 1,190.8 (bolt) | 396.0 | 903.2 | 0.76 / 2.28 | 0.2288 | 1.000 | 0.003 / 0.1 |
| **Ti-6Al-4V** (baseline) | LC2 | valid | 323.7 | 972.3 (bolt) | 257.4 | 903.2 | 0.93 / 3.51 | 0.1738 | 1.000 | 0.007 / 0.2 |
| **Ti-6Al-4V** (baseline) | LC3 | valid | 317.8 | 701.1 (bolt) | 232.9 | 903.2 | 1.29 / 3.88 | 0.0921 | 1.000 | 0.005 / 0.3 |
| **Ti-6Al-4V** (baseline) | LC4 | valid | 298.9 | 416.5 (pin) | 154.8 | 903.2 | 2.17 / 5.83 | 0.0388 | 1.000 | 0.001 / 0.1 |
| Al 7075-T651 | LC1 | valid | 289.2 | 1,200.1 (bolt) | 396.3 | 421.3 | 0.35 / **1.06 (< 1.5)** | 0.3618 | **1.581** | 0.004 / 0.2 |
| Al 7075-T651 | LC2 | valid | 287.8 | 979.0 (bolt) | 257.3 | 421.3 | 0.43 / 1.64 | 0.2749 | **1.582** | 0.003 / 0.3 |
| Al 7075-T651 | LC3 | valid | 288.0 | 706.1 (bolt) | 232.7 | 421.3 | 0.60 / 1.81 | 0.1458 | **1.583** | 0.002 / 0.4 |
| Al 7075-T651 | LC4 | valid | 338.3 | 417.6 (pin) | 155.9 | 421.3 | 1.01 / 2.70 | 0.0613 | **1.580** | 0.000 / 0.0 |
| Al 6061-T651 | LC1 | valid | 325.9 | 1,200.1 (bolt) | 396.3 | 241.3 | 0.20 / **0.61 (> yield)** | 0.3763 | **1.645** | 0.004 / 0.2 |
| Al 6061-T651 | LC2 | valid | 323.8 | 979.0 (bolt) | 257.3 | 241.3 | 0.25 / **0.94 (> yield)** | 0.2859 | **1.645** | 0.003 / 0.3 |
| Al 6061-T651 | LC3 | valid | 323.0 | 706.1 (bolt) | 232.7 | 241.3 | 0.34 / **1.04 (< 1.5)** | 0.1517 | **1.647** | 0.002 / 0.4 |
| Al 6061-T651 | LC4 | valid | 314.9 | 417.6 (pin) | 155.9 | 241.3 | 0.58 / 1.55 | 0.0637 | **1.642** | 0.000 / 0.0 |
| 17-4PH H1025 | LC1 | valid | 306.5 | 1,245.3 (bolt) | 399.0 | 999.7 | 0.80 / 2.51 | 0.1274 | 0.557 | 0.002 / 0.2 |
| 17-4PH H1025 | LC2 | valid | 287.7 | 1,011.6 (bolt) | 258.1 | 999.7 | 0.99 / 3.87 | 0.0968 | 0.557 | 0.008 / 0.4 |
| 17-4PH H1025 | LC3 | valid | 287.3 | 730.3 (bolt) | 232.1 | 999.7 | 1.37 / 4.31 | 0.0516 | 0.560 | 0.003 / 0.2 |
| 17-4PH H1025 | LC4 | valid | 290.3 | 422.7 (pin) | 161.0 | 999.7 | 2.37 / 6.21 | 0.0215 | 0.554 | 0.000 / 0.0 |
| AISI 4140 Q&T | LC1 | valid | 288.6 | 1,231.3 (bolt) | 397.9 | 689.5 | 0.56 / 1.73 | 0.1282 | 0.560 | 0.003 / 0.1 |
| AISI 4140 Q&T | LC2 | valid | 287.8 | 1,001.5 (bolt) | 257.7 | 689.5 | 0.69 / 2.68 | 0.0974 | 0.560 | 0.007 / 0.8 |
| AISI 4140 Q&T | LC3 | valid | 287.3 | 722.8 (bolt) | 232.2 | 689.5 | 0.95 / 2.97 | 0.0518 | 0.562 | 0.002 / 0.5 |
| AISI 4140 Q&T | LC4 | valid | 288.0 | 421.1 (pin) | 159.4 | 689.5 | 1.64 / 4.33 | 0.0217 | 0.559 | 0.000 / 0.0 |

- **Balance.** The largest residuals are 0.008 N and 0.8 N·mm. Relative to the applied load every one rounds to
  0.00 %, far inside the 0.5 % tolerance.
- **Solver messages.** ccx logged no warnings and no errors in any run.
- **Timing.** Solves took 287–390 s; 102 min for the 20.
- **Files per run.** The CSV links each row's deck, `.frd` and map. Each run's folder also holds the FreeCAD
  document, the ccx log and the `.dat`.

## 4. Governing cases and screening, per material

| Material | Mass (g) | Governing stress case | vM outside exclusions (MPa) | Min SF outside | Meets SF 1.5 (all LCs) | Yield exceeded outside exclusions | Governing displacement case | Max disp (mm) | Within 1.1 × Ti (all LCs) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (baseline) | 2,052.2 | LC1 | 396.0 | 2.28 | yes | none | LC1 | 0.2288 | yes (reference) |
| Al 7075-T651 | 1,301.8 | LC1 | 396.3 | 1.06 | **no** | none | LC1 | 0.3618 | **no** |
| Al 6061-T651 | 1,250.8 | LC1 | 396.3 | 0.61 | **no** | LC1, LC2 | LC1 | 0.3763 | **no** |
| 17-4PH H1025 | 3,616.2 | LC1 | 399.0 | 2.51 | yes | none | LC1 | 0.1274 | yes |
| AISI 4140 Q&T | 3,616.2 | LC1 | 397.9 | 1.73 | yes | none | LC1 | 0.1282 | yes |

**Al 7075's stress failure depends on the exclusion radius** (section 5). At 10 mm its LC1 peak is 396.3 MPa, SF
1.06. At 10.5 mm it is 280.0 MPa, SF 1.50, and at 11 mm and beyond it is the arm root, 265.7 MPa, SF 1.59; LC2
(SF 1.64) and LC3 (232.7 MPa, SF 1.81) are next. It would then pass the stress screen. It fails the displacement
screen either way.

**Al 6061's does not.** With the bolt zone at 11 mm or more, LC1 is still 265.7 MPa at the arm root, above its
241.3 MPa yield.

## 5. Where the peaks are

Deck-frame coordinates in mm. The locations are the same for every material, except one displacement maximum
noted in the table.

| Case | Raw maximum | Maximum outside exclusions | Maximum displacement |
| --- | --- | --- | --- |
| LC1 | B2, just outside the fixed-patch edge (r 7.29 mm against the edge's 7.09), (−7.08, −1.95, 7.85) | **Fillet ring round B2's boss, r 10.05 mm from its axis**, (−2.80, −9.73, 8.89): 0.05 mm outside the bolt zone | −x tip of the +y lug, (−37.38, −57.15, 52.76) |
| LC2 | The same B2 node | **Fillet ring round B1's boss, r 10.01 mm**, (48.63, −7.91, 8.83): 0.01 mm outside the bolt zone | Top of the +y lug, (−33.32, −58.93, 57.97) |
| LC3 | B2, just outside the patch edge, (1.84, −7.10, 7.85) | Arm root of the −y lug, (−15.19, −92.88, 29.85), 57 mm from any bolt | −x tip of the +y lug, (−39.09, −57.20, 47.38); for 17-4PH the −y lug tip, (−38.18, −93.39, 45.50) |
| LC4 | Bore edge of the −y lug (pin zone), (−15.28, −92.06, 36.68) | Arm root of the −y lug, (−13.02, −92.67, 31.46) | −x tip of the −y lug, (−38.16, −93.39, 43.61) |

- **Raw peaks are support artefacts.** Each sits at an idealised boundary: a fixed-patch edge (LC1–LC3) or the
  rigid bore (LC4), which are the risks listed in [M2A.4 §6](ge-manual-boundary-conditions.md). They rise 3–11 %
  from L1 to L2 and are **not** used for screening ([mesh record §6](ge-manual-mesh.md)).
- **The LC3 and LC4 screening peaks are converged.** Both are at an arm root, far from every support, and
  change by −0.7 % and −0.3 % from L2 to L3r.
- **The LC1 and LC2 screening peaks sit on the edge of the exclusion, and are not converged.** Each is a node on
  the fillet ring round a bolt boss, 0.01–0.05 mm outside the zone and 3 mm from the singular fixed-patch edge at
  r 7.09 mm. They rose 16–21 % from L1 to L2, and L3r did not refine that area, so nothing tests them. It is a
  ring, not one node: in Ti LC1, 113 nodes between r 10 and 11 mm exceed the next peak. Widening the bolt zone
  moves the screening peak (Ti shown; the other materials follow within 2 %):

  | Bolt exclusion radius (mm) | 10 | 10.5 | 11 | 12 | 15 | 20 |
  | --- | --- | --- | --- | --- | --- | --- |
  | LC1 peak outside (MPa) | 396.0 | 280.3 | 266.3 | 266.3 | 266.3 | 266.3 |
  | LC2 peak outside (MPa) | 257.4 | 183.0 | 143.7 | 131.1 | 131.1 | 131.1 |

  - **LC1:** at 10.5 mm the peak is still a zone-edge node at B2. From 11 mm it is (−15.19, −92.88, 29.85), the
    arm root of the −y lug, and it holds out to 20 mm. The arm-root maximum is converged: 264.0 MPa on L3r,
    −0.9 %, where it sits on the +y lug.
  - **LC2:** at 10.5 and 11 mm the peak is still a zone-edge node. From 12 mm it is the −y arm root,
    (−2.23, −92.35, 36.49), 135.5 MPa on L3r, +3.4 %.
  - **So the 10 mm radius is too small for this part on L2.** At 12 mm every screening peak is a converged
    arm-root stress. Changing the radius is an acceptance decision, left open here (section 7).

## 6. Maps

`out/ge_manual_matrix/maps/<card>_<LC>.png`: one image per run, 20 in all. Each is a 2 × 2 grid:

- **Top row:** von Mises on the undeformed part.
- **Bottom row:** displacement magnitude on the deformed part.
- **Cameras:** the left column is the fixed isometric camera (+x, +y, +z); the right column is the fixed lug-side
  camera (−x, −y, +z). Both use the same parallel scale in every image.
- **Legend ranges are common across the five materials for each load case:**

  | Case | Stress range (MPa) | Displacement range (mm) | Deformation scale |
  | --- | --- | --- | --- |
  | LC1 | 0–399.0 | 0–0.3763 | × 21.3 |
  | LC2 | 0–258.1 | 0–0.2859 | × 28.0 |
  | LC3 | 0–232.9 | 0–0.1517 | × 52.7 |
  | LC4 | 0–161.0 | 0–0.0637 | × 125.6 |

  The stress top is the largest peak outside the exclusions among the five materials; anything above it is
  **magenta**, which in practice means only the excluded zones. The displacement top is the largest maximum
  among the five materials.
- **Markers:** a red sphere marks the raw peak and a black sphere the peak outside the exclusions.
- **Labels:** each image states the units, the view, the deformation scale and the range.

The maps are gitignored with the rest of `out/`. `--report-only` rebuilds them without solving.

## 7. Open quality issues

1. **The bolt exclusion radius decides two results.** At 10 mm the LC1 and LC2 screening peaks are unconverged
   zone-edge values; at 12 mm they are converged arm-root stresses (section 5). This changes Al 7075's stress
   verdict (fail at 10 mm, a bare pass at 10.5 mm, SF 1.59 from 11 mm) and every LC1 and LC2 safety factor. It does not change Ti, Al 6061
   or the steels' pass/fail. The radius was fixed at 10 mm before any M2A.6 result, so moving it needs an owner
   decision; a level refining the `nut_seat` region would test the ring directly.
2. **Convergence evidence is Ti-only.** The M2A.2 study ran L1 / L2 / L3r for Ti-6Al-4V. The other four cards
   share the mesh, supports and loads, and their stress fields differ from Ti's by under 1 % in LC1, so the same
   conclusions are expected to hold, but they were not run on L3r.
3. **Idealised supports.** The nut patches carry uplift, the base bottom has no contact and there is no bolt
   preload ([M2A.4 §6](ge-manual-boundary-conditions.md)).
4. **The rigid pin with no contact** overstates bore stiffness and spreads bearing load all round the bore.
5. **The GUI has not been walked through once.** The runs come from the script; M2A.3–M2A.5 each still need one
   manual pass as well.

## 8. Status against the M2A.6 checklist

| Requirement | Status |
| --- | --- |
| 20 analyses in FreeCAD FEM/CalculiX; documents, decks, logs and results retained | Done: `data/ge_manual/matrix/GE_Challenge_Bracket/L2/<card>/<LC>/` (gitignored) |
| Per run: status and warnings, time, mesh ID, material, mass, max von Mises and location, max displacement and location | Done (sections 3 and 5, CSV) |
| Support forces **and moments** against the applied load about a common origin, with tolerances | Done. Origin: the pin reference point; tolerance 0.5 %; every run passes (section 3) |
| No failed solve reported as a pass | No run failed. The script marks any failure as INVALID, with the reason and no metrics |
| Stress and displacement maps for every pair; units, view, deformation scale, consistent extraction; fixed cameras; common ranges | Done (sections 1 and 6) |
| Raw maxima alongside stress excluding a defined singularity zone; exclusion and convergence evidence visible | Done: raw values, exclusions and the radius sensitivity (sections 2 and 5), on the accepted, frozen mesh, with the [M2A.2 convergence study](ge-manual-mesh.md) behind it. **Open:** the LC1 and LC2 peaks at the 10 mm zone edge are not converged (section 7) |
| Report and a 20-row CSV | This page and [`ge-manual-analysis-matrix.csv`](ge-manual-analysis-matrix.csv) |
| Mass repeated and identical across LC1–LC4 | Done |
| Governing case per material; Ti labelled as the baseline; no alternative called challenge-compliant; yield exceedance labelled as failed screening | Done (summary, section 4) |

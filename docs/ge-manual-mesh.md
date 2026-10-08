# GE manual mesh — procedure and quality (M2A.2)

> **4 Oct:** rewritten for the current part, `GE_Challenge_Bracket`, on the repaired M2A.8 source
> ([#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66)). Everything here comes from the
> current `out/ge_manual_mesh/mesh-quality.json` and the Ti runs in `data/ge_manual/matrix/`. The Iteration1 record
> and the pre-repair study (3 Oct) are in git history; section 4 keeps how the settings were reached.

| | |
| --- | --- |
| Task | M2A.2 ([#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19; convergence study 2026-10-03; re-meshed and re-run on the repaired source 2026-10-04 |
| Input | Partitioned working copy `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`, SHA-256 `435c6724…8308897d`: the [M2A.1](ge-manual-geometry.md) working copy with the four nut seats split at Ø 14.173 by [M2A.4](ge-manual-boundary-conditions.md) |
| Tools | FreeCAD 1.1.3 FEM Workbench → `FemMeshGmsh` → Gmsh 4.15.2 (`vendor/fem-env/bin/gmsh`); quality from the Gmsh 4.15.2 Python API |
| Script | `$FEM_PYTHON scripts/ge_manual_mesh.py --levels L1 L2 L3r L3 --refreeze` (about 2 min). It builds the same objects as the manual steps in section 1 and writes `out/ge_manual_mesh/mesh-quality.json`. Without `--refreeze` it will not re-mesh the frozen level |
| Status | **All four levels pass the seven quality thresholds, L1 included.** **Convergence done for Ti LC1–LC4** on L1 / L2 / L3r: displacement converges within 0.1 % and arm-root stress within 4.5 % (section 6); the boss-ring peak at the 10 mm zone edge does not. **L2 is the frozen mesh**, recorded in `scripts/ge_part.py`. One GUI walk-through is still needed |

## 1. Manual steps (FreeCAD 1.1.3 GUI)

1. **Set Gmsh to one thread.** Edit → Preferences → FEM → Gmsh, and set the number of threads to **1**. With the
   default (all cores), the same input gave different node counts from one run to the next (seen on Iteration1).
   The script sets this preference only for its own run and then restores it.
2. **Open the geometry.** Open `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd` and switch to the **FEM**
   workbench. `Bracket` is already in the SimJEB deck frame (+z up, out = −x).
3. **Create the Analysis.** Model → **Analysis container**.
4. **Create the mesh object.** Select `Bracket` in the tree, then Mesh → **FEM mesh from shape by Gmsh**.
   - In the task panel, set **Element dimension 3D**, **Element order 2nd**, and the level's **Max size** and
     **Min size** from section 2.
   - Close the panel with **OK** and don't mesh yet. The mesh object lands in the Analysis.
5. **Set the remaining mesh properties.** Select `Mesh` and set these in the Property editor:
   - `High Order Optimize` = **Optimization**
   - `Second Order Linear` = **false**, so midside nodes lie on the curved geometry
   - `Optimize Netgen` = **true**. This is not the FreeCAD default; section 4 explains why it's needed.
   - `Mesh Size From Curvature` = the level's value from section 2
   - Leave everything else at the default: Algorithm2D/3D Automatic, OptimizeStd true, GeometryTolerance 1e-6,
     CoherenceMesh true, no recombination or subdivision.
6. **Add the four mesh regions.** With `Mesh` selected, run Mesh → **FEM mesh refinement** four times. For each
   region, set **Max element size** to the level's region size, click **Add**, and pick the faces listed below.
   This Python console form sets the same references:
   ```python
   doc = App.ActiveDocument; b = doc.Bracket
   doc.MeshRegion.References = [(b, ("Face57", "Face58", ...))]   # paste a list from below
   ```

   | Region | What it covers | Faces |
   | --- | --- | --- |
   | `pin_bore` (6) | Both lug bores (r 9.557) and their four chamfer cones | Face57–Face62 |
   | `arm_root` (4) | The R 3.175 blends where the clevis arms meet the body | Face41, Face45, Face47, Face51 |
   | `nut_seat` (16) | Bolt-hole walls, the four seat annuli (z = 7.849; each a nut patch and a free ring) and the R 2.54 counterbore blends | Face1, Face3, Face4, Face15–Face18, Face31–Face36, Face54–Face56 |
   | `thin_section` (4) | Faces within 1 mm of M2A.1's thinnest wall samples (4.66 mm, between a counterbore and a base end wall) | Face5, Face10, Face12, Face53 |

   The script chooses these faces by geometric predicate (`select_regions`), not by stored index, and records
   the lists in `mesh-quality.json`. Face numbers are valid only for the working copy with the checksum above.
7. **Mesh.** Double-click `Mesh`, then click **Apply** in the task panel. Record the Gmsh output and the node and
   element counts it prints.
8. **Save.** Save the document under the level's name, for example `GE_Challenge_Bracket_mesh_L2.FCStd`.
9. **Inspect and measure.** Look at the sections (section 5), then run the script to get the quality metrics.
   The FreeCAD GUI does not report signed Jacobian or scaled Jacobian.

## 2. Levels and settings

Curvature is set explicitly: FreeCAD's default of 12 elements per 2π puts needlessly small elements on every
blend. All sizes are in mm.

| Level | Max | Min | Region size | Curvature (elements per 2π) | Nodes | C3D10 | Gmsh time | Role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 5.0 | 1.0 | 2.0 | 4 | 89,473 | 55,004 | 8.7 s | Convergence study, coarse |
| **L2** | 4.0 | 1.0 | 1.5 | 6 | 170,937 | 108,293 | 17.3 s | **Frozen**; M2A.3–M2A.6 run on it |
| L3r | 4.0 | 0.75 | 1.5; `arm_root` 1.0 | 6 | 226,381 | 145,600 | 24.0 s | Convergence study, fine at the arm roots |
| L3 | 3.0 | 0.75 | 1.0 | 9 | 409,928 | 267,640 | 58.0 s | Meshed for quality only; not solved |

Element counts by type, identical between the FreeCAD `FemMesh` and the `.unv`:

| Level | Line3 | Triangle6 | Tetrahedron10 |
| --- | --- | --- | --- |
| L1 | 1,755 | 15,608 | 55,004 |
| L2 | 2,258 | 25,774 | 108,293 |
| L3r | 2,454 | 31,276 | 145,600 |
| L3 | 3,247 | 51,566 | 267,640 |

**Why L3r, not L3, is the third solved level.** The `ccx` in the FEM environment links **SPOOLES only**, a direct
solver: PARDISO and PaStiX are not linked. A global L3 (about 1.2 M degrees of freedom) would need about 13 GB,
which a 16 GB host doesn't have. L3r keeps L2's global sizes and refines only the `arm_root` region to L3's
1.0 mm, with the global minimum at 0.75 mm so that size is not clamped. `ITERATIVE CHOLESKY` fits in memory, but
its fixed stopping tolerance left displacement 2.2 % and nodal stress up to 25 MPa off SPOOLES on L1, so it is
not used.

## 3. Quality metrics and acceptance thresholds

These thresholds were fixed in `THRESHOLDS` in the script before any mesh was accepted, and they were not
changed after seeing results. Every metric comes from `gmsh.model.mesh.getElementQualities` in Gmsh 4.15.2, run
on the `.unv` that FreeCAD reads back.

| Metric | Definition (Gmsh 4.15.2) | Threshold |
| --- | --- | --- |
| Inverted / degenerate | `minDetJac` ≤ 0 (signed Jacobian determinant, minimum over the tet10's sampling points), or \|`volume`\| < 1e-9 × mean | **0 elements** |
| Scaled Jacobian | `minSJ`: minimum scaled Jacobian of the curved (quadratic) element; 1 is ideal, ≤ 0 is invalid | min ≥ 0.1; 0.1th percentile ≥ 0.3 |
| Gamma | `gamma`: inscribed-to-circumscribed radius ratio normalised to 1 for a regular tet, taken on the corner nodes | min ≥ 0.05; at most 0.1 % of elements below 0.2 |
| Aspect ratio | `maxEdge` / `minEdge` of the element | max ≤ 20; 99.9th percentile ≤ 8 |

The scaled-Jacobian minimum of 0.1 equals Gmsh's own high-order optimiser target (`Mesh.HighOrderThresholdMin`,
default 0.1). FreeCAD 1.1.3 doesn't expose that setting, so the optimiser stops near 0.1 and the worst elements
cluster there. **L1's margin on this rule is thin by construction** (0.115).

Other metrics: an edge-ratio aspect ratio is reported instead of Gmsh's `eta`/`SICN`. Gmsh's `minSICN` and
`minIsotropy` exist but are not used.

### Results

| Metric | L1 | L2 (frozen) | L3r | L3 |
| --- | --- | --- | --- | --- |
| Inverted (`minDetJac` ≤ 0) / zero volume | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `minSJ` min / p0.1 / p1 / p5 / median | 0.115 / 0.420 / 0.693 / 0.881 / 1.000 | 0.307 / 0.590 / 0.800 / 0.914 / 1.000 | 0.302 / 0.603 / 0.807 / 0.919 / 1.000 | 0.554 / 0.727 / 0.854 / 0.950 / 1.000 |
| `gamma` min / p0.1 / p1 / median | 0.195 / 0.302 / 0.490 / 0.826 | 0.187 / 0.418 / 0.527 / 0.844 | 0.207 / 0.401 / 0.521 / 0.850 | 0.220 / 0.435 / 0.546 / 0.860 |
| Fraction with `gamma` < 0.2 | 0.0018 % | 0.0009 % | 0 | 0 |
| Aspect ratio median / p99.9 / max | 1.58 / 3.21 / 4.07 | 1.54 / 2.76 / 3.50 | 1.52 / 2.73 / 3.79 | 1.50 / 2.61 / 3.73 |
| **Accepted (all seven rules)** | **yes** | **yes** | **yes** | **yes** |

Worst elements, with element IDs as in the `.unv` and `FemMesh`, and centroids in the deck frame (mm):

| Level | Worst by `minSJ` | Worst by `gamma` |
| --- | --- | --- |
| L1 | #64070 0.115 at (−8.2, 0.6, 7.6), by the B2 counterbore | #37035 0.195 at (−26.8, −90.7, 52.2), on the −y lug |
| L2 | #135642 0.307 at (−7.5, −155.8, 9.6), by the B3 counterbore | #84639 0.187 at (59.1, −65.5, 1.1), on the +x base wall |
| L3r | #37170 0.302 at (−7.6, −141.1, 9.4), by the B3 counterbore | #132022 0.207 at (23.5, −91.4, 48.4), on the top slope |
| L3 | #60605 0.554 at (47.2, −148.1, 8.0), by the B4 counterbore | #74410 0.220 at (27.4, −84.2, 48.9), on the top slope |

No worst element sits at a geometry artefact any more. **Before the M2A.8 repair, L1 failed:** one element at the
bottom edge of hole B2 had gamma 0.015, forced by a 0.207 mm sliver edge in the hole
([geometry record §2](ge-manual-geometry.md)). With the hole rebuilt, L1's gamma minimum is 0.195 and its largest
aspect ratio fell from 8.58 to 4.07. Gmsh logs no warning at any level.

## 4. How the accepted settings were reached

The settings were worked out on Iteration1 (19 Sep) and carried over unchanged. Node counts in this table are
Iteration1's.

| Attempt | Change | Result |
| --- | --- | --- |
| 1 | FreeCAD defaults plus M2 sizes: max 4, min 1, regions 1.5, curvature 12, OptimizeNetgen off | 982k nodes at the coarsest level. `gamma` min 0.006, so **rejected**. Too large for the solver anyway |
| 2 | Curvature as a level parameter (6/9/12) with max 4/3/2 | L1 331k, L2 891k, L3 2.83M nodes. All **rejected**: `minSJ` 0.001–0.088 and `gamma` 0.002–0.045 at the tiny B-spline faces; at L2 Gmsh logged "Failed to reach critical value … ScaledJac". L3 is too large for SPOOLES in 16 GB |
| 3 | **`OptimizeNetgen = true`**, tried on attempt 2's L2 | All thresholds pass (`minSJ` 0.127, `gamma` 0.119) |
| 4 | Levels moved one step coarser (section 2) to stay solvable; Netgen on | All pass, but a rerun of L2 gave different counts, so **not repeatable** |
| 5 | Gmsh single-threaded (step 1) | Counts, connectivity and quality identical across runs. L1 then failed `gamma` (0.035) at the tiny faces with min 1.25 |
| 6 | L1 minimum size 1.25 → 1.0, the same as L2 | **Accepted** (section 3) |
| Rejected fix | A 0.4 mm refinement region on the 44 faces under 3 mm², with global min 0.4 | Passes, but curvature sizing then drives L1 to 812k and L3 to 1.88M nodes |
| 7 | L2 and L3 dropped after the L2 solve ran out of memory (section 2) | **L1 only** |
| 8 | Part changed to `GE_Challenge_Bracket` (20 Sep); L2 and L3 brought back for the convergence study, and L3r added (23 Sep) | L2, L3r and L3 passed; **L1 failed `gamma`** (0.015) on one element at hole B2 |
| 9 | M2A.8: the B2 hole rebuilt in the source, removing its two 0.207 mm sliver edges (4 Oct) | **All four levels accepted** (section 3), with no change to any size or setting |

Trials with `SecondOrderLinear` (straight midside nodes) were not needed: no accepted curved mesh has an inverted
element. No threshold was relaxed and no exception is carried.

## 5. Repeatability, files and sections

**Repeatability** was established on Iteration1 and has not been re-tested on this part. There, single-threaded
Gmsh reproduced node and element counts, connectivity and every quality number exactly, while node coordinates
varied by up to 1×10⁻⁵ mm between runs. The `.unv` and FCStd bytes, and so their SHA-256, therefore do **not**
repeat. The mesh identity is the level settings plus the **connectivity SHA-256** (tet10 node lists in `.unv`
order) and the node and element counts.

| Level | Connectivity SHA-256 |
| --- | --- |
| L1 | `44436b4ede83e3a388da51c59a5294b20b2605a00a5dda4519080fc790b0bfff` |
| **L2** | `e836f7dca4614168b37b04a4c6c3a264e834a39895f7dec11f67254e73b6c8ae` |
| L3r | `9ea3b9856ebd4dae5b63681710fb9cee9aa4e173ea9f7fa0f2a40480e2fa2919` |
| L3 | `4b38c2da48bbdd896e00e07d8ea13c8142b0dc85f0c62bba176d20c06ab06ffc` |

Full checksums of every file are in `out/ge_manual_mesh/mesh-quality.json`. The files are gitignored, because they
are derived from GrabCAD non-commercial CAD:

- `data/ge_manual/mesh/<level>/GE_Challenge_Bracket_mesh_<level>.FCStd`: Analysis, Mesh and four MeshRegions,
  ready for M2A.3–M2A.5 to add material, supports and loads;
- `Bracket_Mesh.unv`, `shape2mesh.geo` and `Bracket_Geometry.brep` alongside it.

**Section and quality views** are in `out/ge_manual_mesh/<level>/`:

- `quality_histograms.png`: `minSJ`, `gamma` and aspect ratio, log-scale counts, threshold lines;
- `worst_elements.png`: the 10 worst elements by `minSJ`, with IDs;
- `section_lug_bore.png`, `section_arm_root.png`, `section_bolt_B2_B1.png` and `section_thin_wall_z21.png`:
  crinkle-clipped sections through the lug and bore, both arm roots, bolts B2 and B1 with their seats, and the
  base end walls, coloured by `minSJ`.

The through-thickness element count at the 4.66 mm walls was not measured; check it in the GUI walk-through.

## 6. Convergence study (Ti-6Al-4V, LC1–LC4)

Tolerances are the ones fixed before comparison: max displacement changes ≤ 2 %; stress outside the singularity
zones changes ≤ 5 %; reactions balance the applied load within 0.5 %; a raw peak that moves more than 20 % is
flagged, never hidden. The comparison that is judged is the two finest levels, L2 → L3r.

**Where the runs were made.** All twelve on the D-17 FEM environment on this Mac: ccx 2.23 with SPOOLES, on
4 Oct, with `ge_manual_matrix.py --level <level> --cards ti6al4v`.

| Level | Wall per solve | SPOOLES peak memory |
| --- | --- | --- |
| L1 | 98–142 s | 2.1 GB |
| L2 | 299–390 s | 4.5–5.1 GB |
| L3r | 557–739 s | 6.3–6.9 GB |

Memory was measured on the pre-repair meshes (3 Oct), which are within 2 % of these in size; it was not
re-measured.

**How each quantity is read.** Von Mises is the matrix's nodal-averaged stress. The arm-root values are the
maximum over the mesh nodes lying on that fillet face: Face51 is the +y lug's outer arm-root fillet and Face41
the −y lug's. "Outside the 10 mm zone" is the M2A.6 screening peak: outside the pin exclusion and 10 mm from every
bolt axis.

**Maximum displacement (mm)**

| Case | L1 | L2 | L3r | L2 → L3r | ≤ 2 % |
| --- | --- | --- | --- | --- | --- |
| LC1 | 0.2275 | 0.2288 | 0.2287 | 0.0 % | ✅ |
| LC2 | 0.1729 | 0.1738 | 0.1737 | −0.1 % | ✅ |
| LC3 | 0.0916 | 0.0921 | 0.0921 | 0.0 % | ✅ |
| LC4 | 0.0387 | 0.0388 | 0.0388 | 0.0 % | ✅ |

**Arm-root fillets, away from every constraint singularity (MPa)**

| Case | Face | L1 | L2 | L3r | L1 → L2 | L2 → L3r | ≤ 5 % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LC1 | +y (Face51) | 244.8 | 257.0 | **264.0** | +5.0 % | +2.7 % | ✅ |
| LC1 | −y (Face41) | 239.7 | 266.3 | 254.3 | +11.1 % | **−4.5 %** | ✅ |
| LC2 | +y | 122.2 | 126.3 | 128.4 | +3.4 % | +1.7 % | ✅ |
| LC2 | −y | 127.2 | 131.1 | **135.5** | +3.1 % | +3.4 % | ✅ |
| LC3 | +y | 199.3 | 205.9 | 214.4 | +3.3 % | +4.1 % | ✅ |
| LC3 | −y | 217.7 | 232.9 | **231.2** | +7.0 % | −0.7 % | ✅ |
| LC4 | +y | 149.1 | 151.9 | **154.4** | +2.1 % | +1.6 % | ✅ |
| LC4 | −y | 150.7 | 154.8 | 153.0 | +2.7 % | −1.2 % | ✅ |

Bold marks the larger of the two arm roots at L3r. Taking that larger value at each level, the governing
arm-root stress changes by −0.9 % (LC1), +3.4 % (LC2), −0.7 % (LC3) and −0.3 % (LC4) from L2 to L3r. The mean
distance between neighbouring nodes on these fillets is 0.90 / 0.65 / 0.38 mm at L1 / L2 / L3r.

**Peak outside the 10 mm bolt zone (MPa)**

| Case | L1 | L2 | L3r | L1 → L2 | L2 → L3r | Where | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LC1 | 326.3 | 396.0 | 394.2 | **+21 %** | (−0.5 %) | boss ring at B2, r 10.34 → 10.05 → 10.07 | **not converged, not tested by L3r** |
| LC2 | 222.3 | 257.4 | 257.7 | **+16 %** | (+0.1 %) | boss ring at B1, r 10.34 → 10.01 → 10.01 | **not converged, not tested by L3r** |
| LC3 | 217.7 | 232.9 | 231.2 | +7.0 % | −0.7 % | −y arm root | converged |
| LC4 | 150.7 | 154.8 | 154.4 | +2.7 % | −0.3 % | arm root | converged |

**Raw peaks (MPa), reported and never used**

| Case | L1 | L2 | L3r | L1 → L2 | L2 → L3r | Where |
| --- | --- | --- | --- | --- | --- | --- |
| LC1 | 1,103.0 | 1,190.8 | 1,189.5 | +8.0 % | −0.1 % | B2 fixed-patch edge |
| LC2 | 880.1 | 972.3 | 971.6 | +10.5 % | −0.1 % | fixed-patch edge (B3 at L1, B2 from L2) |
| LC3 | 680.2 | 701.1 | 708.9 | +3.1 % | +1.1 % | B2 fixed-patch edge |
| LC4 | 377.0 | 416.5 | 409.5 | +10.5 % | −1.7 % | pin exclusion (rigid-bore boundary) |

No raw peak moves more than 20 % between levels, so none is flagged. That is not convergence: L3r keeps L2's
sizes at the seats and the bores, so L2 → L3r does not test them, and L1 → L2 still moves them by up to 10.5 %.

**Reactions.** All 12 runs are solver-valid, and every support force and moment residual rounds to 0.00 % of the
applied load (tolerance 0.5 %).

**What this settles and what it doesn't**
- **Displacement is converged in all four cases**, to 0.1 % or better between L2 and L3r.
- **The arm-root fillets are converged in all four cases**: the largest L2 → L3r change on any fillet is 4.5 %
  (LC1, −y), inside the 5 % tolerance. The governing stress is about **264 MPa in LC1**, then 231 (LC3),
  154 (LC4) and 136 MPa (LC2).
- **The margin on that tolerance is smaller than on the pre-repair meshes** (3.0 % there). Which lug carries the
  LC1 maximum also swaps between L2 (−y) and L3r (+y); the two differ by under 4 % at either level.
- **L1 is not converged**, although it now passes quality: it reads an arm root up to 11.1 % low (LC1, −y).
- **The boss ring just outside the 10 mm bolt zone is not a converged stress in LC1 or LC2.** It rises 16–21 %
  from L1 to L2 and sits on the zone edge (r 10.01–10.05), which is how the tail of the fixed-patch-edge
  singularity behaves. L3r left that area at L2 size, so its −0.5 % and +0.1 % say nothing either way. With an
  11 mm zone the LC1 peak is the arm root; in LC2 it is still a zone-edge node (143.7 MPa at r 11.02), and only
  at 12 mm is it the arm root. The radius is the open acceptance question in the
  [analysis report §7](ge-manual-analysis-report.md); a level refining `nut_seat` would test the ring directly.
- **L2 is the frozen mesh.** First frozen on 3 Oct (owner decision) and re-frozen on 4 Oct on the repaired
  source, with the same level and sizes and a new connectivity.
  - **Record:** `scripts/ge_part.py` holds the level and its connectivity SHA-256, `e836f7dc…73b6c8ae`.
  - **Guards:** `ge_manual_matrix.py` runs on L2 by default and stops if the mesh document or its quality record
    is not the frozen one; `ge_manual_mesh.py` will not re-mesh L2 without `--refreeze`.
  - **M2A.3–M2A.6 are run on L2** ([materials](ge-manual-materials.md),
    [boundary conditions](ge-manual-boundary-conditions.md), [load cases](ge-manual-load-cases.md),
    [analysis report](ge-manual-analysis-report.md)); their scripts default to the frozen level.

## 7. Status against the M2A.2 checklist

| Step | Status |
| --- | --- |
| 1. Working copy, Analysis, Gmsh mesh, C3D10 | Done (section 1) |
| 2. All settings recorded; start from M2 evidence; local MeshRegions at arm roots, bores, nut seats and thin sections | Done (sections 1, 2 and 4) |
| 3. Generate; inspect sections; mesher version; counts by type; time; files and checksums | Done (sections 2, 3 and 5). **The GUI walk-through still needs one manual run** to confirm the steps as written; the numbers above come from the script |
| 4. Named metrics, distributions, worst IDs and locations, histograms, worst-element views; unavailable metrics stated | Done (section 3) |
| 5. Zero inverted; thresholds fixed before acceptance; failures corrected by sizing | Done (sections 3 and 4). The one L1 failure was corrected in the geometry (M2A.8), not by relaxing a threshold |
| 6. Three levels × LC1–LC4 convergence; freeze | **Convergence done for Ti LC1–LC4** on L1 / L2 / L3r (section 6): displacement and arm-root stress meet the tolerances; the boss-ring peak at the 10 mm zone edge does not converge and is flagged. **Frozen on L2** |

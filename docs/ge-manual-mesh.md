# GE manual mesh — procedure and quality (M2A.2)

> **21 Sep status:** This document contains historical Iteration1 study evidence. Current scripts select `GE_Challenge_Bracket`; current mesh quality is rejected (gamma minimum 0.014993 < 0.05), and replacement acceptance is open in #66/#60. See [the current audit](progress-review-2026-09-21.md) for geometry hashes, progress and remaining checks. Do not treat the older geometry/face IDs/numeric results below as verification of the replacement.

| | |
| --- | --- |
| Task | M2A.2 ([#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19 |
| Input | Partitioned working copy `data/ge_manual/Iteration1_partitioned.FCStd`, SHA-256 `b025011c…790af6`: the [M2A.1](ge-manual-geometry.md) working copy with the four nut seats split at Ø 14.173 by [M2A.4](ge-manual-boundary-conditions.md) |
| Tools | FreeCAD 1.1.3 FEM Workbench → `FemMeshGmsh` → Gmsh 4.15.2 (`vendor/fem-env/bin/gmsh`); quality from the Gmsh 4.15.2 Python API |
| Script | `vendor/fem-env/bin/python scripts/ge_manual_mesh.py` (about 1 min). It builds the same objects as the manual steps in section 1 and writes `out/ge_manual_mesh/mesh-quality.json` |
| Status | **Mesh and quality: done for Iteration1; on `GE_Challenge_Bracket` L1 is rejected** (one element, gamma 0.015) while L2, L3r and L3 pass. **Convergence: done for Ti LC1–LC4** (3 Oct) on L1 / L2 / L3r: displacement and arm-root stress converge within 3.0 % (section 6); the boss-ring peak at the 10 mm zone edge does not. **L2 is the frozen mesh** (3 Oct), recorded in `scripts/ge_part.py` |

## 1. Manual steps (FreeCAD 1.1.3 GUI)

1. **Set Gmsh to one thread.** Edit → Preferences → FEM → Gmsh, and set the number of threads to **1**. With the
   default (all cores), the same input gave 321,322 nodes on one run and 321,501 on the next. The script sets this
   preference only for its own run and then restores it.
2. **Open the geometry.** Open `data/ge_manual/Iteration1_partitioned.FCStd` and switch to the **FEM** workbench.
   `Bracket` is already in the SimJEB deck frame (+z up, out = −x).
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
   Picking 65 faces by hand is error-prone, so this Python console form sets the same references:
   ```python
   doc = App.ActiveDocument; b = doc.Bracket
   doc.MeshRegion.References = [(b, ("Face35", "Face36", ...))]   # paste a list from below
   ```

   | Region | What it covers | Faces |
   | --- | --- | --- |
   | `pin_bore` (12) | Both lug bores (r 9.557) and their 8 chamfer cones | Face35–Face46 |
   | `arm_root` (65) | Curved blend faces where the clevis arms meet the body (centroids y −97…−52, x −40…40, z 10…40, bores excluded) | Face48 49 50 78 80 87 88 89 90 91 96 102 103 133 165 166 175 179 192 193 194 196 197 199 219 220 221 222 224 225 239 240 245 246 247 249 250 251 252 253 255 257 258 259 260 261 263 265 267 269 270 271 272 273 274 275 280 284 288 289 290 291 321 322 327 |
   | `nut_seat` (24) | Bolt-hole walls, the four seat annuli (z = 7.849; each now a nut patch and a free ring) and the seat-recess toroids | Face1–Face16, Face27–Face34 |
   | `thin_section` (9) | Faces within 1 mm of M2A.1's thinnest wall samples (base end walls, about 4.66 mm) | Face25 69 70 119 120 140 143 146 148 |

   The script chooses these faces by geometric predicate (`select_regions`), not by stored index, and records
   the lists in `mesh-quality.json`. Face numbers are valid only for the working copy with the checksum above.
7. **Mesh.** Double-click `Mesh`, then click **Apply** in the task panel. Record the Gmsh output and the node and
   element counts it prints.
8. **Save.** Save the document under the level's name, `Iteration1_mesh_L1.FCStd`.
9. **Inspect and measure.** Look at the sections (section 5), then run the script to get the quality metrics.
   The FreeCAD GUI does not report signed Jacobian or scaled Jacobian.

## 2. Levels and settings

Only one level, L1, is meshed. Curvature is set explicitly: FreeCAD's default of 12 elements per 2π by itself puts
about 1 mm elements on all 151 of the r 2 mm fillets.

| Level | Max | Min | Region size | Curvature (elements per 2π) | Element size on r 2 fillets | Nodes | C3D10 | Gmsh time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 5.0 | 1.0 | 2.0 | 4 | about 3.1 | 155,203 | 90,353 | 14.9 s |

All sizes are in mm. Element counts by type, identical between the FreeCAD `FemMesh` and the `.unv`:

| Level | Line3 | Triangle6 | Tetrahedron10 |
| --- | --- | --- | --- |
| L1 | 5,158 | 34,194 | 90,353 |

**Why only L1.** The `ccx` in the FEM environment links **SPOOLES only**, a direct solver: PARDISO and PaStiX are
not linked (checked with `otool` and `strings`). The host is an Apple M2 with 16 GB of memory. L1 (about 0.47 M
degrees of freedom) solves in about 50 s. Two finer levels were also meshed: L2 (max 4.0, min 1.0, region 1.5,
curvature 6; 321,377 nodes) and L3 (max 3.0, min 0.75, region 1.0, curvature 9; 842,653 nodes). Both passed the
thresholds in section 3. On 2026-09-19 the M2A.4 smoke-test solve of L2 LC1 (about 0.97 M degrees of freedom)
**ran out of memory**, so L2 and L3 were dropped and their files deleted. `ge_manual_mesh.py` now defines L1 only.

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
cluster there. **The margin is thin by construction** (L1: 0.113).

Other metrics: an edge-ratio aspect ratio is reported instead of Gmsh's `eta`/`SICN`. Gmsh's `minSICN` and
`minIsotropy` exist but are not used.

### Results

| Metric | L1 |
| --- | --- |
| Inverted (`minDetJac` ≤ 0) / zero volume | 0 / 0 |
| `minSJ` min / p0.1 / p1 / p5 / median | 0.113 / 0.373 / 0.647 / 0.826 / 1.000 |
| `gamma` min / p0.1 / p1 / median | 0.079 / 0.314 / 0.455 / 0.790 |
| Fraction with `gamma` < 0.2 | 0.016 % |
| Aspect ratio median / p99.9 / max | 1.68 / 4.52 / 9.31 |
| **Accepted** | **yes** |

Worst elements, with element IDs as in the `.unv` and `FemMesh`, and centroids in the deck frame (mm):

| Level | Worst by `minSJ` | Worst by `gamma` |
| --- | --- | --- |
| L1 | #116953 0.113 at (44.3, −119.9, 28.7); #57913 0.114 at (−4.5, −39.6, 27.3) | #124214 0.079 at (−21.8, −126.6, 11.6), min edge 0.25 mm; #124192 0.106 at (−20.0, −29.9, 13.0) |

**The worst gamma** is near (−21.8, −126.6, 11.6), with a twin near
(−20.0, −29.9, 13.0). These are clusters of tiny B-spline faces in the source CAD: Face134–137 and Face282–283,
0.3–1.4 mm² each, on the −x side walls of the base. The worst elements there have edges of 0.19–0.25 mm;
the mesh cannot be coarser than those faces. They are geometry artifacts, not stress features, and they sit away from the pin, the seats
and the arm roots.

**Gmsh log.** Gmsh gives two warnings: "Surface mesh: worst distortion = −1.53 (2 elements with jac. < 0)" and
"Volume mesh: worst distortion = −1.35 (85 elements with jac. < 0)". These counts come from the straight-sided
mesh **before** high-order optimisation. The final mesh has zero elements with `minDetJac` ≤ 0.

## 4. How the accepted settings were reached

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

Trials with `SecondOrderLinear` (straight midside nodes) were not needed: no accepted curved mesh has an inverted
element. Geometry repair (defeaturing the tiny faces) was not needed either, and would have changed the frozen
geometry.

## 5. Repeatability, files and sections

**Repeatability** (checked on the unpartitioned copy, before M2A.4). Single-threaded Gmsh reproduces node and element counts, connectivity and every quality number
exactly. Node coordinates vary by up to 1×10⁻⁵ mm between runs, from the optimisers' floating-point order. The
`.unv` and FCStd bytes, and so their SHA-256, therefore do **not** repeat. The mesh identity is the level settings
plus the **connectivity SHA-256** (tet10 node lists in `.unv` order) and the node/element counts. The `.geo` and
`.brep` inputs do repeat byte for byte.

| Level | Connectivity SHA-256 | `shape2mesh.geo` SHA-256 |
| --- | --- | --- |
| L1 | `342e0de4406fb646df3ae22e589d470e601b036a9da57237bacf63b372280b83` | `7f7b6794ea333ea4b46f4be6eedf172c5bd83b2dc349b71064d6cbd737cbb740` |

Full checksums of every file are in `out/ge_manual_mesh/mesh-quality.json`. The files are gitignored, because they
are derived from GrabCAD non-commercial CAD:

- `data/ge_manual/mesh/L1/Iteration1_mesh_L1.FCStd`: Analysis, Mesh and four MeshRegions, ready for
  M2A.3–M2A.5 to add material, supports and loads;
- `Bracket_Mesh.unv`, `shape2mesh.geo` and `Bracket_Geometry.brep` alongside it.

**Section and quality views** are in `out/ge_manual_mesh/L1/`:

- `quality_histograms.png`: `minSJ`, `gamma` and aspect ratio, log-scale counts, threshold lines;
- `worst_elements.png`: the 10 worst elements by `minSJ`, with IDs;
- `section_lug_bore.png`: y = −60.48, through the lug and the bore;
- `section_arm_root.png`: x = −12, through both arm roots;
- `section_bolt_B2_B1.png`: y = 0, through bolts B2 and B1 and their seats;
- `section_thin_wall_z21.png`: z = 21, through the thin base end walls.

The sections use crinkle clipping, so they show whole elements, coloured by `minSJ`. They show
graded refinement at the bore, the arm-root blends and the seats. At L1 the z = 21 slice shows about 2–3 elements
across the internal ribs. The through-thickness element count at the 4.66 mm end walls was not measured; check it
in the GUI walk-through.

## 6. Convergence study (Ti-6Al-4V, LC1–LC4, on `GE_Challenge_Bracket`)

Tolerances are the ones fixed before comparison: max displacement changes ≤ 2 %; stress outside the singularity
zones changes ≤ 5 %; reactions balance the applied load within 0.5 %; a raw peak that moves more than 20 % is
flagged, never hidden. The comparison that is judged is the two finest levels, L2 → L3r.

**Levels.** L2 and L3 are back in `ge_manual_mesh.py` (not meshed by default). A global L3 (415,584 nodes, about
1.25M DOF) passes quality but would need about 13 GB for SPOOLES, which a 16 GB host doesn't have. So the third
level is **L3r**: L2's global sizes, with only the `arm_root` region refined to L3's 1.0 mm and the global minimum
at 0.75 mm.

| Level | max / min / region / curvature | Nodes | C3D10 | `minSJ` min | gamma min | Aspect max | Quality | Connectivity SHA-256 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 5 / 1.0 / 2.0 / 4 | 93,659 | 57,835 | 0.158 | **0.015** | 8.58 | **rejected** (element 72558) | `5e6a3c41…ee71cf6` |
| L2 | 4 / 1.0 / 1.5 / 6 | 172,710 | 109,287 | 0.217 | 0.202 | 6.73 | accepted | `ad92e201…2916922` |
| L3r | 4 / 0.75 / 1.5 (arm_root 1.0) / 6 | 230,557 | 148,446 | 0.220 | 0.182 | 6.73 | accepted | `cf1f3fd4…7947374e` |
| L3 (not solved) | 3 / 0.75 / 1.0 / 9 | 415,584 | 271,698 | 0.489 | 0.202 | 3.73 | accepted | `a755cd96…15285fa9` |

Every level has zero inverted and zero zero-volume elements. Full distributions, worst-element IDs and file
checksums are in `out/ge_manual_mesh/mesh-quality.json`; histograms and sections are in `out/ge_manual_mesh/<level>/`.

**Where the runs were made.** The meshes are the same files throughout (L1 by Gmsh 4.15.2 on the D-17 Mac; L2, L3r
and L3 by Gmsh 4.15.0 on the Windows host). The solves are split across two hosts, both SPOOLES:

| Runs | Host | ccx | SPOOLES peak memory | Wall per solve |
| --- | --- | --- | --- | --- |
| L1, LC1–LC4 | Mac (D-17) | 2.23 | 2.1 GB (measured on Windows) | about 40 s |
| L2 and L3r, LC1 | Windows | 2.22 | 4.5 GB / 6.3 GB | 380 s / 642 s |
| L2, LC2–LC4 (3 Oct) | Mac (D-17) | 2.23 | 5.1 GB | 324–365 s |
| L3r, LC2–LC4 (3 Oct) | Mac (D-17) | 2.23 | 6.9 GB | 696–912 s |

So each L2 → L3r pair is solved on one host with one ccx version; only the LC1 pair differs from the LC2–LC4 pairs.
`ITERATIVE CHOLESKY` fits in memory but its fixed stopping tolerance leaves displacement 2.2 % and nodal stress up
to 25 MPa off SPOOLES on L1, so it is not used here. PaStiX and PARDISO are not linked in either ccx.

**How each quantity is read.** Von Mises is the matrix's nodal-averaged stress. The arm-root values are the
maximum over the mesh nodes lying on that fillet face (Face35 is the +y lug's arm-root fillet, Face34 the −y
lug's). "Outside the 10 mm zone" is the M2A.6 screening peak: outside the pin exclusion and 10 mm from every bolt
axis.

**Maximum displacement (mm)**

| Case | L1 | L2 | L3r | L2 → L3r | ≤ 2 % |
| --- | --- | --- | --- | --- | --- |
| LC1 | 0.2278 | 0.2287 | 0.2287 | 0.0 % | ✅ |
| LC2 | 0.1731 | 0.1738 | 0.1737 | −0.1 % | ✅ |
| LC3 | 0.0918 | 0.0921 | 0.0921 | 0.0 % | ✅ |
| LC4 | 0.0387 | 0.0388 | 0.0388 | 0.0 % | ✅ |

**Arm-root fillets, away from every constraint singularity (MPa)**

| Case | Face | L1 | L2 | L3r | L1 → L2 | L2 → L3r | ≤ 5 % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LC1 | +y (Face35) | 244.0 | 262.9 | **258.5** | +7.7 % | −1.7 % | ✅ |
| LC1 | −y (Face34) | 242.7 | 253.8 | 255.4 | +4.6 % | +0.6 % | ✅ |
| LC2 | +y | 122.4 | 124.8 | 128.2 | +2.0 % | +2.7 % | ✅ |
| LC2 | −y | 127.0 | 133.8 | **135.4** | +5.4 % | +1.2 % | ✅ |
| LC3 | +y | 197.5 | 208.9 | 215.2 | +5.8 % | +3.0 % | ✅ |
| LC3 | −y | 217.6 | 238.1 | **235.5** | +9.4 % | −1.1 % | ✅ |
| LC4 | +y | 145.4 | 153.2 | **153.3** | +5.4 % | +0.1 % | ✅ |
| LC4 | −y | 151.2 | 153.9 | 153.0 | +1.8 % | −0.6 % | ✅ |

Node spacing at the arm root is 0.99 / 0.65 / 0.32 mm at L1 / L2 / L3r. (The LC1 −y value at L3r was first
recorded as 254.5; re-extracted on 3 Oct it is 255.4.)

**Peak outside the 10 mm bolt zone (MPa)**

| Case | L1 | L2 | L3r | L1 → L2 | L2 → L3r | Where | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LC1 | 336.5 | 417.9 | 421.2 | **+24 %** | (+0.8 %) | boss ring at B2, r 10.34 → 10.06 → 10.06 | **not converged, not tested by L3r** |
| LC2 | 209.8 | 256.0 | 257.6 | **+22 %** | (+0.6 %) | boss ring; moves from B1 (r 10.34) to B2 (r 10.06) | **not converged, not tested by L3r** |
| LC3 | 217.6 | 238.1 | 235.5 | +9.4 % | −1.1 % | −y arm root | converged |
| LC4 | 151.2 | 153.9 | 153.3 | +1.8 % | −0.4 % | arm root | converged |

**Raw peaks (MPa), reported and never used**

| Case | L1 | L2 | L3r | L2 → L3r | Where |
| --- | --- | --- | --- | --- | --- |
| LC1 | 1,521.8 | 1,216.4 | 1,269.4 | +4.4 % | fixed-patch edge |
| LC2 | 1,030.9 | 971.4 | 943.5 | −2.9 % | fixed-patch edge |
| LC3 | 922.4 | 638.9 | 827.3 | **+29 %, flagged** | fixed-patch edge; jumps from B4 (L2) to B2 (L3r) |
| LC4 | 373.1 | 389.9 | 396.3 | +1.6 % | pin exclusion (rigid-bore boundary) |

**Reactions.** All 12 runs are solver-valid, and every support force and moment residual rounds to 0.00 % of the
applied load (tolerance 0.5 %).

**What this settles and what it doesn't**
- **Displacement is converged in all four cases**, to 0.1 % or better between L2 and L3r.
- **The arm-root fillets are converged in all four cases**: the largest L2 → L3r change is 3.0 % (LC3, +y). The
  real governing stress is about **259 MPa in LC1**, then 236 (LC3), 153 (LC4) and 135 MPa (LC2).
- **L1 is not converged**, as well as failing quality: it reads the arm root up to 9.4 % low (LC3, −y).
- **The boss ring just outside the 10 mm bolt zone is not a converged stress in LC1 or LC2.** It rises 22–24 % from
  L1 to L2 and sits on the zone edge (r 10.06), which is how the tail of the fixed-patch-edge singularity behaves.
  L3r left that area at L2 size, so its +0.6–0.8 % says nothing either way. With an 11 mm zone the LC1 peak is the
  arm root; in LC2 it is still a zone-edge node (141.9 MPa at r 11.09), and only at 12 mm is it the arm root. The
  radius is the [#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64) question; a level
  refining `nut_seat` would test the ring directly.
- **The raw fixed-patch-edge peaks do not converge** (LC3 moves +29 % between the two finest levels), as expected
  of a singularity. They stay flagged.
- **L2 is the frozen mesh (owner decision, 3 Oct).** L1 is out. L2 passes quality, is within 3.0 % of L3r at every
  arm root and within 0.1 % on displacement in all four cases, and solves in about 6 min and 5.1 GB, so the 20-run
  matrix fits on the 16 GB host.
  - **Record:** `scripts/ge_part.py` holds the level and its connectivity SHA-256, `ad92e201…2916922`.
  - **Guards:** `ge_manual_matrix.py` runs on L2 by default and stops if the mesh document or its quality record
    is not the frozen one; `ge_manual_mesh.py` will not re-mesh L2 without `--refreeze`.
  - **M2A.4, M2A.5 and M2A.6 are re-run on L2** ([boundary conditions](ge-manual-boundary-conditions.md),
    [load cases](ge-manual-load-cases.md), [analysis report](ge-manual-analysis-report.md)); their scripts
    default to the frozen level.

## 7. Status against the M2A.2 checklist

| Step | Status |
| --- | --- |
| 1. Working copy, Analysis, Gmsh mesh, C3D10 | Done (section 1) |
| 2. All settings recorded; start from M2 evidence; local MeshRegions at arm roots, bores, nut seats and thin sections | Done (sections 1, 2 and 4) |
| 3. Generate; inspect sections; mesher version; counts by type; time; files and checksums | Done (sections 2, 3 and 5). **The GUI walk-through still needs one manual run** to confirm the steps as written; the numbers above come from the script |
| 4. Named metrics, distributions, worst IDs and locations, histograms, worst-element views; unavailable metrics stated | Done (section 3) |
| 5. Zero inverted; thresholds fixed before acceptance; failures corrected by sizing | Done (sections 3 and 4). The curved-midside trial was not needed |
| 6. Three levels × LC1–LC4 convergence; freeze | **Convergence done for Ti LC1–LC4** on L1 / L2 / L3r (section 6): displacement and arm-root stress meet the tolerances; the boss-ring peak at the 10 mm zone edge and the raw peaks do not converge and are flagged. **Frozen on L2** (3 Oct) |

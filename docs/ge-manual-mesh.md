# GE manual mesh — procedure, quality and convergence (M2A.2)

| | |
| --- | --- |
| Task | M2A.2 ([#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19 |
| Input | Working copy `data/ge_manual/Iteration1_manual.FCStd`, SHA-256 `fcc77c98…96c8b` ([M2A.1 record](ge-manual-geometry.md)) |
| Tools | FreeCAD 1.1.3 FEM Workbench → `FemMeshGmsh` → Gmsh 4.15.2 (`vendor/fem-env/bin/gmsh`); quality from the Gmsh 4.15.2 Python API |
| Script | `vendor/fem-env/bin/python scripts/ge_manual_mesh.py [--levels L1 L2 L3]` (about 3 min). It builds the same objects as the manual steps in section 1 and writes `out/ge_manual_mesh/mesh-quality.json` |
| Status | **Mesh and quality: done.** All three levels pass the acceptance thresholds. **Convergence: pending** (needs the M2A.3–M2A.5 material, supports and loads). **No mesh is frozen yet**; L2 is the provisional candidate |

## 1. Manual steps (FreeCAD 1.1.3 GUI)

1. **Set Gmsh to one thread.** Edit → Preferences → FEM → Gmsh, and set the number of threads to **1**. With the
   default (all cores), the same input gave 321,322 nodes on one run and 321,501 on the next. The script sets this
   preference only for its own run and then restores it.
2. **Open the geometry.** Open `data/ge_manual/Iteration1_manual.FCStd` and switch to the **FEM** workbench.
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
   doc.MeshRegion.References = [(b, ("Face31", "Face32", ...))]   # paste a list from below
   ```

   | Region | What it covers | Faces |
   | --- | --- | --- |
   | `pin_bore` (12) | Both lug bores (r 9.557) and their 8 chamfer cones | Face31–Face42 |
   | `arm_root` (65) | Curved blend faces where the clevis arms meet the body (centroids y −97…−52, x −40…40, z 10…40, bores excluded) | Face44 45 46 74 76 83 84 85 86 87 92 98 99 129 161 162 171 175 188 189 190 192 193 195 215 216 217 218 220 221 235 236 241 242 243 245 246 247 248 249 251 253 254 255 256 257 259 261 263 265 266 267 268 269 270 271 276 280 284 285 286 287 317 318 323 |
   | `nut_seat` (20) | Bolt-hole walls, the four seat annuli (z = 7.849) and the seat-recess toroids | Face1–Face12, Face23–Face30 |
   | `thin_section` (9) | Faces within 1 mm of M2A.1's thinnest wall samples (base end walls, about 4.66 mm) | Face21 65 66 115 116 136 139 142 144 |

   The script chooses these faces by geometric predicate (`select_regions`), not by stored index, and records
   the lists in `mesh-quality.json`. Face numbers are valid only for the working copy with the checksum above.
7. **Mesh.** Double-click `Mesh`, then click **Apply** in the task panel. Record the Gmsh output and the node and
   element counts it prints.
8. **Save.** Save the document under the level's name, for example `Iteration1_mesh_L2.FCStd`.
9. **Inspect and measure.** Look at the sections (section 5), then run the script to get the quality metrics.
   The FreeCAD GUI does not report signed Jacobian or scaled Jacobian.

## 2. Levels and settings

Every size is refined from L1 to L3. Curvature is a level parameter as well: FreeCAD's default of 12 elements per
2π by itself puts about 1 mm elements on all 151 of the r 2 mm fillets.

| Level | Max | Min | Region size | Curvature (elements per 2π) | Element size on r 2 fillets | Nodes | C3D10 | Gmsh time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 5.0 | 1.0 | 2.0 | 4 | about 3.1 | 154,683 | 90,058 | 15.9 s |
| **L2** | 4.0 | 1.0 | 1.5 | 6 | about 2.1 | 321,377 | 195,035 | 16.4 s |
| L3 | 3.0 | 0.75 | 1.0 | 9 | about 1.4 | 842,653 | 536,044 | 45.5 s |

All sizes are in mm. Element counts by type, identical between the FreeCAD `FemMesh` and the `.unv`:

| Level | Line3 | Triangle6 | Tetrahedron10 |
| --- | --- | --- | --- |
| L1 | 5,066 | 34,080 | 90,058 |
| L2 | 6,784 | 60,390 | 195,035 |
| L3 | 9,839 | 125,676 | 536,044 |

**Upper limit.** L3 is capped near 0.85 M nodes, about 2.5 M degrees of freedom. The `ccx` in the FEM environment
links **SPOOLES only**: PARDISO and PaStiX are not linked (checked with `otool` and `strings`). The host is an
Apple M2 with 16 GB of memory. The first attempt used FreeCAD's default curvature of 12 at max 4 mm and gave
982,363 nodes at the coarsest level. Whether L3 actually solves in 16 GB is checked in the convergence step. If it
does not, record that and use the iterative solver.

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
cluster there. **The margin is thin by construction** (L2: 0.1016).

Other metrics: an edge-ratio aspect ratio is reported instead of Gmsh's `eta`/`SICN`. Gmsh's `minSICN` and
`minIsotropy` exist but are not used.

### Results

| Metric | L1 | L2 | L3 |
| --- | --- | --- | --- |
| Inverted (`minDetJac` ≤ 0) / zero volume | 0 / 0 | 0 / 0 | 0 / 0 |
| `minSJ` min / p0.1 / p1 / p5 / median | 0.113 / 0.375 / 0.653 / 0.830 / 1.000 | 0.102 / 0.373 / 0.677 / 0.871 / 1.000 | 0.127 / 0.568 / 0.771 / 0.940 / 1.000 |
| `gamma` min / p0.1 / p1 / median | 0.078 / 0.314 / 0.455 / 0.790 | 0.130 / 0.407 / 0.522 / 0.824 | 0.111 / 0.452 / 0.549 / 0.851 |
| Fraction with `gamma` < 0.2 | 0.016 % | 0.004 % | 0.0004 % |
| Aspect ratio median / p99.9 / max | 1.68 / 4.64 / 9.29 | 1.59 / 3.19 / 6.72 | 1.52 / 2.73 / 6.46 |
| **Accepted** | **yes** | **yes** | **yes** |

Worst elements, with element IDs as in the `.unv` and `FemMesh`, and centroids in the deck frame (mm):

| Level | Worst by `minSJ` | Worst by `gamma` |
| --- | --- | --- |
| L1 | #116523 0.113 at (44.3, −119.9, 28.7); #40659 0.123 at (−4.5, −39.6, 27.3) | #115607 0.078 at (−21.9, −126.3, 12.2), min edge 0.09 mm |
| L2 | #217447 0.102 at (−3.7, −127.3, 18.1); #202795 0.123 at (−18.6, −26.2, 21.0) | #259944 0.130 at (−21.9, −126.3, 12.2), min edge 0.10 mm |
| L3 | #165582 0.127 at (43.3, −124.9, 0.3); #305304 0.186 at (50.4, −124.8, 0.3) | #584494 0.111 at (−21.9, −126.3, 12.2), min edge 0.10 mm |

**The worst gamma is at the same place at every level**, near (−21.9, −126.3, 12.2), with a twin near
(−24.9, −30.6, 11.9). These are clusters of tiny B-spline faces in the source CAD: Face130–133 and Face278–279,
0.3–1.4 mm² each, with edges down to 0.09 mm, on the −x side walls of the base. The mesh cannot be coarser than
those edges there. They are geometry artifacts, not stress features, and they sit away from the pin, the seats
and the arm roots.

**Gmsh log.** Gmsh warns, for example "Volume mesh: worst distortion = −1.35 (87 elements with jac. < 0)" at L1.
These counts come from the straight-sided mesh **before** high-order optimisation. The final meshes have zero
elements with `minDetJac` ≤ 0. L1 also reports "1 ill-shaped tets are still in the mesh"; that element passes the
thresholds above (L1 gamma minimum 0.078). L3's log has no warnings.

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

Trials with `SecondOrderLinear` (straight midside nodes) were not needed: no accepted curved mesh has an inverted
element. Geometry repair (defeaturing the tiny faces) was not needed either, and would have changed the frozen
geometry.

## 5. Repeatability, files and sections

**Repeatability.** Single-threaded Gmsh reproduces node and element counts, connectivity and every quality number
exactly. Node coordinates vary by up to 1×10⁻⁵ mm between runs, from the optimisers' floating-point order. The
`.unv` and FCStd bytes, and so their SHA-256, therefore do **not** repeat. The mesh identity is the level settings
plus the **connectivity SHA-256** (tet10 node lists in `.unv` order) and the node/element counts. The `.geo` and
`.brep` inputs do repeat byte for byte.

| Level | Connectivity SHA-256 | `shape2mesh.geo` SHA-256 |
| --- | --- | --- |
| L1 | `f97466559fd0e67e400afdc94e71670722bd2d12e0ad8064c4db53d187a992d9` | `3e198fcecff947910840d7eb79b272c26cdc2f8701f2927eb39490ced12aeafa` |
| L2 | `805b99be38b1e3c89f9bdd9051d3aecb2acccfcd01432232c40fda16d140eb0b` | `a6942477480e4cefa66833c089dca655e2838692e62f0232841c47d30f0eb9d5` |
| L3 | `7448398cf4fd75c3c535ec0b48d4ed0665aed87e0958add3fe84ce4d3e853b24` | `54ff26ba628131aa02d59abda37eaa4f6c7087d81776dd48e14035a28b95bc55` |

Full checksums of every file are in `out/ge_manual_mesh/mesh-quality.json`. The files are gitignored, because they
are derived from GrabCAD non-commercial CAD:

- `data/ge_manual/mesh/<level>/Iteration1_mesh_<level>.FCStd`: Analysis, Mesh and four MeshRegions, ready for
  M2A.3–M2A.5 to add material, supports and loads;
- `Bracket_Mesh.unv`, `shape2mesh.geo` and `Bracket_Geometry.brep` alongside it.

**Section and quality views** are in `out/ge_manual_mesh/<level>/`:

- `quality_histograms.png`: `minSJ`, `gamma` and aspect ratio, log-scale counts, threshold lines;
- `worst_elements.png`: the 10 worst elements by `minSJ`, with IDs;
- `section_lug_bore.png`: y = −60.48, through the lug and the bore;
- `section_arm_root.png`: x = −12, through both arm roots;
- `section_bolt_B2_B1.png`: y = 0, through bolts B2 and B1 and their seats;
- `section_thin_wall_z21.png`: z = 21, through the thin base end walls.

The sections use crinkle clipping, so they show whole elements, coloured by `minSJ`. At every level they show
graded refinement at the bore, the arm-root blends and the seats. At L1 the z = 21 slice shows about 2–3 elements
across the internal ribs. The through-thickness element count at the 4.66 mm end walls was not measured; check it
in the GUI walk-through.

## 6. Convergence study (pending M2A.3–M2A.5)

Step 6 of the task needs Ti-6Al-4V ([M2A.3](ge-manual-workflow.md)), the nut-seat supports and rigid-pin load
transfer (M2A.4), and LC1–LC4 (M2A.5). None of these exist yet. The tolerances are fixed **now**, before any
comparison:

| Quantity | Measured on L1, L2 and L3 for each of LC1–LC4 | Converged when (L2 → L3) |
| --- | --- | --- |
| Max displacement magnitude | Whole part | Change ≤ 2 % |
| Reaction force and moment | Summed over the four seats about the pin reference point | Balance the applied load to ≤ 0.5 % at every level |
| Peak von Mises **away from singularities** | Outside the exclusion zones defined in M2A.4 (at minimum, the idealised seat-patch edges and the rigid pin–bore boundary; M2's LC1 used a 10 mm plan radius about each bolt axis) | Change ≤ 5 % |
| Raw peak von Mises | Everywhere | Reported, never hidden. A change > 20 % marks a **non-convergent peak**, flagged with its location (the same threshold as D-12) |

If L2 meets these criteria against L3 for all four cases, **freeze L2**: record its connectivity SHA-256 and the
FCStd used. Otherwise freeze L3, if it solves in 16 GB, and record the solver used. Update this section with the
table of results.

## 7. Status against the M2A.2 checklist

| Step | Status |
| --- | --- |
| 1. Working copy, Analysis, Gmsh mesh, C3D10 | Done (section 1) |
| 2. All settings recorded; start from M2 evidence; local MeshRegions at arm roots, bores, nut seats and thin sections | Done (sections 1, 2 and 4) |
| 3. Generate; inspect sections; mesher version; counts by type; time; files and checksums | Done (sections 2, 3 and 5). **The GUI walk-through still needs one manual run** to confirm the steps as written; the numbers above come from the script |
| 4. Named metrics, distributions, worst IDs and locations, histograms, worst-element views; unavailable metrics stated | Done (section 3) |
| 5. Zero inverted; thresholds fixed before acceptance; failures corrected by sizing | Done (sections 3 and 4). The curved-midside trial was not needed |
| 6. Three levels × LC1–LC4 convergence; freeze | **Pending M2A.3–M2A.5** (tolerances fixed in section 6) |

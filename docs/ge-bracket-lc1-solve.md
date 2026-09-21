# ge_bracket LC1 — the ccxtools solve, parsed and measured (M2.5)

| | |
| --- | --- |
| Task | M2.5 ([#48](https://github.com/sujitojha1/3d-part-optimization-agent/issues/48)) · [plan](plan.md) step 5 |
| Date | 2026-09-21 |
| Part | The parametric `ge_bracket` ([frozen record](ge-bracket-part.md)) at every baseline parameter, full model |
| Load case | LC1, the [frozen record](ge-bracket-lc1.md): `(0, 0, +35,585.77) N`, rigid pin, four fixed bolt holes, Ti-6Al-4V, allowable 602.1 MPa |
| Mesh | D-24 as frozen in [M2.3](ge-bracket-mesh.md): max 4.0 / min 1.0 / MeshRegion 1.5 / curvature 8, `OptimizeNetgen` on |
| Labels | M2.4's [element-centroid fallback](ge-bracket-labels.md), because no D-06 label reaches the deck |
| Script | `scripts/lc1_solve.py` (about 1 min 51 s), writing `out/lc1_solve/result.json` |
| Status | **Solved and parsed.** The baseline passes at **1.35×**. Two things M2.5 was meant to settle came out against the current record: the D-24 MeshRegion at 1.5 **trips the 60 s cut trigger**, and the raw peak's region label is **ambiguous** where the governing peak's is not. Neither is a reason to take the `L_bracket` fallback — section 6 |

**Measured outside D-17.** Every number here was produced on **Windows-AMD64 with FreeCAD 1.1.3,
Gmsh 4.15.0 and ccx 2.22**, not the `vendor/fem-env` macOS arm64 environment D-17 pins (FreeCAD
1.1.3, Gmsh 4.15.2, CalculiX 2.23). The divergence is recorded in every `result.json` under
`environment`, and section 7 says which conclusions it can and cannot touch. **The timings are
provisional until re-measured on the D-17 machine**; the stresses, mass and labels are not
platform-sensitive in any way this run can detect, and the one direct cross-check available —
section 7 — agrees with the Mac to 7 %.

## 1. What M2.5 asked for, and what it returned

The issue asks for four quantities and a wall time. All five, at the D-24 mesh:

| Quantity | Value | Where |
| --- | --- | --- |
| Full-part mass | **1,198.77 g** | CAD solid volume 270,602.161 mm³ × 4.43e-3 g/mm³ |
| Max von Mises, outside the support zone | **445.8 MPa** | node 31469 at (−13.63, −136.62, 0.75), `base_plate` |
| Max von Mises, raw | **630.6 MPa** | node 1238 at (−4.15, −144.78, 0.00), **label ambiguous** — section 4 |
| Max displacement | **0.4516 mm** | node 971 at (−50.56, −73.18, 0.00) |
| Peak element → region | **`base_plate`**, unambiguous | both elements holding node 31469 carry it |
| Wall time, mesh + solve | **92.13 s** | 12.02 s Gmsh + 80.11 s ccx, full model |
| Wall time, CAD → parsed result | **111.23 s** | + 0.84 CAD, 6.17 write_inp, 10.65 load_results, 2.30 labels |

The stress check reads the peak **outside** the support zone, as `ge_bracket_lc1.json`'s
`stress_check` fixes it: **445.8 against 602.1 MPa is 1.35×**, and the part passes. The raw peak is
reported and flagged, never dropped.

**Mass is a CAD number, not a mesh number.** The meshed volume (straight-edge tet10 sum) is
270,995.769 mm³, +0.145 % on the CAD volume, which is the discretisation check, not a second
measurement. The 1,198.77 g agrees with the 1,199 g recorded in [M2.2](ge-bracket-lc1.md) when the
bosses went flush.

## 2. Against M2.2's hand calculation

The comparison is against [section 2 of the LC1 record](ge-bracket-lc1.md#2-hand-calculation-before-the-solve),
written before any solve and frozen in `scripts/lc1_solve.py` as `HAND` so it cannot drift.

| Quantity | Hand | FE (D-24 mesh) | Reading |
| --- | --- | --- | --- |
| Bolt 2 | −10.4 kN (prying) | −3.5 kN | Sign agrees, magnitude does not |
| Bolt 3 | +28.2 kN | +20.9 kN | Sign agrees |
| Bolt 4 | +23.2 kN | +21.2 kN | Sign agrees |
| Bolt 5 | −5.3 kN (prying) | −3.0 kN | Sign agrees |
| Governing von Mises | 174 MPa | **445.8 MPa** | **2.56× disagreement** |
| Peak region | `base_plate` | `base_plate` | Agrees |
| Arm-root fillet | 115 MPa (76 × Kt 1.5) | 261.5 MPa | 2.3× |
| Pin bore | 117 MPa (bearing) | 277.4 MPa | 2.4×; and not converged — section 5 |

**The disagreement is information.** All four prying signs come out as predicted, and the peak lands
in the region the hand calculation named, so the load path is understood. The 2.56× on the governing
stress is the same error M2.2 already diagnosed on the coarse mesh: the hand calculation spread the
bending over the full 104–107 mm outline, and the load actually runs through a strip about 45 mm
wide from the arm foot to bolt 4. That was a 2.7× miss at 457.8 MPa; refining to the D-24 mesh moves
it to 2.56× at 445.8 MPa. **Refinement did not rescue the hand calculation, and was never going to:
the section width was the wrong assumption, not the mesh.**

Reaction balance holds exactly: total `(0, 0, −35,585.77) N`, 0.0000° off the load axis and
0.0000 % in magnitude, against the 0.1° / 0.5 % tolerances REQ-VER-006 needs. The rigid pin model
writes the whole vector as one `*CLOAD` on the reference node, so there is no area-weighting loss —
the 0.118 % the rejected `half_bore` model carried.

## 3. Against M2.2's own solve

Same part, same load case, same pin model; M2.2 ran a provisional 4 mm mesh with no `MeshRegion`,
M2.5 runs the accepted D-24 mesh.

| Quantity | M2.2 (provisional, ~67k nodes) | M2.5 (D-24, 102,169 nodes) | Change |
| --- | --- | --- | --- |
| Peak outside the zone | 457.8 MPa at (−13.43, −136.79, 0.00) | 445.8 MPa at (−13.63, −136.62, 0.75) | −2.6 %, same site |
| Raw peak | 781 MPa, bolt 3 hole edge | 630.6 MPa, bolt 4 hole edge | −19 %, different hole |
| Arm-root fillet | 255.7 MPa | 261.5 MPa | +2.3 % |
| Max displacement | 0.4506 mm | 0.4516 mm | +0.2 % |
| Mass | 1,199 g | 1,198.77 g | — |

The governing stress and the displacement are stable; the raw peak is not, which is section 4.
**The D-24 sizes were provisional pending this solve ([M2.3](ge-bracket-mesh.md) section 2). They
have now been solved on, and they hold for the answer — but not for the clock, section 6.**

## 4. The raw peak's label is ambiguous. The governing peak's is not.

M2.4 established that no D-06 label reaches the ccxtools deck, so the label comes from the
element-centroid partition. On this mesh that partition is **exhaustive, disjoint and non-empty in
every region**: all 62,726 C3D10 elements labelled, `base_plate` 33,090, `arm_root_fillet` 14,161,
`clevis_arm` 11,234, `pin_bore` 2,645, `bolt_boss` 1,596.

A peak is reported at a *node*, and a node is shared by several elements. M2.5 therefore reports the
label of **every element holding the peak node**, and whether they agree:

| Peak | Node | Elements holding it | Labels | Unambiguous |
| --- | --- | --- | --- | --- |
| Outside the support zone, 445.8 MPa | 31469 | 2 | `base_plate` | **yes** |
| Raw, 630.6 MPa | 1238 | 2 | `base_plate`, `bolt_boss` | **no** |

**The raw peak sits exactly on the boundary between two D-06 regions**, which is the boss/plate
seam at the bolt-hole edge — the singular feature itself. It cannot be given one label, so
`REQ-OPT-002`, which requires the identified concentration to be recorded as *one* region label
from D-06, **cannot be satisfied from the raw peak on this part**. It is satisfied from the peak
outside the support zone, which lands cleanly inside `base_plate`.

This is a second, independent argument for the exclusion-zone rule that
[LC1 section 4](ge-bracket-lc1.md#4-the-bolt-hole-supports-are-singular) already argued on physical
grounds. The first argument was that the raw peak does not converge; this one is that it cannot be
labelled. **Both still need the owner confirmation section 4 of that record asked for**, and the
raw-versus-exclusion question stays open for `REQ-VER-002` and D-12.

**One honest qualification.** M2.2 saw the raw peak move 778 → 709 MPa between its 4 mm and 2.5 mm
meshes. Across M2.5's own four meshes it barely moves — 618.1, 629.0, 629.8, 630.6 MPa,
non-monotonically, always at the same node. Stability across these four is **not** convergence: they
share the same 1.0 mm minimum element size at the hole edge, which is what sets the singular value.
The label ambiguity does not depend on convergence and stands on its own.

## 5. Per region, from the disjoint partition

Each region's value is the highest nodal von Mises on any element the partition assigns to it — the
D-06 route, not M2.2's overlapping face-node sets.

| Region | Peak, MPa | At (mm) | Elements |
| --- | --- | --- | --- |
| `base_plate` | 630.6 | (−4.15, −144.78, 0.00) | 33,090 |
| `bolt_boss` | 630.6 | (−4.15, −144.78, 0.00) | 1,596 |
| `pin_bore` | 277.4 | (−18.81, −85.89, 35.54) | 2,645 |
| `clevis_arm` | 277.4 | (−18.81, −85.89, 35.54) | 11,234 |
| `arm_root_fillet` | 261.5 | (−20.99, −94.42, 20.75) | 14,161 |

Two pairs share a value because each pair's peak sits on the seam between them — the same
boundary effect as section 4, at the boss/plate seam and at the bore/arm seam. **A per-region ranking
read off the raw maxima is therefore not a partition of distinct sites**, and M3 should read region
values from element interiors, not from shared nodes, if it wants them to be independent.

**The governing peak is in the base plate, not the fillet**, which M2.2 already found and M2.5
confirms at the accepted mesh. The consequence M2.2 drew stands: an `arm_root_fillet` edit will not
move the governing peak on this part, and D-12's calibration on that fillet tests a region that is
not the peak.

## 6. The clock: the cut trigger fires, and the lever that clears it

The 21 Sep cut trigger asks whether `ge_bracket` meshes and solves by hand in ≤ 60 s. **At D-24's
MeshRegion of 1.5 it does not: 92.13 s.** D-23's half model is not available — the SimJEB bolt
pattern is not symmetric about the clevis midplane — so the next D-13 lever is the minimum element
size. Sweeping the one `MeshRegion` value, everything else at D-24:

| MeshRegion | Nodes | Gmsh | ccx | Mesh + solve | Peak outside zone | Arm-root fillet | Pin bore | Max disp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **1.5** (D-24) | 102,169 | 12.02 s | 80.11 s | **92.13 s** | 445.8 MPa | 261.5 | 277.4 | 0.4516 |
| **2.0** | 72,046 | 7.83 s | 40.80 s | **48.63 s** | 435.8 MPa | 259.3 | 232.6 | 0.4515 |
| 3.0 | 55,568 | 5.80 s | 24.24 s | 30.04 s | 438.3 MPa | 258.6 | 213.8 | 0.4513 |
| 4.0 (region off) | 46,857 | 4.94 s | 19.04 s | 23.98 s | 435.0 MPa | 236.9 | 189.9 | 0.4507 |

**MeshRegion 2.0 clears the trigger at 48.63 s and does not change the answer.** The governing peak
moves 2.2 % and stays in `base_plate` at the same node; the arm-root fillet moves 0.8 %; the
displacement moves 0.02 %. **The proposal is to move D-24's MeshRegion from 1.5 to 2.0. That is a
D-24 change and an owner decision, so it is recorded here and not applied.**

Two things the sweep says that the single number does not:

- **The base mesh, not the region, sets the governing answer.** The `MeshRegion` refines the fillet
  and the bore; the governing peak is in the base plate, which none of these four meshes refines. It
  reads 435–446 MPa across a 2.2× range of node count. Coarsening the *base* size would be a
  different and more dangerous lever, which is why D-13 puts it last.
- **`pin_bore` is not converged and is the reason not to go past 2.0.** It climbs 189.9 → 213.8 →
  232.6 → 277.4 MPa and is still rising at 1.5. It does not govern under LC1 — 277 against 446 — so
  it does not change this decision, but **any load case that makes the bore govern must re-open the
  mesh study**, and going to 3.0 would under-read it by 23 %.

**Do not take the `L_bracket` fallback.** The trigger fires on a setting with a measured, answer-
preserving alternative, not on the part. Against D-13's budget the simulation half of an evaluation
is 111.23 s at region 1.5, so 8 evaluations are 14.8 min of the 20 min budget — and at region 2.0,
8.3 min, which leaves room for the D-11 CAM jobs that M3.8 still has to time. **At 1.5 it does not
leave that room**, which is the budget argument for the same change the trigger argues for.

## 7. What the D-17 divergence can and cannot touch

The cross-check available is M2.3's own mesh, which the Mac recorded at **101,512 nodes / 62,228
C3D10 / 3.80 s** for `nominal_full`. This machine builds the same case at **102,169 / 62,726 /
12.02 s**: **+0.6 % on node count**, from Gmsh 4.15.0 against 4.15.2, and **3.2× on Gmsh wall time**.

| Conclusion | Touched by the platform? |
| --- | --- |
| Mass, 1,198.77 g | **No.** A CAD volume times a density; no solver, no mesh |
| Governing stress, 445.8 MPa, and its `base_plate` label | **No detectably.** A 0.6 % node-count difference against a quantity that moves 2.2 % over a 2.2× node-count range |
| Reaction balance to 0.0000° / 0.0000 % | **No.** An equilibrium identity |
| The raw peak's label ambiguity | **No.** A topological fact about where the seam falls, not a numeric one |
| **Every wall time, and so the cut-trigger decision** | **Yes.** Different CPU, different ccx (2.22 against 2.23), different Gmsh. Gmsh is 3.2× slower here, so the mesh column is the least trustworthy |

The timing conclusion survives the caveat in the direction that matters. This machine solves the
**coarse** mesh in 19.04 s against the Mac's 16.45 s on a comparable one — **16 % slower, not 5×** —
so the 92.13 s at region 1.5 is a mesh cost, not a machine cost, and the trigger would fire on the
Mac too. **Re-measure on the D-17 machine before the cut decision is closed**, but expect the same
answer.

## 8. What this does not establish

- **One load case, one parameter point.** LC1 at the baseline. Nothing about LC2–LC4, and nothing
  about any other point in the parameter space; `arm_root_fillet` at its minimum is meshed in M2.3
  but not solved here.
- **No convergence study.** Four meshes that share a minimum element size is a sensitivity sweep of
  one setting, not the three-level study M2A still owes. The `pin_bore` column is the proof: it has
  not converged, and this sweep cannot say where it lands.
- **The raw-versus-exclusion question is not closed.** M2.5 reports both and adds one argument.
  `REQ-VER-002` and D-12 still need the owner's decision, and D-12's singularity checks are
  preserved, not replaced, by the exclusion zone.
- **No contour, no reading.** M2.6 ([#49](https://github.com/sujitojha1/3d-part-optimization-agent/issues/49))
  renders the field and judges whether the regions are visually distinguishable. M2.5 only fixes
  what the right answer is.
- **No D-06 label in the deck.** Still the fallback, exactly as M2.4 left it: the deck's nine sets
  are `Eall`, the four `Fixed_*`, `MaterialSolid` and the three `Pin*`, and **not one carries a D-06
  label** — re-confirmed here on the accepted mesh, and asserted by the script.

## 9. Reproducing

```
"/c/Program Files/FreeCAD 1.1/bin/python.exe" scripts/lc1_solve.py                  # the M2.5 record
"/c/Program Files/FreeCAD 1.1/bin/python.exe" scripts/lc1_solve.py --no-solve       # deck only
"/c/Program Files/FreeCAD 1.1/bin/python.exe" scripts/lc1_solve.py --region 2.0 --tag region2
```

On the D-17 machine the interpreter is `vendor/fem-env/bin/python`. Exit 0 when the solve finished
and every guard passed — reaction balance, a non-zero stress field, a working directory ccxtools did
not redirect, a D-06 partition, and no D-06 set in the deck — and 2 otherwise. `--tag` writes to
`out/lc1_solve_<tag>/` so a probe cannot overwrite the record. Each run writes the FCStd, Gmsh's
working files, the ccxtools deck and `.frd`, the fallback `d06_elsets.inp` and `result.json`;
`out/` is gitignored.

`scripts/ge_bracket_labels.py` gained a VTK branch for the centroid fallback's cell locator, because
this machine has no pyvista. Both branches compute the same thing — pyvista's `find_closest_cell` is
a wrapper over `vtkStaticCellLocator` — and `result.json` records which one ran under
`d06_partition.locator`.

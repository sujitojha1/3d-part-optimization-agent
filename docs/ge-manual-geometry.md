# GE manual geometry — frozen source record (M2A.1, M2A.8)

> **4 Oct:** rewritten for the current part, `GE_Challenge_Bracket`, after the M2A.8 repair
> ([#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66)). Everything here comes from the
> current `out/ge_challenge_solid/solid-check.json` and `out/ge_manual_geometry/geometry-check.json`. The
> Iteration1 record this page held before is in git history; section 7 records why it was superseded.

| | |
| --- | --- |
| Tasks | M2A.1 ([#59](https://github.com/sujitojha1/3d-part-optimization-agent/issues/59)) and M2A.8 ([#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66)) · [M2A workflow](ge-manual-workflow.md) |
| Frozen | 2026-10-04 (first frozen 2026-09-20; B2 hole rebuilt 2026-10-04) |
| Selected file | `data/ge_manual/GE_Challenge_Bracket.stp` (gitignored: derived from CAD licensed non-commercial by GrabCAD) |
| SHA-256 | `d0b2adcec4e7f14ad6a24078e9afae53a2d96f6f5e872caded15934892161117` (101,187 bytes), recorded in `scripts/ge_part.py` |
| Built from | `data/simjeb/Bracket_Modified_FVZ.stp`, SHA-256 `aa9cf67d296938b0dfa2c3af542e40e643568277d09de52c17afd0e9e908e023`, never written |
| Build | `$FEM_PYTHON scripts/ge_challenge_solid.py` → the STEP and `out/ge_challenge_solid/solid-check.json` |
| Working copy | `data/ge_manual/GE_Challenge_Bracket_manual.FCStd`, built from `GE_Challenge_Bracket_deck_frame.step` (both gitignored) |
| Check | `$FEM_PYTHON scripts/ge_manual_geometry.py` (about 5 min, FreeCAD 1.1.3) → `out/ge_manual_geometry/geometry-check.json` and annotated views |
| Status | **Frozen and accepted.** One valid solid; external surface identical to the donor's outer shell; interfaces match the GE brief; no short edge or small face; boolean check clean on the working copy; **all seven M2A.2 mesh thresholds pass at L1** ([mesh record](ge-manual-mesh.md)). **A person still needs to open the file in the FreeCAD GUI** to confirm the views and face picks |

The manual M2A study uses exactly one geometry file, the one in the table above. The parametric agent baseline
`parts/ge_bracket.FCStd` ([part record](ge-bracket-part.md)) stays separate and unchanged.

**This file is not GE's original part.** It is the external surface of a 2013 challenge entry with a solid
interior of our own (section 1). Nothing on this page verifies the original part's envelope, because no reference
for it exists: the challenge's `original.stp` link returns 404 ([GE brief §1](ge-jet-engine-bracket.md)).

## 1. Identity and provenance

| Item | Value | Source |
| --- | --- | --- |
| Design identity | Our solid: the outer shell of GrabCAD GE challenge entry `ge-jet-engine-bracket-for-dmls-1`, file `Bracket_Modified_FVZ`, closed into a solid with a fully dense interior | `ge_challenge_solid.py`; `all_bracket_metadata.tab` row id 79 |
| Donor attribution | **Fritz VZ** (GrabCAD `fritz.vz-1`). CAD licensed for non-commercial use by GrabCAD; the SimJEB metadata is ODC-By (cite Whalen, Beyene & Mueller 2021) | Metadata; [SimJEB README](simjeb-dataset.md) |
| Donor SimJEB record | id **79**, category `block`, metadata volume 172,574.7 mm³ (the lightweighted part, with its cavity) | Metadata |
| Donor CAD system | Siemens UGS NX 6.0, exported by ST-Developer v11, schema `AUTOMOTIVE_DESIGN` (AP214), timestamp 2013-07-30T13:20:59−04:00 | Donor STEP header |
| This file's CAD system | FreeCAD 1.1.3, Open CASCADE STEP translator 7.9, schema `AUTOMOTIVE_DESIGN` (AP214) | STEP header |
| Units | Declared `SI_UNIT(.MILLI.,.METRE.)`, distance accuracy 0.005 mm | STEP header |
| Redistribution | **Not redistributed.** The solid is derived from licensed CAD, so it stays in the gitignored `data/` and is rebuilt locally from the donor. Only its checksum and the script are committed | Project policy |

**The file is frozen as generated.** Open CASCADE writes a timestamp into the STEP header, so regenerating the
file changes its bytes. The checksum in `scripts/ge_part.py` must then be re-recorded, and everything downstream
re-run.

## 2. How the solid is built (M2A.8)

The donor is one solid with two closed shells. Every defect that stopped it meshing is in the inner one:

| Donor shell | Faces | Edges | Faces < 1 mm² | Zero-length edges | Smallest face |
| --- | --- | --- | --- | --- | --- |
| Outer | 58 | 166 | 0 | 0 | 46.72 mm² |
| Inner (sealed cavity, 3.17 mm offset) | 258 | 603 | 8 | 10 | 0.0039 mm² |

1. **Keep the outer shell, drop the cavity.** The outer shell is closed into a solid: 463,257.7 mm³ against the
   donor's 172,106.5 mm³.
2. **Rebuild the B2 bolt hole.** In the donor, each end circle of the Ø 10.668 hole is closed by a
   **0.207 mm B-spline sliver**. Gmsh honours that edge, and it produced the one element that failed the gamma
   threshold at L1 (0.015 against 0.05), at the bottom edge of hole B2. The hole is plugged and re-drilled on the
   same axis and radius, which leaves plain circles. The edge count goes from 166 to 162 and the shortest edge
   from 0.207 to 0.658 mm.
3. **Interior: fully solid, by decision.** No pockets, ribs or cavity are added. A solid part is machinable and
   is the honest subject for the CNC readiness study ([M2A.7](ge-manual-cam-readiness.md)); lightweighting is the
   optimisation agent's job, not this baseline's. Mass in Ti-6Al-4V is **2,052.2 g**
   ([M2A.3](ge-manual-materials.md)).

**The external surface did not move.**

| Check | Result |
| --- | --- |
| Donor outer-shell vertices to this solid | 0.000 mm (every vertex) |
| Sampled surface, donor outer shell → this solid | 7.5×10⁻¹¹ mm maximum |
| Sampled surface, this solid → donor outer shell | 9.9×10⁻¹¹ mm maximum |
| Volume change from the hole rebuild | +0.053 mm³ in 463,258 (1×10⁻⁷): the sliver B-spline became a true arc |

Sampling is a 0.05 mm tessellation, every fifth point, with the exact distance to the other solid.

**Budget from the issue, as built**

| Rule | Result |
| --- | --- |
| No face under 1 mm² | Smallest is 46.66 mm² |
| No edge under 0.3 mm | Shortest is 0.658 mm |
| No zero-length edge | None |
| Minimum wall ≥ GE's 1.27 mm minimum feature | 4.66 mm (section 3) |

## 3. Solid checks

| Check | Result |
| --- | --- |
| B-rep validity (`isValid`) | **Valid** |
| Solids / shells | **1 solid, 1 closed shell**; 58 faces, 162 edges |
| Volume / area | 463,257.630 mm³ / 53,993.3 mm² |
| Bounding box, native frame | x −163.297…15.240, y −44.440…47.709, z −22.362…88.904 mm |
| Bounding box, deck frame (section 4) | x −39.293…67.286, y −163.428…16.754, z 0…62.505 mm (106.6 × 180.2 × 62.5) |
| Minimum wall (sampled) | **4.66 mm**, 1st percentile 4.71 mm; 0 samples below GE's 1.27 mm minimum feature. Method: an inward ray from each of 42,104 triangle centroids (0.05 mm-deflection tessellation) to the next surface. The thinnest sections are between a counterbore and the base end wall, near (−14.6, −152.6, 15.5) and (−14.2, 5.4, 15.5) in the deck frame. This is an estimate from samples, not an exact B-rep distance |
| BOP checker (`check(True)`), source STEP | 28 edge and 28 face `BOPAlgo_InvalidCurveOnSurface` messages; explained and cleared in the working copy, below |
| BOP checker, working copy and partitioned copy | **Clean** |

**The boolean-check flags are a tolerance artefact, not a geometry fault.** On 24 edge-and-face pairs (blend
cylinders and the counterbore tori) the 2-D curve on the surface and the 3-D edge differ by at most
**0.00704 mm**. The STEP import assigns those edges a tolerance of 0.00703 mm, so each pair sits 0.00001 mm
outside its own tolerance and the checker flags it. Nothing is moved to fix this: the working copy's B-rep
tolerance is set to **0.01 mm**, above the measured difference, and the check is clean. OCC's `fix()` alone does
not clear the flags. For scale, 0.007 mm is under 1 % of the smallest mesh size used.

## 4. Coordinate frame and load transform

**Native frame.** The file is stored tilted, as the donor is. The pin axis lies exactly along native +x, and the
base normal (the bolt axis, oriented toward the pin) is (0, 0.662599, 0.748974). That is 41.50° from native z.
**Do not apply SimJEB load vectors in the native axes.**

**Deck frame.** This is the frame of the SimJEB `148.fem` deck, which fixes the GE load vectors
([SimJEB §2](simjeb-dataset.md)): +z vertical up, "out" is −x, and z = 0 is the base bottom plane. The four bolt
axes were fitted rigidly, in plane, to the deck's RBE2 spider centres (nodes 129261–129264). The fit residuals are
0.07, 0.22, 0.18 and 0.14 mm. The transform is p_deck = R · p_native + t:

```
R = [[ 0.030277763546,  0.748630626819, -0.662295584783],
     [-0.999541523417,  0.022677258094, -0.020062027083],
     [ 0.0,             0.662599371079,  0.748974013866]]
t = [38.027871, -147.035461, 0.0] mm
```

It is the same transform as Iteration1's: the two entries share the challenge's interface positions.

**Independent check.** The deck's RBE3 pin load node (129265) was not used in the fit. It lies at
(−21.036, −75.065, 44.801); this file's pin reference transforms to **(−20.974, −74.760, 44.725)**. The difference
is (0.06, 0.30, −0.08) mm, mostly along the pin axis. The body's centre of mass sits at x = +20.05, so −x points
from the body toward the clevis: "out" is consistent.

**Pin axis is not exactly along y.** In the deck frame the pin axis is (0.0303, −0.9995, 0), 1.73° from y. LC2
and LC3's "out" component (−x) is therefore 1.73° off perpendicular to the pin. M2A.5 applies the SimJEB vectors
unchanged in the deck frame, to stay comparable with SimJEB.

## 5. Interfaces against the GE brief

Bolt labels B1–B4 follow the `148.fem` RBE2 order, which is also Interfaces 2–5 in the
[part record](ge-bracket-part.md) and in [M2A.4](ge-manual-boundary-conditions.md).

### Interface 1 — pin and lug bores

| Item | This file | GE brief / reference | Status |
| --- | --- | --- | --- |
| Bore diameter, both lugs | **Ø 19.1135** (0.7525 in), one common axis | Pin Ø 19.05 (0.75 in) | Pin fits: **0.0635 mm diametral clearance** |
| Lug (bore) length | 6.35 each (0.250 in) | — | Matches SimJEB 148 |
| Clevis gap / outer span | 22.225 (0.875 in) / 34.925 (1.375 in) | — | Matches SimJEB 148 |
| Bore centres (deck) | (−21.406, −60.480, 44.725) and (−20.541, −89.041, 44.725) | — | — |
| **Pin reference point** (pin centreline × clevis midplane) | **(−20.974, −74.760, 44.725)** deck; 44.7246 above base bottom | RBE3 node (−21.036, −75.065, 44.801) | Load and moment reference for M2A.4/M2A.5 |

### Interfaces 2–5 — bolts and nut seats

| Bolt | Axis (x, y) deck | Hole Ø | Clearance on Ø 9.525 bolt | Nut seat |
| --- | --- | --- | --- | --- |
| B1 (node 129261) | (52.003, 1.512) | 10.3124 (0.406 in) | 0.787 | z = 7.8486, flat annulus Ø 10.31–16.00, 117.6 mm² |
| B2 (node 129262) | (−0.044, −0.064) | **10.668 (0.420 in)** | **1.143** | z = 7.8486, flat annulus Ø 10.67–16.00, 111.7 mm² |
| B3 (node 129263) | (−0.056, −148.189) | 10.3124 | 0.787 | z = 7.8486, flat annulus Ø 10.31–16.00, 117.6 mm² |
| B4 (node 129264) | (38.028, −147.035) | 10.3124 | 0.787 | z = 7.8486, flat annulus Ø 10.31–16.00, 117.6 mm² |

- **Seats.** Each nut seats on a flat annular boss top, 7.8486 mm (0.309 in) above the base bottom. The boss is
  Ø 16.00 OD and sits in a Ø 21.08 counterbore. The GE nut face (Ø 10.287 max ID, Ø 14.173 min OD) fits inside
  every boss top, with 0.91 mm radial margin to the Ø 16.00 edge. The base bottom (z = 0, 13,998.3 mm²) is one
  plane and is the mating face.
- **Contact patch for M2A.4.** Each hole is larger than the nut face's maximum ID, so the nut bears on an annulus
  from the hole edge out to Ø 14.173: **74.2 mm²** at B1, B3 and B4, and **68.4 mm²** at B2. M2A.4 partitions the
  seats at Ø 14.173.
- **B2's hole is oversize.** GE specifies the bolt (Ø 9.525) and the nut face, not the hole. This file has
  Ø 10.3124 at B1, B3 and B4, and **Ø 10.668 at B2**, as the donor does. It still clears the bolt and still
  carries the GE nut face, but its contact annulus is 8 % smaller. The M2A.8 rebuild kept this diameter.
- **Bolt pattern.** The spacing is **not** a rectangle: B1–B2 is 52.07 mm, B3–B4 is 38.10 mm, B2–B3 is 148.13 mm
  and B1–B4 is 149.20 mm. This is the same pattern as SimJEB's deck; all four holes fit it within 0.22 mm.

### Envelope

Not verified. There is no original-envelope reference. The deck-frame bounding box in section 3 describes the
donor entrant's design, not GE's envelope.

## 6. Working copy and symmetry

**Working copy.** `data/ge_manual/GE_Challenge_Bracket_manual.FCStd` holds:

- `Bracket`: the solid in the deck frame, with an identity Placement and a 0.01 mm B-rep tolerance (section 3);
- `PinReference`: a vertex at the pin reference point.

The script moves the source into the deck frame and writes `GE_Challenge_Bracket_deck_frame.step`, reads it back,
and saves the result in the document. It never writes to the source; the checksum is re-verified after the run.

The STEP round trip is deliberate. On Iteration1, leaving the transform as a Placement made BRepCheck flag
located chamfer cones as "Unorientable", and FEM would inherit that located shape. This part shows no such
face, and the round trip is kept so every part takes the same route. The round-trip solid is valid, with 58
faces and no volume change. The saved document reopens as 1 valid solid with a clean boolean check.

| Artifact (this build) | SHA-256 |
| --- | --- |
| `data/ge_manual/GE_Challenge_Bracket_deck_frame.step` | `26a54d6054ed9c58994cf6e27186672d53aa3152566dfdcb2f0ac0842e5f0608` |
| `data/ge_manual/GE_Challenge_Bracket_manual.FCStd` | `e892ab9c912e7eee2bf8b6d44bffa8c8b0b865b3752906588fc236a9fad9e785` |
| `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd` ([M2A.4](ge-manual-boundary-conditions.md)) | `435c6724cf8e1c87296bde2b95d696621a0b45fd19d7fc116a35b2bc8308897d` |

All derived files embed timestamps, so re-running a script changes their checksums. Downstream M2A records cite
the checksum of the copy they actually used. The stable identity is the source SHA-256.

**Full model required.** The geometry is not mirror-symmetric about the clevis midplane:

- mirrored surface vertices deviate by up to 18.3 mm;
- 85 % of them deviate by more than 0.1 mm;
- the bolt pattern is a trapezoid (52.07 versus 38.10 mm);
- B2's hole is oversize.

LC4's torque about z would be antisymmetric even on symmetric geometry. **Use the full model for all four cases.**

**Annotated views** (generated locally, gitignored): `out/ge_manual_geometry/interfaces_iso.png`,
`interfaces_top.png`, `interfaces_front.png` and `interfaces_side.png`. Each shows the deck frame, the Ø 19.05
pin through both bores with its reference coordinates, each bolt axis with its hole Ø and seat height, the GE
nut-face annulus drawn on each seat, and the −x "out" arrow.

## 7. Supersession record

| Date | Selected geometry | Why it was replaced |
| --- | --- | --- |
| 19 Sep | `Iteration1.stp` (SimJEB id 474, 283,730 mm³) | Meshes cleanly, but its weight is taken out by open pockets cut up from the underside, so the underside is not continuous |
| 20 Sep | `Bracket_Modified_FVZ.stp` (SimJEB id 79, 172,106 mm³) | Continuous underside, but the weight is taken out by a **sealed internal cavity** no tool can reach, and that cavity's 258-face shell cannot be meshed to the M2A.2 thresholds: gamma stayed at 0.0135 from 89,538 to 473,335 nodes. Healing leaves it unchanged or destroys the solid |
| 20 Sep | `GE_Challenge_Bracket.stp`, first build (`d34fab37…`): FVZ's outer shell, solid interior | Passed at L2 and L3 but **failed gamma at L1** (0.015) on one element at hole B2, and carried 28 + 28 boolean-check flags |
| **4 Oct** | **`GE_Challenge_Bracket.stp`, B2 hole rebuilt (`d0b2adce…`)** | Current. L1, L2, L3r and L3 all pass the seven thresholds; boolean check clean |

The pre-repair geometry, meshes and results are kept locally in `data/ge_manual/before-m2a8-repair/` and
`out/before-m2a8-repair/`. M2A.2–M2A.7 were re-run on the repaired source.

## 8. Status against the M2A.1 and M2A.8 checklists

| Step | Status |
| --- | --- |
| M2A.1 1. Path, identity, attribution, SHA-256, units, frame, CAD version | Done (sections 1 and 4) |
| M2A.1 2. Validity, connectivity, bounding box, volume, minimum walls, four nut/bolt locations, both lug bores, annotated views | Done by script (sections 3, 5 and 6). **A person still needs to open the file in the FreeCAD GUI** to confirm the views and face picks; everything here ran headless in FreeCAD 1.1.3 |
| M2A.1 3. Pin Ø 19.05 and bolt/nut interfaces; deviations; envelope not claimed | Done (section 5) |
| M2A.1 4. Separate working copy, source intact; full model unless symmetry justified | Done (section 6); full model |
| M2A.8 1. External surface taken unchanged; checksum recorded; donor untouched | Done (sections 1 and 2) |
| M2A.8 2. Interfaces re-checked against the GE brief on the closed solid | Done (section 5) |
| M2A.8 3. Internal volume decided and recorded | Done: fully solid (section 2) |
| M2A.8 4. Minimum-wall and quality budget | Done (section 2) |
| M2A.8 5. All seven M2A.2 thresholds at L1, with no exception; then re-freeze and re-run M2A.1–M2A.7 | Done: L1 passes ([mesh record](ge-manual-mesh.md)); M2A.2–M2A.6 were re-run on 4 Oct and M2A.7 on 7 Oct |

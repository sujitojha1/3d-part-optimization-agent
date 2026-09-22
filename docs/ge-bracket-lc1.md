# ge_bracket LC1 — frozen load record

| | |
| --- | --- |
| Task | M2.2 ([#46](https://github.com/sujitojha1/3d-part-optimization-agent/issues/46)) |
| Frozen | 2026-09-19 |
| Record | `parts/ge_bracket_lc1.json`, the machine-readable copy M3.3 reads |
| Evidence | `vendor/fem-env/bin/python scripts/lc1_pin_models.py [--model rigid\|half_bore] [--hmax MM]` |
| Part | [ge-bracket-part.md](ge-bracket-part.md). M2.2 changed it: the bosses are now flush (section 5) |

## 1. The record

One load case (D-08), in SimJEB's convention: mm, N, MPa, **+z up**, "out" is −x.

| Item | Value |
| --- | --- |
| Load | **(0, 0, +35,585.77) N**, from SimJEB `148.fem` `FORCE 2` on node 129265 (8,000 lbf vertical) |
| Applied at | Pin centre (−21.036, −75.065, 44.801) mm, through both pin bores |
| Pin-load model | **Rigid Body Constraint** on `pin_bore_pos_y` and `pin_bore_neg_y`, reference node at the pin centre, translations loaded, rotations free (section 3) |
| Support | FreeCAD **Fixed** on each bolt-hole face `bolt_hole_2`–`5`: every hole node held in all DOF. Same as SimJEB's RBE2 spider with `SPC 123456` |
| Material | Ti-6Al-4V: E 113,800 MPa, ν 0.342, ρ 4,430 kg/m³ (SimJEB `MAT1`); yield **903.2 MPa** (131 ksi, the challenge) |
| Safety factor | **1.5**, so the allowable von Mises is **602.1 MPa** |
| Stress check | Max nodal von Mises **outside the support zone** ≤ 602.1 MPa. The zone is a 10 mm radius in plan about each bolt axis, full height (section 4). The raw peak is reported and flagged too. **Region scoring** (D-07 region hit) reads a separate 25 mm zone, never pass/fail (owner, 2026-09-22; [M2.7 §4](m2-exchange.md)) |
| Displacement limit | **1.1 × baseline** max displacement magnitude: baseline 0.4506 mm, **limit 0.4957 mm**. Re-measure when M2.3 freezes D-24's mesh sizes |
| Model extent | **Full model.** D-23's half model does not apply, because SimJEB's bolt pattern is not symmetric about the clevis midplane |
| Wrong-direction mutant (D-16) | This record with the vector **(0, 0, −35,585.77) N** |

## 2. Hand calculation, before the solve

The arithmetic uses the baseline in [ge-bracket-part.md §3](ge-bracket-part.md).

**Bolt reactions: rigid plate over the bolt group.** The pin sits 43.5 mm outboard of the
bolt-group centroid in −x, so the group takes a moment as well as the force. A linear
distribution R = a + b·x + c·y, fitted to the total force and both first moments, gives:

| Bolt | Position | Share of the load |
| --- | --- | --- |
| 2 | (51.9, 1.6) | −10.4 kN: pulled the other way, prying |
| 3 | (0.0, −0.3) | +28.2 kN |
| 4 | (−0.2, −148.1) | +23.2 kN |
| 5 | (38.1, −147.0) | −5.3 kN: prying |

**Stresses, nominal:**

| Where | Model | Stress |
| --- | --- | --- |
| Base plate, section at each arm's outer face | Bolt reactions × lever to the section; full outline width (104–107 mm), t = 18 | 168 MPa (+y wing), 174 MPa (−y wing) |
| Arm root | Half the load on 54.5 × 8 mm, plus 7.74 mm eccentricity in x | 41 + 35 = 76 MPa |
| Pin bearing | F / (2 · 19.05 · 8) | 117 MPa |
| Lug net section | (F/2) / (2 · 10 · 8) | 111 MPa |

**Prediction:** the baseline passes by more than 3×. The peak is in the **base plate**
between the arm feet and bolts 3 and 4, not at the arm-root fillet (76 MPa nominal, Kt about
1.5).

## 3. Pin-load model: both tried

FreeCAD has no `*DISTRIBUTING COUPLING`, so SimJEB's RBE3 pin spider has no direct
equivalent. The baseline was solved both ways: second order, `HighOrderOptimize =
Optimization`, max 4 mm, min 1 mm, about 67k nodes, 16–17 s per solve.

| Quantity | `rigid` | `half_bore` |
| --- | --- | --- |
| How | One Rigid Body Constraint on both bores; the vector is one CLOAD on the reference node | Bores split at the pin plane; Force on the four upper-half faces |
| Load written to the deck | 35,585.77 N, exact | 35,543.79 N (**−0.118 %**, FreeCAD's area weighting) |
| Bolt reactions | balance the load to 0.0 % and 0.0° | balance what was written |
| Peak outside the support zone | **457.8 MPa**, base underside by bolt 4 | 471.0 MPa, same node |
| `arm_root_fillet` peak | 255.7 MPa | 195.4 MPa |
| `pin_bore` / `clevis_arm` peak | 202 / 211 MPa | 412 / 398 MPa |
| Max displacement | 0.451 mm, base −x end | 0.491 mm, lug top |

**Chosen: `rigid`.**
- The challenge calls the pin infinitely stiff.
- The declared vector reaches the deck exactly, as a single CLOAD, and that is what
  `REQ-VER-006` needs to read.
- One reference node matches SimJEB's load node, which V3 compares against.
- The bore faces stay whole, so each bore predicate still matches exactly one face
  (`REQ-OPT-008`). Splitting the bores for `half_bore` breaks that.
- The governing base-plate peak differs by 3 %.

**Cost of that choice:** a rigid pin ties both bores together and stops them ovalising. It
reads about **half** the `half_bore` stress at the lug and bore. The lug is far from critical
at the baseline, but an agent thinning `lug_wall` toward 5 mm sees optimistic numbers there.
Recorded as a known unconservative bias. If `pin_bore` or `clevis_arm` ever becomes the
peak region, re-check with `half_bore`.

**A wrong-direction bug, caught.** The first `half_bore` run set the Force constraint's
`DirectionVector` from Python. FreeCAD silently replaced it on recompute with a direction
taken from the bore faces. The load went in at **45°**, (+25.1, 0, −25.1) kN, and nothing
warned. The script now sets `Direction` from a reference face, asserts `DirectionVector`
after recompute, and checks every run's bolt reactions against the declared vector (0.1°
and 0.5 %). That is the check `REQ-VER-006` describes, and this is a real instance of the
failure the D-16 mutant simulates.

## 4. The bolt-hole supports are singular

A fully fixed hole face meeting a free face is a stress singularity, the same as a sharp
re-entrant corner ([fem-geometry-preparation §13](fem-geometry-preparation.md)). The raw
peak shows it:

| Mesh (max size) | Raw peak | Where | Peak outside the support zone |
| --- | --- | --- | --- |
| 4 mm, 67k nodes | 778 MPa | bolt 3 hole, bottom edge | 457.6 MPa at (−13.4, −136.8, 0) |
| 2.5 mm, 147k nodes, 80 s | 709 MPa | bolt 4 hole, **top** edge | 455.9 MPa, same node |

The raw peak exceeds the allowable, jumps between holes and does not settle. The peak
outside the zone changes by 0.4 % and stays at the same node, so it is a real stress. D-12's
protocol would mark every baseline `unverified` if it read the raw peak. So the stress check
reads the peak outside a 10 mm plan radius about each bolt axis: the boss lobe, a hole
radius plus 4.85 mm of wall. The raw peak is still reported and flagged. **This changes how
`REQ-VER-002` and D-12 read "peak", and needs owner confirmation.**

## 5. Solve against the hand calculation

`rigid`, 4 mm mesh:

| Quantity | Hand | FE | Why they differ |
| --- | --- | --- | --- |
| Bolts 3 and 4 | +28.2 / +23.2 kN | +20.9 / +21.2 kN | Same pattern. The plate is flexible, so bolts 2 and 5 pry less |
| Bolts 2 and 5 | −10.4 / −5.3 kN | −3.5 / −3.0 kN | Prying, confirmed |
| Governing stress | 168–174 MPa | **457.8 MPa** | The load runs through a strip about 45 mm wide from the arm foot to bolt 4, not the full 104 mm. 21.2 kN × 54 mm on 45 × 18² gives about 530 MPa |
| Peak region | `base_plate` | `base_plate`, underside near bolt 4 | Agree |
| Arm-root fillet | 76 MPa × Kt ≈ 115 | 256 MPa | Second highest region; the fillet also carries base-plate bending |

The FE agrees with the prediction on where the peak is and on the reaction pattern. It
disagrees by 2.7× on the governing stress. The full-width section was optimistic, and the
first solve showed it. The baseline passes: 458 MPa against 602 MPa is **1.32×**, and
0.451 mm defines the displacement limit. The margin is thinner than the hand calculation's
3×.

**The plan expected the peak at the fillet.** It lands in the base plate. Two consequences:
an `arm_root_fillet` edit will not move the governing peak on this part, and D-12's
calibration on that fillet tests a region that is not the peak. The fillet is still the
right place to calibrate the singularity check, because the D-16 mutant sets its radius to
zero.

**The part changed in M2.2.** M2.1's bosses stood 3 mm proud of the base. That left a sharp
90° root corner, and under LC1 it held the peak outside the support zone. The value rose
16 % under refinement (460 → 533 MPa), a geometric singularity. The bosses are now **flush**
lobes of the base outline, and the nut seats on the base top. The baseline mass drops from
1,211 g to **1,199 g**. All 77 check states still pass.

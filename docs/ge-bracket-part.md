# ge_bracket — frozen part record

| | |
| --- | --- |
| Task | M2.1 ([#44](https://github.com/sujitojha1/3d-part-optimization-agent/issues/44)) |
| Frozen | 2026-09-19 |
| Document | `parts/ge_bracket.FCStd`, built by `parts/ge_bracket.py` (kept, promoted in M3.1) |
| Check | `vendor/fem-env/bin/python scripts/ge_bracket_check.py [--corners]` |
| Decisions | [D-04](requirements.md), D-05, D-06, D-11, D-14; inputs from [SimJEB](simjeb-dataset.md) and the [GE brief](ge-jet-engine-bracket.md) |

This page freezes the demo part: its interfaces, its six parameters, its region labels, the
face predicates everything else selects with, and its `cnc_3axis` setups. The load case,
pin-load model and half-model decision are **M2.2's**, not this page's. Section 7 lists what
building the part found about other decisions.

## 1. Frame and interfaces

SimJEB's frame: mm, **+z up**, "out" is **−x**. Every interface value below is measured from
design 148 (`148.fem` spider nodes, and the `surf` = 2 and 3 nodes of `148field.csv`). SimJEB
puts the interfaces at the same place in all 381 designs.

| Interface | Feature | Where (mm) | Size |
| --- | --- | --- | --- |
| 1 | Pin bore, axis ∥ y | centre (−21.036, −75.065, 44.801), the RBE3 load node | Ø 19.05 (measured r 9.54) |
| 1 | Clevis gap | inner arm faces at y = −85.52 and −63.88 | 21.64 wide. Centred on the pin, 0.37 mm off SimJEB's own midpoint |
| 2 | Bolt hole, axis ∥ z | (51.948, 1.552) | Ø 10.30 |
| 3 | Bolt hole | (0.042, −0.270) | Ø 10.30 |
| 4 | Bolt hole | (−0.202, −148.094) | Ø 10.30 |
| 5 | Bolt hole | (38.142, −146.964) | Ø 10.30 |

Interfaces 2–5 follow the `148.fem` RBE2 order (spider nodes 129261–129264). SimJEB's pin
axis tilts about 2° from y (`(0.030, −0.999, −0.025)`). This model uses exact y, within
SimJEB's own picking accuracy.

## 2. Construction

`GeBracket` is a FreeCAD Python feature whose six length properties are bound by expression
to the aliases of the `Params` spreadsheet. Setting a cell and recomputing rebuilds the solid
from scratch. The builder picks the arm-root fillet edges by position, so the geometry itself
never refers to an edge or face index. Open the document with the repository root on
`sys.path`, because it stores the class as `parts.ge_bracket.GeBracket`.

- **Base plate:** the convex hull of the four bolt centres and the two arm footprints, offset
  outward by the boss radius, extruded to `base_thickness`. The outline is convex, so it has
  no inside corners for a tool to miss.
- **Bolt bosses:** the outline's Ø 20 lobes round each bolt, **flush with the base top**.
  They clear the 14.173 mm nut-face OD, and the nut seats on the base top. The bolt holes go
  through the base. M2.2 removed the original 3 mm raise because its sharp root corner was a
  singularity under LC1 ([ge-bracket-lc1.md §5](ge-bracket-lc1.md)).
- **Clevis arms:** two plates normal to y, each a lug (radius 9.525 + `lug_wall` about the
  pin) hulled onto a foot. The foot runs along x from the lug's −x tangent to pin x + 35 mm.
- **Arm-root fillets:** `arm_root_fillet` on the full root loop of each arm: the two long
  edges along x and the two short ends along y.
- **Base pockets:** one underside pocket in each wing, between an arm and its bolt row. Each
  sits 12 mm clear of the arm, 6 mm inside the outline and 14 mm from every bolt axis, with
  4 mm inside corners.
- **Centre hole:** through the base at (39.5, pin y), on the clevis midplane.

Fixed choices, not agent parameters: boss Ø 20, foot length, and the pocket
clearances and corner radius. Material Ti-6Al-4V at 4.43 g/cm³, from the SimJEB deck.

## 3. Parameter record (D-05)

| Parameter | Kind | Baseline | Min | Max | Step |
| --- | --- | --- | --- | --- | --- |
| `base_thickness` | `wall_thickness` | 18.0 | 12.0 | 24.0 | 0.5 |
| `arm_thickness` | `wall_thickness` | 8.0 | 4.0 | 12.0 | 0.5 |
| `lug_wall` | `wall_thickness` | 10.0 | 5.0 | 15.0 | 0.5 |
| `arm_root_fillet` | `fillet_radius` | 5.0 | 3.0 | 8.0 | 0.5 |
| `base_pocket_depth` | `pocket_depth` | 3.0 | 1.0 | 8.0 | 0.5 |
| `centre_hole_diameter` | `hole_diameter` | 14.0 | 8.0 | 20.0 | 1.0 |

All values are in mm. Baseline mass is **1,199 g**, and the range over all 64 bound corners
is 574–1,808 g. SimJEB 148 weighs 582 g.

- **Thickness floor:** the thinnest section anywhere in the box is 4.0 mm (pocket floor at
  `base_thickness` 12, `base_pocket_depth` 8), above the 1.27 mm floor. `lug_wall` ≥ 5 and
  the boss wall is 4.85. The centre hole stays ≥ 5.3 mm from the outline and ≥ 9.7 mm from
  the fillets.
- **Fillet and tool:** every `arm_root_fillet` from 3.0 to 8.0 is cut by the **6 mm endmill**
  (r 3.0). The minimum is 3.0 so that no permitted edit needs a smaller tool. D-16's
  sharp-corner mutant (`arm_root_fillet` = 0) sits outside the bounds on purpose, and no tool
  cuts it.
- **Why a thick base:** see section 6. A 10 mm plate fails in bending. The mass levers are
  the pockets, the centre hole and the plate itself.

## 4. Named regions and face predicates (D-06, D-04)

Every face carries exactly one label. Single-face predicates each match **exactly one** face
(`REQ-OPT-008`), and constraints and CAM operations select only through those. Set rules
label whatever those leave, and they may match any number of faces.

| Region | Single-face predicates | Set rules |
| --- | --- | --- |
| `pin_bore` | `pin_bore_pos_y`, `pin_bore_neg_y`: cylinder r 9.525, axis ∥ y through the pin, on that side of the clevis midplane | — |
| `clevis_arm` | per side: `lug_*` (cylinder r = 9.525 + `lug_wall` about the pin), `arm_outer_*` and `arm_inner_*` (planes ⟂ y at the arm faces), `arm_end_*` (plane ⟂ x at the lug's −x tangent), `arm_slope_*` (plane with normal in +x+z) | — |
| `arm_root_fillet` | per side: `fillet_inner_*`, `fillet_outer_*`, `fillet_x0_*`, `fillet_x1_*`: non-planar, starting on the base top, beside that edge of the arm footprint | `fillet_corner`: corner blends OCC adds where two root fillets meet. Seen at 8 mm, not at 5 mm |
| `base_plate` | `base_top`, `base_bottom`, `centre_hole`, `pocket_floor_pos_y`, `pocket_floor_neg_y` | `base_side` (outline walls), `pocket_wall` |
| `bolt_boss` | per interface 2–5: `bolt_hole_N` (cylinder r 5.15, axis ∥ z through that bolt), `boss_side_N` (the outline's r 10 lobe round that bolt) | — |
| `bulk` | — | Empty on this part: every face has a label |

**Constraints use:** `bolt_hole_2`–`5` (fixed interfaces) and `pin_bore_pos_y` and
`pin_bore_neg_y` (the load; M2.2 picks the model).

**Checked (2026-09-19):** 77 states, all valid single solids with every predicate at exactly
one face and every face labelled once. They are the baseline, each parameter alone at its
min and at its max, and all 64 bound corners. A rebuild takes about 0.14 s. The fillet
topology changes across the box: corner blends appear at large radii. That is why they are a
set rule, not a predicate. M2.4 carries these faces through Mesh Groups into the `.inp`.

## 5. `cnc_3axis` setups and ToolBit library (D-11)

Library: `tooling/cnc_3axis.fctl`, unchanged from Gate 4. It holds a 6 mm endmill (30 mm
cutting edge), a 3 mm endmill (20 mm) and a 5 mm drill.

| Setup | Operation → predicate-selected faces | Reach needed |
| --- | --- | --- |
| `top_+z` | Profile: outline (`base_bottom` contour), `centre_hole`, `bolt_hole_2`–`5`. Adaptive: `base_top` | holes ≤ 24 mm (at max base) |
| `bottom_-z` | Adaptive: `pocket_floor_*` | ≤ 8 mm |
| `side_+y`, `side_-y` | Profile: `lug_*`, `arm_slope_*`, `arm_end_*`, `pin_bore_*`. Adaptive: `arm_outer_*` | ≤ 12 mm (arm thickness) |
| `end_-x`, `end_+x` | Profile: the four long `fillet_inner_*` and `fillet_outer_*`. Adaptive: `arm_inner_*` (the clevis slot) | half the foot, ≤ 29.8 mm |

**Is the arm-root fillet reachable by a 2.5D Profile from the side setup? No.** The long
root fillets run along x, so a tool along y (the `side_±y` setups) looks straight at the arm
face and cannot follow them. A 2.5D Profile cuts them only with the tool along x, from **new
`end_±x` setups**. From each end the tool must reach half the arm foot: (44.5 +
`lug_wall`) / 2, at most 29.8 mm at `lug_wall` 15. That fits the 6 mm endmill's 30 mm
cutting edge, which is why `lug_wall` stops at 15. The short fillets at the foot ends run
along y, and `side_±y` cuts them. The toroidal corner blends follow neither axis, so they
may leave residual stock under any 2.5D operation. That is **unverified until M5.2** runs
`PathSimulator` on the part. The clevis slot (21.64 mm wide, up to ~46 mm tall) is also
only reachable from the ends.

## 6. Sizing solve — provisional, not M2.2

*Superseded by [ge-bracket-lc1.md](ge-bracket-lc1.md), which solves the frozen LC1 record on
the flush-boss part. These runs used the raised bosses, and the "outside the bosses" value
here is the boss-root corner that M2.2 removed.*

This solve was run by hand, only to check the baseline wasn't absurd. M2.2 owns the load
record, the pin model and the pass/fail check. The setup: LC1 +35,585.77 N spread evenly on
both bore faces; the four bolt-hole faces Fixed; Ti-6Al-4V with E 113.8 GPa and ν 0.342;
FemMeshGmsh second order, max 4 mm, min 1 mm; full model.

| `base_thickness` | Peak von Mises | Peak outside the bosses | Max displacement | Solve |
| --- | --- | --- | --- | --- |
| 10 mm | 1,705 MPa | 1,700 MPa, base underside near bolt 4 | 2.38 mm | 7 s |
| 14 mm | 1,047 MPa | 791 MPa, same place | 0.90 mm | 10 s |
| **18 mm (baseline)** | 649 MPa | **470 MPa**, base top by bolt 3 | 0.46 mm | 15 s |
| 20 mm | 590 MPa | 370 MPa | 0.35 mm | 18 s |

The overall peak sits on the bolt-3 hole edge in every run. That is the fixed-face
singularity M2.2 must handle. Away from the bosses, 18 mm leaves about 1.3× on the 602 MPa
allowable. A flat 10–14 mm plate fails in bending between the arm feet and bolts 4 and 5,
because this part has no ramps or gussets. The full model already solves in 15 s, well
inside D-13's 60 s trigger.

## 7. Findings for other decisions

1. **D-14's bolt-hole diameter is the bolt, not the hole.** SimJEB's holes measure
   **Ø 10.30** (r 5.15 in all four), which matches the 10.287 mm nut-face ID. This part uses
   10.30. D-14 should say "bolt Ø 9.525 in Ø 10.30 holes".
2. **D-23's half model does not hold at SimJEB's interfaces.** The bolt pattern is not
   mirror-symmetric about the clevis midplane (y = −75.065). Mirrored, bolt 2 lands 13.8 mm
   in x and 4.7 mm in y from bolt 5; bolts 3 and 4 miss by 1.8 mm. Geometry and supports are
   not symmetric, so one of D-23's four conditions fails. M2.2 should default to the full
   model, which at 15 s does not need halving.
3. **D-24 needs `HighOrderOptimize` from the first mesh, and its retry fails silently.** At
   the baseline, the default second-order mesh has non-positive Jacobians and `ccx` exits
   201. `HighOrderOptimize = Optimization` fixes it (D-24 already lists it; it is not the
   FreeCAD default). The D-24 retry, `SecondOrderLinear = true`, makes `ccx` exit **0 with an
   all-zero stress and displacement field**. `REQ-VER-004` must treat an all-zero field as
   invalid, not only non-finite values.
4. **D-11's setups need `end_±x`** (section 5). The declared top, bottom and side +y cannot
   cut the long root fillets or the clevis slot. `side_-y` is also needed for the −y arm.
5. **D-06's labels hold, with a `bulk` that is empty here.** Corner blends appear and
   disappear with the fillet radius, so M2.4 needs set rules or element-centroid
   membership, not only face lists.

## 8. The other parts, and the fallback

`L_bracket`, `cantilever_plate_with_hole` and `ribbed_beam` stay deferred (D-14). One part
is what three weeks allows, and `ge_bracket` is the one with an external reference: SimJEB's
381 designs, 148 among them. **`L_bracket` is the fallback.** The trigger: if `ge_bracket`
does not mesh and solve by hand in ≤ 60 s by the end of **21 Sep** (M2.5, [plan](plan.md)),
switch the demo part. Section 6's 15 s full-model solve is an early sign this will not fire.

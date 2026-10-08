# GE manual CAM readiness — four 3-axis setups on `GE_Challenge_Bracket` (M2A.7)

> **7 Oct:** re-run on the repaired source (M2A.8, [#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66):
> the B2 bolt hole rebuilt). Everything here comes from the current `out/ge_manual_cam/` (`survey.json`,
> `op10`–`op40.json`, `assessment.json`). The readiness result is unchanged from the first issue of this page
> (3 Oct); the repair renumbered the faces, and two faults in the study's own setup were fixed (section 4). The
> Iteration1 CAM outputs are kept in `out/ge_manual_cam_Iteration1/` and are not described here.
> **CNC readiness is a project extension** to GE's additive-manufacturing brief. This page is a simulated
> readiness assessment, **not** a certification that the part is safe to machine.

| | |
| --- | --- |
| Task | M2A.7 ([#65](https://github.com/sujitojha1/3d-part-optimization-agent/issues/65)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-10-03; re-run on the repaired source 2026-10-07 |
| Geometry | `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`, SHA-256 `435c6724…8308897d`, the same solid M2A.2–M2A.6 use. 62 faces, 463,257.6 mm³, 53,992 mm² |
| Tools | FreeCAD 1.1.3 CAM Workbench: 3D Surface (experimental, needs OpenCamLib), Profile and Helix operations; `refactored_linuxcnc` post processor; `PathSimulator` |
| Tool library | `tooling/Bit/ge_manual/`: four ToolBits (section 3) |
| Script | `$FEM_PYTHON scripts/ge_manual_cam.py survey`, then `cam`, `assess`, `render` (35 min to over an hour, depending on the host; setup 2 alone takes 15–30 min). `check` redoes the simulation on the saved CAM documents without rebuilding paths |
| Data | `out/ge_manual_cam/`: `survey.json`, per setup `opNN.json`, `opNN.ngc`, `opNN_setup.png`; `assessment.json`; `readiness_map.png`. CAM documents in `data/ge_manual/cam/opNN.FCStd`. All gitignored (derived from licensed CAD) |
| Status | **Conditionally ready.** In simulation the four setups finish **99.3 %** of the surface with **no gouge**, no rapid through stock and no hit on the coarse workholding boxes. **Blocked:** the two inner bore chamfers. **Unverified:** the lug bores and outer chamfers (tool reach), the lower quadrant of the lug tips, and everything a simulator cannot establish (section 8). **One GUI walk-through is still needed**; the numbers come from the script |

## Summary

- **The part is a good 3-axis candidate.** It is one solid with a flat underside, no cavity and no thin wall.
  Top, bottom and the two pin sides have line of sight to 99.85 % of the surface.
- **Seven of eleven feature groups are ready in simulation,** covering 51,086 mm² of 53,992 mm² (94.6 %).
- **One group is blocked:** the two bore chamfers that face into the clevis gap. No axis-aligned tool can see them.
- **Three groups are unverified:**
  - **Lug bores:** the path cuts them fully, but a holder that clears the part needs 73.7 mm of stick-out, and
    the modelled Ø12 tool reaches 45 mm.
  - **Outer bore chamfers:** the same reach problem with a Ø4 ball (18 × its diameter), and the 0.64 mm chamfer
    is smaller than the stock check can resolve.
  - **Lug tips:** the lower outer quadrant of each lug tip is only 60 % finished. Setup 1 stops 8 mm short of it.
- **The 31,634 mm² "gouge" the 21 Sep review flagged was a checking fault, not a toolpath fault** (section 6).
  It is fixed, and both independent stock checks now read 0 mm².
- **Feeds and speeds are shop assumptions,** not vendor data, and no G-code has been run on a controller.

## 1. Geometry for a 3-axis mill

`survey` turns the deck frame 1.735° about z through the pin reference, so the pin axis lies along y. z = 0 is
the base bottom. The part then spans x −38.75 to 69.56, y −164.03 to 14.51 and z 0 to 62.50 mm
(108.3 × 178.5 × 62.5).

**Line of sight.** A face counts as visible from a direction when a point 0.3 mm off the surface has no material
above it along that direction (0.1 mm z-buffer). This ignores tool radius and holder; those are checked in
sections 3 and 5.

| Setups | Surface area with line of sight |
| --- | --- |
| Top only (+z) | 68.0 % |
| Top and bottom (+z, −z) | 98.2 % |
| Top, bottom and both pin sides (+z, −z, +y, −y) | **99.85 %** |
| All six axis directions | 99.85 % |

Adding ±x gains nothing, so four setups are enough. The 0.15 % left is Face58 and Face59, the bore chamfers on
the clevis-gap side.

**What limits the tools**

| Check | Finding |
| --- | --- |
| Smallest concave radius | **R2.54**, the blend at each counterbore floor: needs a ball of Ø5 or less (Ø4 used). Next is R3.175 at the four arm-root fillets (Ø6 ball fits) |
| Deep pockets | The four counterbores, Ø21.08 × 17.4 deep (0.8 × diameter). No other pocket |
| Narrowest slot | The clevis gap, 20.96 mm wide and about 40 mm deep: a Ø12 tool passes with 4.5 mm a side |
| Undercuts | The slope under the lugs (Face20) cannot be seen from the top; it is cut from below in setup 1. The inner bore chamfers cannot be seen from any axis direction |
| Minimum wall | Each lug is 7.6 mm thick. Nothing thinner; no enclosed void |
| Lug-bore access | Along ±y only. The bore mouths sit 37–72 mm below part surfaces a holder must clear (section 5) |

## 2. Stock, coordinate systems and setups

**Stock.** One block for setups 1 and 2: the part's bounding box plus 3 mm in x and y, 2 mm under the base
bottom and a 10 mm grip band beyond the lug tips: **114.3 × 184.5 × 74.5 mm**. The part is 29 % of that volume.

**Work coordinate system.** Every setup keeps the CAM-frame origin: the deck-frame origin turned with the part,
about 2.3 mm from the B2 bolt axis, with z = 0 on the base bottom. Each setup turns the part about the x axis so its tool direction becomes
+z. The G-code uses `G54`; **the offsets are not probed or transferred between setups here** (section 8).

| Setup | Tool approaches from | Turn about x | Workholding (assumed) | Datum the setup relies on |
| --- | --- | --- | --- | --- |
| 1 `op10` | −z (underside up) | 180° | Vise on the 10 mm grip band of stock beyond the lug tips | Sawn block faces |
| 2 `op20` | +z (top) | 0° | Soft jaws on the two flat base end faces (+y and −y), gripping z 3–18 mm; base bottom on parallels | Base bottom and outline from setup 1 |
| 3 `op30` | +y (pin side) | 90° | Angle plate on the base bottom, bolted through the four finished counterbores | Base bottom and bolt holes |
| 4 `op40` | −y (pin side) | −90° | As setup 3, part turned end for end | As setup 3 |

- **Why the soft jaws grip the ends.** The −x side overhangs above z 11.6 mm (the slope under the lugs), so
  jaws on the long sides would have less than 12 mm to hold. The two end faces are flat, parallel, 178.5 mm
  apart and 23.3 mm tall.
- **Setup transfer.** Setup 2 starts with setup 1's grip band still on the part, so its stock is 10 mm proud of
  the lug tips. Setups 3 and 4 start from the **in-process stock**: the finished part with the two lug bores
  still solid. In the GUI that is Job → Stock → **Use Existing Solid**.

## 3. Tools, feeds and speeds

| T | ToolBit | Ø | Flute / length | Used for |
| --- | --- | --- | --- | --- |
| T1 | `12mm_Endmill_L45` | 12 | 45 / 75 mm, 4 flutes | Roughing, outline contour, counterbores, lug bores |
| T2 | `8mm_Endmill_L30` | 8 | 30 / 60 mm, 4 flutes | Bolt holes |
| T3 | `6mm_Ball_L45` | 6 | 45 / 70 mm, 2 flutes | Finishing |
| T4 | `4mm_Ball_L45` | 4 | 45 / 70 mm, 2 flutes | Counterbore floors (R2.54), bore chamfers |

The ball ends are modelled straight to 45 mm. Physically they are necked long-reach tools.

**Feeds and speeds are shop assumptions, not vendor data.** They assume coated solid carbide and flood coolant
on a generic vertical machining centre capped at 12,000 rpm. Spindle speed is the cutting speed over π × Ø; feed
is rpm × flutes × feed per tooth; plunge is a third of the feed. **Replace them with the chosen tool vendor's
figures before cutting metal.**

| Material | Cutting speed (m/min) and feed per tooth (mm): rough / holes / finish / small ball |
| --- | --- |
| Ti-6Al-4V | 45, 0.05 / 40, 0.03 / 60, 0.04 / 50, 0.025 |
| Al 7075-T651 | 350, 0.08 / 250, 0.05 / 400, 0.06 / 350, 0.04 |
| Al 6061-T651 | 400, 0.08 / 300, 0.05 / 450, 0.06 / 400, 0.04 |
| 17-4PH H1025 | 70, 0.05 / 60, 0.03 / 90, 0.04 / 80, 0.025 |
| AISI 4140 Q&T | 110, 0.06 / 90, 0.04 / 130, 0.05 / 110, 0.03 |

The posted G-code is for **Ti-6Al-4V**, the challenge baseline:

| Tool | rpm | Feed (mm/min) | Plunge (mm/min) |
| --- | --- | --- | --- |
| T1 Ø12 endmill | 1,194 | 239 | 80 |
| T2 Ø8 endmill | 1,592 | 191 | 64 |
| T3 Ø6 ball | 3,183 | 255 | 85 |
| T4 Ø4 ball | 3,979 | 199 | 66 |

The same table for the other four materials is in `assessment.json` (`feeds_by_material`). Both aluminium cards
hit the 12,000 rpm cap on the ball ends.

## 4. Manual steps (FreeCAD 1.1.3 GUI)

Repeat A–E for each setup, with the rows of section 2 and the operations below.

**A. Model and job**

1. Open `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`. In the **Part** workbench, copy `Bracket`, then
   Edit → Placement: rotate −1.7351° about z through (−20.974, −74.760, 0), then by the setup's angle about x.
2. Switch to the **CAM** workbench. CAM → **Job**, with the turned copy as the model.
3. Job → **Setup** tab → Stock: *Create Box from Base Extent*, with the extensions of section 2. For setups 3 and
   4 use *Use Existing Solid* with the in-process solid.
4. Job → **Output** tab: post processor `refactored_linuxcnc`, output file `opNN.ngc`.
5. Job → **Tools** tab: remove the default tool. Add T1–T4 from `tooling/Bit/ge_manual/` and enter the rpm, feed
   and plunge of section 3.

**B. Operations.** Edit → Preferences → CAM → **Enable experimental features** turns on 3D Surface.

| Setup | Operation | Tool | Settings |
| --- | --- | --- | --- |
| 1 | **Rough**: 3D Surface, no faces selected | T1 | Bound box *Stock*; multi-pass, step down 2 mm; step over 40 %; depth offset 0.5 mm; final depth −36.9 |
| 1 | **Finish**: 3D Surface | T3 | Bound box *Stock*; single pass; step over 10 %; sample interval 0.2 mm; final depth −36.9 |
| 1 | **Outline**: Profile, no faces selected | T1 | Side *Outside*; start 0, final −36.9, step down 6 mm |
| 1 | **Bolt holes**: Helix on the four hole walls | T2 | Start 0, final −8.1 |
| 2 | **Rough**: 3D Surface | T1 | As setup 1, final depth 18.5 (the jaws reach z 18) |
| 2 | **Finish**: 3D Surface | T3 | As setup 1, final depth 18.5 |
| 2 | **Finish cross**: 3D Surface | T3 | As Finish, cut pattern angle 90° |
| 2 | **Counterbores**: Helix on the four Ø21.08 walls | T1 | Start 25.5, final 10.45 |
| 2 | **Counterbore floors**: 3D Surface on the eight seat faces and four R2.54 blends | T4 | Multi-pass, step down 0.5 mm; step over 8 %; start 10.95, final 7.8486 |
| 3 | **Lug bores**: Helix on one bore face | T1 | Start 1 mm above the +y lug face; final 0.5 mm past the far lug |
| 3, 4 | **Bore chamfer**: 3D Surface on the outer chamfer facing the tool | T4 | Step over 8 %; sample interval 0.15 mm |

Five settings matter, and each was a fault before it was fixed:

- **A whole-model 3D Surface must use bound box *Stock*.** With *BaseBoundBox* the operation fails with
  `BRep_API: command not done` and leaves an empty path, while the job still looks clean.
- **Do not create a 3D Surface with an empty face list by mistake.** It machines the whole model.
- **One raster pass leaves up to a step-over of stock on walls parallel to its lines.** That is why setup 1
  has the Outline contour and setup 2 the second finishing pass at 90°.
- **The Bore chamfer operations use bound box *Stock*.** With *BaseBoundBox*, 3D Surface cuts the stock by the
  model's envelope, and FreeCAD crashed (segmentation fault) on setup 4, where the stock is the finished part.
- **The in-process solid must overlap the lugs.** A bore plug flush with the chamfer circle, within the working
  copy's 0.01 mm tolerance, fused into an invalid solid with one bore left open; the stock check then read
  449 mm² of gouge before any cutting. The plugs are 0.5 mm larger than the chamfer, and the script stops if the
  stock is not one valid solid.

**C. Recompute and inspect.** Select the Job and recompute. Every operation must show a path; an operation with
no path is a failure, not a pass. Check the paths against the stock and the workholding by eye.

**D. Sanity check and post.** CAM → **Check the CAM job for common errors**, then CAM → **Post Process**.

**E. Simulate.** CAM → **CAM Simulator**, and look for stock left on the part and cuts into it.

## 5. Results per setup

| Setup | Operations | G-code lines | Finished of the area it can see | Gouge (mm²) | Rapids through stock | Workholding hits |
| --- | --- | --- | --- | --- | --- | --- |
| 1 `op10` | Rough, Finish, Outline, Bolt holes | 23,400 | 96.9 % | 0 | 0 | 0 |
| 2 `op20` | Rough, Finish, Finish cross, Counterbores, Counterbore floors | 83,534 | 71.4 % | 0 | 0 | 0 |
| 3 `op30` | Lug bores, Bore chamfer | 426 | (in-process stock) | 0 | 0 | 0 |
| 4 `op40` | Bore chamfer | 393 | (in-process stock) | 0 | 0 | 0 |

- **Every operation recomputed to a valid, non-empty path.**
- **"Finished"** means the simulated stock is cleared to within 0.4 mm of the surface (0.2 mm simulation grid).
  Setup 2 reads 71 % because it stops at z 18.5, above the jaws; setup 1 finishes the walls below that.
- **Two independent stock checks agree** on setups 1 and 2: FreeCAD's `PathSimulator` (96.9 % and 71.4 %) and a
  z-map replay written for this study (96.7 % and 71.9 %). Setups 3 and 4 use the z-map only (section 6).
- **Sanity Check** reports only unused tool controllers, "the Job has not been post-processed" (it runs before
  the post) and "consider specifying the stock material".
- **G-code:** `out/ge_manual_cam/op10.ngc` (SHA-256 `555017f7…`), `op20.ngc` (`dd7d1e5f…`), `op30.ngc`
  (`9fd9752b…`), `op40.ngc` (`800f0164…`). LinuxCNC dialect. **Not run on a controller or a machine.**
- **Views:** `opNN_setup.png` shows the part, stock, coarse workholding boxes and every toolpath per setup;
  `readiness_map.png` colours each face by its status. These are script renders, not GUI screenshots.

**Tool reach.** For each operation: the stick-out a Ø30 holder nose needs to clear the part at the deepest cut.

| Setup | Operation | Tool | Stick-out needed (mm) | × diameter | Within the modelled 45 mm |
| --- | --- | --- | --- | --- | --- |
| 1 | Rough / Outline | Ø12 endmill | 36.4 / 36.9 | 3.0 / 3.1 | yes |
| 1 | Finish | Ø6 ball | 36.9 | **6.1** | yes |
| 1 | Bolt holes | Ø8 endmill | 8.1 | 1.0 | yes (30 mm) |
| 2 | Rough | Ø12 endmill | 43.5 | 3.6 | yes |
| 2 | Finish, Finish cross | Ø6 ball | 44.0 | **7.3** | yes, by 1 mm |
| 2 | Counterbores | Ø12 endmill | 17.4 | 1.5 | yes |
| 2 | Counterbore floors | Ø4 ball | 24.7 | **6.2** | yes |
| 3 | Lug bores | Ø12 endmill | **73.7** | **6.1** | **no** |
| 3, 4 | Bore chamfer | Ø4 ball | **71.6 / 71.8** | **18** | **no** |

Above 6 × diameter a cut is treated as unverified without vendor data or a trial: deflection and chatter are not
simulated.

## 6. The setup 2 "gouge", and what the simulator can and cannot check

The 21 Sep review recorded 31,634 mm² of sampled gouge on setup 2 and asked for a diagnosis. On the current part
the same check first read 24,158 mm². **It was a fault in the check, in two places. The toolpath does not gouge.**

1. **`PathSimulator` mis-cuts a long straight move that ramps in z.** 3D Surface writes one such move wherever
   its path crosses a plane. A single 41 mm move along the top slope, from z 62.4 to 50.6, took the simulated
   stock under it down to z 29: 21 mm below the tool. Found by bisecting the roughing moves. Feeding the
   simulator the same move in pieces no longer than its 0.2 mm grid removes the fault: **0 mm² gouge**.
2. **Heights below z = 0 could not register.** The readout started every column at 0, so setups 1, 3 and 4,
   whose stock lies below z = 0, read as uncut. Fixed by measuring from the stock bottom.

After both fixes the two stock checks agree to within 0.5 % of the visible area on setups 1 and 2.

**A limit that stays.** `PathSimulator` takes only the stock's bounding box. It cannot start from the in-process
solid, so on setups 3 and 4 it sees a block and reports almost nothing cleared (7 % and 3 %). Those setups are checked with the z-map replay only, and each is credited only with what it cut itself.

## 7. Readiness by feature

**Ready (simulation)** means line of sight, at least 95 % of the area finished to 0.4 mm, no gouge, and the
feature's tool within its modelled reach. It does not mean ready to cut (section 8).

| Feature | Faces | Area (mm²) | Finished | Cut in | Status |
| --- | --- | --- | --- | --- | --- |
| Base bottom (mating face) | 1 | 13,998 | 100 % | 1 | ready (simulation) |
| Top and side facets (planes) | 18 | 27,354 | 100 % | 1, 2 | ready (simulation) |
| Base outline corners (R15.24) and end rounds (R12.7) | 10 | 2,667 | 100 % | 1, 2 | ready (simulation) |
| Slope under the lugs (underside only) | 1 | 1,098 | 100 % | 1 | ready (simulation) |
| Bolt holes (Ø10.31; B2 Ø10.67) | 4 | 1,026 | 100 % | 1 | ready (simulation) |
| Counterbore walls (Ø21.08) | 4 | 3,515 | 100 % | 2 | ready (simulation) |
| Nut seats and R2.54 counterbore blends | 12 | 1,428 | 99.8 % | 2 | ready (simulation) |
| Lug tips (R17.78) and arm-root fillets (R3.175) | 6 | 1,921 | 86.8 % | 2 | **unverified** |
| Lug bores (Ø19.11) | 2 | 763 | 100 % | 3 | **unverified** |
| Outer bore chamfers | 2 | 111 | 61 % | 2, 3 | **unverified** |
| Inner bore chamfers (clevis-gap side) | 2 | 111 | 25 % | — | **blocked** |

**Corrective actions**

| Feature | Why | Corrective action |
| --- | --- | --- |
| Inner bore chamfers | No axis-aligned tool has line of sight | A back-chamfer tool through the bore, hand deburring, or drop the chamfer from the machined part. Needs a design decision |
| Lug bores | Boring both lugs from +y needs 73.7 mm of stick-out; the Ø12 tool is modelled to 45 mm | Bore each lug from its own side in setups 3 and 4, which shortens the cut by the 28.6 mm between the lugs (not simulated), or use a Ø16 long-reach tool (4.6 × diameter). A helix-milled bore is also not a toleranced bore: add a boring or reaming pass, and check coaxiality if the lugs are bored from opposite sides |
| Outer bore chamfers | Ø4 ball at 18 × diameter; the 0.64 mm chamfer is below the 0.4 mm check | Replace the ball with a chamfer mill on a Ø12 shank in the same setups; inspect on the part |
| Lug tips | The four arm-root fillets are 100 % finished. The two lug-tip cylinders are 60 %: the outer quadrant below the pin axis (z 36.9–44.7) is seen only from below, and setup 1 stops at z 36.9 | Deepen setup 1 to z 44.7, which needs at least 46 mm of reach, or add a −x setup |

## 8. What this does not establish

These need a machine, a fixture and a programmer's review. **Overall readiness stays conditional on them.**

1. **Holder and shank collisions.** Only a coarse stick-out check with a Ø30 holder nose. No holder model.
2. **Workholding.** The vise, soft jaws and angle plate are coarse boxes. Clamping force, part deflection and jaw
   design are not assessed; setup 2 grips a 15 mm band on a 178.5 mm part.
3. **Work offsets and setup transfer.** No probing cycle, no datum scheme and no tolerance stack across the four
   setups.
4. **Tool deflection, chatter and tool life,** above all the Ø6 ball at 7.3 × diameter and the Ø4 ball at
   6.2 × diameter in Ti-6Al-4V.
5. **Feeds and speeds.** Shop assumptions (section 3).
6. **Surface finish and tolerances.** A 0.6 mm step-over with a Ø6 ball leaves about 0.015 mm of scallop on flat
   faces, by geometry only. No tolerance is checked; the stock check resolves 0.4 mm.
7. **Roughing strategy.** Roughing is a raster 3D Surface in 2 mm layers, chosen because it is what recomputes
   reliably on this solid. An Adaptive clearing pass would load the tool more evenly and is the usual choice.
8. **The G-code itself.** Posted, never run on LinuxCNC or any controller.
9. **The GUI.** The steps in section 4 are what the script does, written as GUI steps. They have not been
   clicked through, and the built-in CAM Simulator has not been replayed by hand.

## 9. Status against the M2A.7 checklist

| Step | Status |
| --- | --- |
| 1. Same geometry in FreeCAD CAM; stock, work coordinate systems, fixture regions, setups and tool approach directions | Done (sections 1 and 2). Work offsets are named, not probed |
| 2. ToolBit library; material-specific feeds and speeds with sources or documented assumptions; diameter, reach, holder clearance, internal radii, deep pockets, lug-bore access, minimum walls, undercuts | Done (sections 1, 3 and 5). Feeds are documented shop assumptions; holder clearance is a coarse check |
| 3. Adaptive/Pocket, Profile and Drilling or boring operations as the features need; recompute and inspect; remaining-stock strategy and setup transfers | Done with 3D Surface, Profile and Helix (sections 2 and 4). **Adaptive is not used** (section 8, item 7); the bores are helix-milled, not bored |
| 4. Post-process with a named postprocessor; replay the simulation; residual stock, gouging and collisions; record what the simulator cannot establish | Done (sections 5, 6 and 8) |
| 5. Screenshots, CAM documents, tool, operation and setup sheets, G-code and simulation evidence; classify every feature; corrective actions | Done (sections 5 and 7), with two gaps: the views are script renders, not GUI screenshots, and FreeCAD's HTML setup sheets were not written in the headless run (the Sanity Check notes are in `opNN.json`) |
| Repeatable manual steps | Written (section 4). **One GUI walk-through is still needed** |

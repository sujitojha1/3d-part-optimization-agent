# GE manual boundary conditions — nut-seat supports and rigid-pin load transfer (M2A.4)

> **3 Oct:** refreshed on **L2**, the mesh frozen by the [M2A.2 convergence study](ge-manual-mesh.md), for the
> current part, `GE_Challenge_Bracket`. Sections 4, 5 and 7 come from the current `out/ge_manual_bcs/bcs.json`;
> the partition (section 2) is unchanged. The smoke test in section 5 is now solved on the current part. The L1
> decks and the Iteration1 smoke test this page held before are in git history.

| | |
| --- | --- |
| Task | M2A.4 ([#62](https://github.com/sujitojha1/3d-part-optimization-agent/issues/62)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19; refreshed 2026-09-23; on L2 2026-10-03 |
| Input | Working copy `data/ge_manual/GE_Challenge_Bracket_manual.FCStd`, SHA-256 `517c9bd7f0f68862b59a1558de05768afb707c10f8a05f3a615ec73cb0fd3b2a`; frozen L2 mesh ([M2A.2 record](ge-manual-mesh.md)); Ti-6Al-4V card ([M2A.3 record](ge-manual-materials.md)) |
| Output geometry | `data/ge_manual/GE_Challenge_Bracket_partitioned.FCStd`, SHA-256 `10e5c43fa30958f088b04507b95d658e9d3049588b91fd71fead68ae4de3b758`. M2A.2 meshes this copy, and every later step uses it |
| Script | `$FEM_PYTHON scripts/ge_manual_bcs.py partition`, then `… setup [--solve]` (the frozen level, L2, by default). It builds the same objects as the manual steps in section 3 and writes `out/ge_manual_bcs/partition.json`, `bcs.json` and three views |
| Status | **Deck setup done, checked and smoke-solved on the current part, on the frozen L2 mesh.** All four supports and both lug bores are in the deck, with no extra restraints, for LC1 and LC4, and both solve and balance the applied force (section 5). **The full force and moment balance is [M2A.6](ge-manual-analysis-report.md)**, and **one GUI walk-through is still needed** |

## 1. Idealisation

| Interface | GE brief ([§2](ge-jet-engine-bracket.md)) | Model here | Restrained / loaded DOF |
| --- | --- | --- | --- |
| 1: pin through both lug bores | Pin Ø 19.05, **infinitely stiff**; all loads applied here | One **rigid body** (`*RIGID BODY`) tying every node on both bore cylinders to a reference node at the pin centreline × clevis midplane | Force on the reference node (ux, uy, uz); moment on the rotation node |
| 2–5: bolts B1–B4 | 0.375-24 bolts, **infinitely stiff**, interfaces **fixed**; nut face Ø 10.287 max ID, Ø 14.173 min OD | **Fixed translations** on the nut-contact patch of each seat: the annulus from the hole edge out to Ø 14.173 | ux = uy = uz = 0 on every patch node. C3D10 nodes have no rotational DOF |

**Interface numbering.** The GE interface graphic labels two corners "Interface 5" ([brief §2](ge-jet-engine-bracket.md)),
so it can't be used to number the bolts. This record uses the `148.fem` RBE2 order, which the
[part record](ge-bracket-part.md) and the [M2A.1 record](ge-manual-geometry.md) also use:
**B1 = Interface 2, B2 = Interface 3, B3 = Interface 4, B4 = Interface 5**.

**Why this support, not SimJEB's.** SimJEB ties each **bolt-hole wall** to a fixed centre node with an RBE2, and
distributes the pin load with an RBE3 ([SimJEB §2](simjeb-dataset.md)). Neither is reused here:

- **Supports.** The workflow asks for fixed **nut-seat patches**. A bore-coupled RBE2 is a different idealisation:
  it loads the hole wall instead of the seat face. It is not adopted here, so there is no comparison to record.
- **Pin.** The GE brief says the pin is infinitely stiff. That is a rigid body. An RBE3 is not rigid: it spreads
  load by weight and doesn't stiffen the bores.

The whole base-top face is **not** fixed. Only the four patches are, and neither the free ring outside Ø 14.173
nor the base bottom (the mating face) is restrained.

## 2. Nut-seat partition

Each seat is a flat annular boss top at z = 7.8486 (above the base bottom), Ø 16.00 outside. The hole is larger
than the nut's maximum ID (section 4 of the [M2A.1 record](ge-manual-geometry.md)). So the nut bears from the
hole edge out to Ø 14.173, and the seat must be split at Ø 14.173.

`partition` imprints four coplanar discs, Ø 14.173, one centred on each bolt axis at the seat height, using
`Shape.generalFuse` with a 1e-4 mm tolerance. The result is checked and must be a single valid solid with an
unchanged volume (463,257.599 → 463,257.576 mm³). The face count goes from 58 to 62. Each seat must split into
exactly one patch and one ring. Because the partition renumbers faces, the Face numbers below apply **only** to
the partitioned copy with the checksum above.

| Bolt (interface) | Axis (x, y) deck | Hole Ø | **Fixed patch** | Area | Free ring (Ø 14.173–16.00) |
| --- | --- | --- | --- | --- | --- |
| B1 (2) | (52.003, 1.512) | 10.3124 | **Face57** | 74.242 mm² | Face56, 43.346 mm² |
| B2 (3) | (−0.044, −0.064) | 10.668 | **Face3** | 68.383 mm² | Face2, 43.346 mm² |
| B3 (4) | (−0.056, −148.189) | 10.3124 | **Face52** | 74.242 mm² | Face51, 43.346 mm² |
| B4 (5) | (38.028, −147.035) | 10.3124 | **Face47** | 74.242 mm² | Face46, 43.346 mm² |

The patch areas match the M2A.1 prediction (74.2 and 68.4 mm²). B2's patch is 8 % smaller because its hole is larger.

**Pin bores.** **Face38** and **Face39**, one bore face per lug (Iteration1 had four, two per lug). The lug-end
chamfer cones are not included.

## 3. Manual steps (FreeCAD 1.1.3 GUI)

**A. Partition (once).**

1. Open `data/ge_manual/GE_Challenge_Bracket_manual.FCStd`, then switch to the **Part** workbench.
2. For each bolt, Part → Primitives → **Circle**, radius **7.0865**, with its centre at the bolt axis from section 2
   and z = **7.8486**, normal +z. Turn each circle into a face with Part → **Shape builder** → Face from edges.
3. Select `Bracket` and the four faces, then Part → Split → **Boolean fragments** (mode Standard).
4. Part → Compound → **Explode compound**. Keep the single solid, name it `Bracket` and delete the rest.
   Copy `PinReference` across unchanged.
5. Check the solid with Part → **Check geometry**. Its volume should be 463,257.58 mm³ and it should have 62
   faces. Save as `GE_Challenge_Bracket_partitioned.FCStd`.

**B. Supports and pin (per load case, on the frozen L2 mesh document from M2A.2).**

1. Open `data/ge_manual/mesh/L2/GE_Challenge_Bracket_mesh_L2.FCStd` and switch to the **FEM** workbench.
2. **Solver.** Select `Analysis`, then Solve → **Solver CalculiX Standard**, with Analysis type **static**.
3. **Material.** Model → Materials → Material for solid, Ti-6Al-4V from the [M2A.3 card](ge-manual-materials.md),
   applied to `Solid1`.
4. **Supports.** Model → Mechanical boundary conditions → **Fixed boundary condition**, four times:
   `Fixed_B1` on Face57, `Fixed_B2` on Face3, `Fixed_B3` on Face52 and `Fixed_B4` on Face47. Pick **only** the
   inner patch; the outer ring must stay free.
5. **Pin.** Model → Mechanical boundary conditions → **Rigid body constraint**, named `Pin`:
   - References: Face38 and Face39.
   - Reference node: **(−20.97366, −74.76046, 44.72459)** mm, which is `PinReference`.
   - Translational mode X/Y/Z = **Load**, and rotational mode X/Y/Z = **Load**.
   - LC1: Force Z = **35585.77 N**, and every other force and moment 0.
   - LC4: Moment Z = **564924.2 N·mm**, and every force 0.
6. Save as `GE_Challenge_Bracket_bcs_L2_<case>.FCStd`, then write the `.inp` from the solver task panel.

Setting a mode to **Load** with value 0 leaves that DOF of the rigid body free. The rigid body is supported only
through the part and the four fixed patches. It must not be set to **Constraint**, which would add a restraint.
M2A.5 adds LC2 and LC3 the same way.

## 4. Deck check

The script reads each exported `.inp` back and compares it with the mesh (`bcs.json`). LC1 and LC4 give the same
sets. Only the `*CLOAD` values differ.

| Check | Result |
| --- | --- |
| `Fixed_B1`–`B4` node sets equal the mesh nodes on each patch face | **Yes**: 244, 261, 244 and 244 nodes (993 in total) |
| Ring nodes fixed, apart from the 60 nodes on the shared Ø 14.173 edge | **0** at every seat |
| Restrained DOFs | `*BOUNDARY` `Fixed_Bn,1`, `,2` and `,3` for each seat: **translations only** |
| Extra `*BOUNDARY` lines | **None**: the deck has exactly the four `Fixed_*` blocks |
| `Pin` node set equals the mesh nodes on both bores | **Yes**: 2,159 nodes, **1,070 and 1,089** per lug |
| Overlap between fixed and pin nodes | 0 |
| Rigid body card | `*RIGID BODY, NSET=Pin, REF NODE=172725, ROT NODE=172726` |
| Reference and rotation nodes | Both at (−20.97366, −74.76046, 44.72459), the pin reference point |
| LC1 loads | `*CLOAD` 172725,3,35585.77; every other component 0; no load on any other node |
| LC4 loads | `*CLOAD` 172726,3,564924.2, a moment about +z on the rotation node; every other component 0 |

Decks: `data/ge_manual/bcs/L2/LC1/LC1.inp` (SHA-256 `91ea964f…8f33e5`) and `…/LC4/LC4.inp` (`46d847ef…ce709c`).
Full checksums are in `bcs.json`. The decks are gitignored because they are derived from licensed CAD.

## 5. Smoke-test solve (L2, Ti-6Al-4V)

Run on `GE_Challenge_Bracket` on 3 Oct with `setup --solve`: CalculiX 2.23 with SPOOLES, on the D-17 Mac.

This only confirms that the setup solves and transfers the load. The formal force **and moment** balance, with
tolerances, is M2A.6.

| Case | ccx | Time | Σ support reactions (N) | Applied |
| --- | --- | --- | --- | --- |
| LC1 | exit 0 | 182.7 s | (0.000, −0.005, **−35,585.769**) | Fz +35,585.77 N |
| LC4 | exit 0 | 173.7 s | (−0.001, 0.000, 0.000) | Mz +564,924.2 N·mm |

Reactions per seat (N):

| Seat | LC1 (Fx, Fy, Fz) | LC4 (Fx, Fy, Fz) |
| --- | --- | --- |
| B1 | (+7, +2,650, **+8,188**) | (+1,693, −512, −605) |
| B2 | (−339, +12,111, −25,803) | (+1,925, +395, +607) |
| B3 | (−11, −9,906, −23,626) | (−1,797, +256, −802) |
| B4 | (+344, −4,855, **+5,655**) | (−1,821, −139, +800) |

**LC4 moment transfer.** The rigid body carries the moment. The seats react it mostly as an in-plane couple, with
net force zero. A rough check takes each seat's resultant at its bolt axis and ignores the moment each patch
carries itself. That gives Mz = −568,405 N·mm about the pin reference point. It opposes the applied +564,924 N·mm
and matches it within 0.6 %. The same rough check leaves about 1×10⁵ N·mm of My in LC1, which is the moment
carried within each patch. That's why the exact check in M2A.6 needs nodal reactions, not resultants.

**Displacement at the pin (LC1).** The reference node moves (0.079, −0.001, 0.164) mm.

## 6. Singularity risks and idealisation limits

These zones must be defined as exclusions for "stress away from singularities" in M2A.6. Raw peaks are still reported.

1. **Patch edge at Ø 14.173.** A fixed region next to a free one is a stress singularity: the peak there keeps
   growing as the mesh is refined. It also sits on the hole edge, where the patch meets the bolt-hole wall.
2. **Rigid bore boundary.** The rigid body keeps the bores from ovalising, and at the lug faces the rigid bore
   edge meets the free chamfer. Peaks at the bore ends are artefacts. The bore stiffness is also overstated.
3. **Bonded pin, no contact.** The rigid body carries tension and compression all round the bore. A real pin
   bears only on one side, with 0.0635 mm diametral clearance. Bearing stress in the lugs is spread out, not
   concentrated.
4. **Patches carry uplift.** In the LC1 smoke test, B1 and B4 react **+z** (up). A nut can only push down on its seat. In the
   real joint, that load goes through the base bottom bearing on the engine, which is not modelled. Stress near
   B1 and B4 under LC1 is therefore not physical.
5. **No bolt preload, no shank bearing.** LC4's in-plane seat forces would really go through friction and the bolt
   shanks. Here they go through the fixed patch.
6. **Mesh convergence.** The [mesh record](ge-manual-mesh.md), section 6, shows the peaks at items 1–2 do not
   converge (the raw LC3 peak moves 29 % between L2 and L3r), and that the stress just outside a 10 mm bolt zone
   is still the tail of the patch-edge singularity. Use a plan exclusion radius about each bolt axis and the
   bores. M2's LC1 used 10 mm; [M2A.6 §5](ge-manual-analysis-report.md) shows 12 mm is needed on this part.

## 7. Files and views

- `out/ge_manual_bcs/partition.json`: partition method, volumes, patch and ring faces, pin bores, reference point.
- `out/ge_manual_bcs/bcs.json`: per level and case, the deck checksum, node-set checks, cards, loads and solve summary.
- `out/ge_manual_bcs/bcs_iso.png`, `bcs_top.png`, `bcs_front.png`: fixed patches in red, free rings in orange,
  rigid-pin bores in blue, and the pin reference point with the LC1 arrow. In the top view, B3's label covers B4's.
- `data/ge_manual/bcs/L2/<case>/`: `GE_Challenge_Bracket_bcs_L2_<case>.FCStd`, `<case>.inp` and `solve/` (deck, `.dat`, `.frd`).

`bcs.json` also keeps the superseded L1 deck record. Only the frozen level, L2, is current.

## 8. Status against the M2A.4 checklist

| Step | Status |
| --- | --- |
| 1. Interfaces 2–5 annotated; nut patches from the GE annulus, intersected with the real holes; partition; base top not fixed | Done (sections 1 and 2; views in section 7) |
| 2. Fixed translation at the four patches; restrained DOFs recorded; bore-coupled support not reused | Done (sections 1 and 4) |
| 3. Rigid pin across both bores, reference at centreline × midplane, load through the reference point; LC4 moment transfer | Done on the current part (sections 3–5). The rough moment check is in section 5; the exact balance is M2A.6 |
| 4. Faces, node sets, reference coordinates, coupling, screenshots, deck cards; all supports and both bores present; no extra restraints | Done (sections 2, 4 and 7). **One GUI walk-through is still needed** to confirm section 3 as written; the numbers come from the script |
| Singularity risks at idealised supports and the rigid pin | Done (section 6) |

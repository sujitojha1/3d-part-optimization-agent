# GE manual load cases — four independent static cases (M2A.5)

> **4 Oct:** refreshed on the repaired source (M2A.8, [#66](https://github.com/sujitojha1/3d-part-optimization-agent/issues/66))
> and its re-frozen **L2** mesh. Sections 3 and 4 come from the current `out/ge_manual_loads/loads.json`. Earlier
> versions are in git history.

| | |
| --- | --- |
| Task | M2A.5 ([#63](https://github.com/sujitojha1/3d-part-optimization-agent/issues/63)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19; refreshed 2026-09-23; on L2 2026-10-03; on the repaired source 2026-10-04 |
| Input | Frozen L2 mesh document `data/ge_manual/mesh/L2/GE_Challenge_Bracket_mesh_L2.FCStd`, SHA-256 `eebb77eb…e7a3f62d` ([M2A.2](ge-manual-mesh.md)); Ti-6Al-4V card ([M2A.3](ge-manual-materials.md)); nut-seat supports and rigid pin ([M2A.4](ge-manual-boundary-conditions.md)) |
| Script | `$FEM_PYTHON scripts/ge_manual_loads.py [--solve]`. It builds the four setups as in section 2, checks each deck and writes `out/ge_manual_loads/loads.json` plus one view per case |
| Status | **Four decks done, checked and smoke-solved on the current part, on the frozen L2 mesh.** All four reproduce the table vectors on the pin reference point, with no other loads or restraints, and are identical apart from their load cards (`all_checks_pass: true`). All four solve and balance the applied force (section 4). **The force and moment balance with tolerances is [M2A.6](ge-manual-analysis-report.md)** |

## 1. Load cases

Sources: [GE brief §3](ge-jet-engine-bracket.md) and [SimJEB §2](simjeb-dataset.md), the `148.fem` FORCE and MOMENT
cards. Each case is applied **on its own**, and all are static.

| Case | GE brief | Force (N) | Moment (N·mm) | Magnitude | Direction check |
| --- | --- | --- | --- | --- | --- |
| **LC1** vertical | 8,000 lbf up | (0, 0, **+35,585.77**) | 0 | 35,585.77 N | 0.000° from +z |
| **LC2** horizontal | 8,500 lbf out | (**−37,809.9**, 0, 0) | 0 | 37,809.9 N | 90.000° from +z, along −x |
| **LC3** diagonal | 9,500 lbf, 42° from vertical toward out | (**−28,276.2**, 0, **+31,403.9**) | 0 | 42,258.12 N | **42.000°** from +z, horizontal part along −x |
| **LC4** torsion | 5,000 lbf·in about the vertical | 0 | (0, 0, **+564,924.2**) | 564.92 N·m | about +z |

**Frame.** The working copy is already in the SimJEB deck frame ([M2A.1 §3](ge-manual-geometry.md)): +z up, "out"
is −x, and z = 0 is the base bottom. So the vectors go in **unchanged**, and no transform is applied. The pin
axis is (0.0303, −0.9995, 0), 1.73° from y (measured on Iteration1 in M2A.1). As M2A.1 recommended, LC2 and LC3 keep SimJEB's pure −x "out" so the
results stay comparable with SimJEB. Their horizontal component is therefore 1.73° off perpendicular to the pin.

**Load point.** Every case loads the rigid body `Pin` from M2A.4 at the pin reference point
**(−20.97366, −74.76046, 44.72459)**: the pin centreline × clevis midplane. Forces go on the reference node and
the LC4 moment on the rotation node. Both nodes sit at that point. SimJEB's own load node is
(−21.036, −75.065, 44.801), 0.32 mm away and mostly along the pin axis ([M2A.1 §3](ge-manual-geometry.md)).

## 2. Manual setup (FreeCAD 1.1.3 GUI)

Make **four separate documents**, one per case, each from a fresh copy of the frozen L2 mesh document. Don't edit one
case into the next. That way no load can carry over.

1. Open `data/ge_manual/mesh/L2/GE_Challenge_Bracket_mesh_L2.FCStd` and immediately **Save As**
   `GE_Challenge_Bracket_<case>_L2.FCStd`, so the mesh document itself stays unchanged.
2. Add the solver, the Ti-6Al-4V material, `Fixed_B1`–`B4` and the rigid body `Pin` exactly as in
   [M2A.4 §3 B](ge-manual-boundary-conditions.md).
3. In `Pin`, keep every translational and rotational mode on **Load**. Enter only this case's row from section 1:
   - LC1: Force Z = 35585.77 N
   - LC2: Force X = −37809.9 N
   - LC3: Force X = −28276.2 N and Force Z = 31403.9 N
   - LC4: Moment Z = 564924.2 N·mm

   Every other force and moment is **0**.
4. Write the `.inp` from the solver task panel, and check the `*CLOAD` cards against section 3.

## 3. Deck check

Each exported deck is read back (`loads.json`). Every check passes for every case.

| Check | LC1 | LC2 | LC3 | LC4 |
| --- | --- | --- | --- | --- |
| `*CLOAD` on reference node 170952 (DOF 1, 2, 3) | 0, 0, 35585.77 | −37809.9, 0, 0 | −28276.2, 0, 31403.9 | 0, 0, 0 |
| `*CLOAD` on rotation node 170953 (DOF 1, 2, 3) | 0, 0, 0 | 0, 0, 0 | 0, 0, 0 | 0, 0, 564924.2 |
| Equal to the section 1 vector | yes | yes | yes | yes |
| Loads on any other node | none | none | none | none |
| Both nodes at the pin reference point (to 1e-6 mm) | yes | yes | yes | yes |
| Constraints in the Analysis | 4 Fixed + 1 Rigid body | same | same | same |
| Extra `*BOUNDARY` lines | none | none | none | none |
| Support and pin node sets as in [M2A.4 §4](ge-manual-boundary-conditions.md) (983 fixed, 2,159 pin) | yes | yes | yes | yes |

- **Units.** The FreeCAD writer uses mm, N and tonne. The `*CLOAD` values are in N on the reference node and in
  N·mm on the rotation node, the same numbers as the table.
- **Decks match apart from their loads.** With the `*CLOAD` cards and `**` comment lines removed, all four decks
  are byte-identical. They have the same nodes, elements, material, supports, rigid body, step and outputs. Only
  the load differs.
- **The mesh document is untouched.** Its SHA-256 is the same before and after the run (`eebb77eb…`).

Decks: `data/ge_manual/loads/L2/<case>/<case>.inp`. SHA-256 prefixes: LC1 `29f0c3fd`, LC2 `ce6ef09d`,
LC3 `6e165696`, LC4 `c4d4cbac`. The full values are in `loads.json`. The decks are gitignored because they are
derived from licensed CAD.

## 4. Smoke-test solve (L2, Ti-6Al-4V)

Run on `GE_Challenge_Bracket` on 4 Oct with `--solve`: CalculiX 2.23 with SPOOLES on the D-17 Mac; ccx exit 0 for
every case, 162–201 s each.

| Case | Σ support reactions (N) | Σ + applied (N) | Pin reference displacement (mm) | Pin rotation (rad) |
| --- | --- | --- | --- | --- |
| LC1 | (0.000, −0.001, −35,585.776) | (0.000, −0.001, −0.006) | (0.0790, −0.0013, **0.1637**) | (0.0000, 0.0027, 0.0000) |
| LC2 | (37,809.901, 0.000, 0.010) | (0.001, 0.000, 0.010) | (**−0.1050**, 0.0034, −0.0839) | (0.0000, −0.0023, −0.0001) |
| LC3 | (28,276.201, 0.000, −31,403.899) | (0.001, 0.000, 0.001) | (−0.0088, 0.0014, **0.0817**) | (0.0000, 0.0007, 0.0000) |
| LC4 | (−0.001, 0.000, 0.000) | (−0.001, 0.000, 0.000) | (0.0008, −0.0045, 0.0003) | (−0.0004, 0.0000, **0.0013**) |

Reactions per seat (N):

| Seat | LC1 | LC2 | LC3 | LC4 |
| --- | --- | --- | --- | --- |
| B1 | (13, 2,653, +8,184) | (9,727, 9,455, −15,056) | (7,286, 9,412, −4,038) | (1,692, −511, −605) |
| B2 | (−342, 12,104, −25,795) | (10,320, −8,381, +15,236) | (7,416, 4,414, −11,370) | (1,926, 394, +607) |
| B3 | (−29, −9,904, −23,623) | (8,687, 5,919, +13,777) | (6,471, −4,313, −10,543) | (−1,799, 256, −802) |
| B4 | (358, −4,854, +5,649) | (9,076, −6,992, −13,957) | (7,103, −9,513, −5,453) | (−1,819, −138, +800) |

- **The load reaches the supports.** In every case the four seats balance the applied force to within 0.010 N.
  The moment balance needs nodal reactions and is done in M2A.6.
- **LC4 torque goes through the pin.** The rotation node carries the full 564,924.2 N·mm. The pin twists
  1.32×10⁻³ rad about z, and the seats react with a zero-sum set of in-plane forces, i.e. a couple. The rough
  moment check in [M2A.4 §5](ge-manual-boundary-conditions.md) puts that couple within 0.6 % of the applied torque.
- **LC1 and LC4 match M2A.4 exactly.** The setup is the same, so the reactions and displacements are identical.
- **Uplift at some seats.** Some seats react +z on the part: B1 and B4 in LC1, B2 and B3 in LC2, B2 and B4 in
  LC4. For that, the nut would have to pull the seat up, which a nut can't do. LC3 has none. [M2A.4 §6](ge-manual-boundary-conditions.md) explains why this is an
  idealisation, since the base bottom bearing on the engine isn't modelled.

## 5. Views

`out/ge_manual_loads/LC1.png` … `LC4.png`. Each has an isometric view and a front x–z view with a grid and axes.
Fixed patches are red and pin bores blue. The black sphere is the pin reference point. Forces are a green arrow
along the vector, labelled with its components. LC4 is a purple +z axis arrow with a counter-clockwise arc seen
from +z. The front views show LC2 and LC3 pointing toward −x, which is the lug side, i.e. "out".

## 6. Status against the M2A.5 checklist

| Requirement | Status |
| --- | --- |
| Full model in the SimJEB frame (+z up, out −x); transform recorded if needed | Done. No transform is needed; the working copy is in the deck frame (section 1) |
| Four separate analyses or decks sharing geometry, material and supports | Done: four documents and decks, identical apart from `*CLOAD` (section 3) |
| Each case independent, with no load accumulation | Done. Each is built from a fresh mesh document, and each deck carries only its own vector (section 3) |
| Signs, units, load point and coupling cards checked against the table | Done (section 3) |
| Arrow and axis screenshots | Done (section 5) |
| LC4 torque transferred through the pin | Done on the current part (sections 3 and 4) |
| Setup reproducible by hand | **One GUI walk-through is still needed** to confirm section 2 as written; the numbers come from the script |

Only the frozen level, L2, is used ([mesh record](ge-manual-mesh.md), section 6).

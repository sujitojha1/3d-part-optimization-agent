# The D-06 label chain into the CalculiX deck (M2.4)

| | |
| --- | --- |
| Task | M2.4 ([#47](https://github.com/sujitojha1/3d-part-optimization-agent/issues/47)) · [plan](plan.md) step 4 |
| Date | 2026-09-21 |
| Part | The parametric `ge_bracket` ([frozen record](ge-bracket-part.md)), at the baseline and at every parameter's min and max |
| Mesh | D-24 sizing frozen in [M2.3](ge-bracket-mesh.md): max 4.0 / min 1.0 / MeshRegion 1.5 / curvature 8 |
| Scripts | `vendor/fem-env/bin/python scripts/ge_bracket_labels.py` (13 points, about 2 min 40 s) and `scripts/ge_bracket_check.py --corners` (77 CAD points, about 1 min 26 s) |
| Status | **Answered, and the answer is the fallback.** Face predicates survive at every bound. FEM Mesh Groups reach the `.unv` and the `FemMesh` intact, but **no D-06 label reaches the ccxtools deck at all**, and even the group-enabled deck gives overlapping node sets and surface-element sets, never a volume partition. D-06's element-centroid fallback is implemented and holds at all 13 points |

**No CadQuery.** The task's original wording says "CadQuery tags"; that predates D-04 (v0.5), which keeps
FreeCAD. Nothing here uses CadQuery and nothing is planned to.

## 1. The chain, and where it breaks

```
geometric predicate -> face -> FEM Mesh Group -> Gmsh Physical Surface
    -> .unv group -> FemMesh group -> [ BREAKS HERE ] -> .inp element set
```

| Link | Holds? | Evidence |
| --- | --- | --- |
| predicate → exactly one face, at every bound | **yes** | 77 CAD points below, and the 13 points re-check it before meshing |
| face → D-06 region, exactly one per face | **yes** | every face labelled, no face in two regions, at all 13 points |
| Mesh Group → Gmsh → `.unv` → `FemMesh` | **yes** | all five regions arrive as `<region>_Nodes` and `<region>_Faces` |
| `FemMesh` group → **ccxtools deck** | **no** | zero D-06 sets in the deck, at all 13 points |
| `FemMesh` group → deck via `writeABAQUS(…, True)` | partly | all ten sets arrive, but they are node and **surface**-element sets |
| any group → a volume partition of the part | **no** | no group has element type `Volume`; 0 of 62,228 C3D10 elements are in one |

## 2. Face predicates at parameter bounds

`scripts/ge_bracket_check.py --corners`, rerun 21 Sep on the current part: **77 points pass** — the
baseline, each of the six parameters alone at its min and max, and all 2⁶ = 64 bound corners. At each
point the shape is one valid solid, every single-face predicate matches exactly one face
(REQ-OPT-008), every face carries exactly one D-06 label, and no thin section drops below 1.27 mm.
Recorded in `out/ge_bracket/check.json`.

The topological-naming risk this task exists for **does not bite**: the predicates are geometric and
are re-run after every recompute, and the face count moves under them without breaking the match —
65 faces at the baseline, 67 at `arm_root_fillet=max`, where OCC adds the two corner blends the
[part record](ge-bracket-part.md) section 7.5 describes. The `fillet_corner` **set rule** absorbs
them into `arm_root_fillet`, which is why the label count stays right while the face count does not.

## 3. The mesh groups themselves

Five FEM Mesh Groups, one per D-06 region, referencing the predicate-selected faces, with
`UseLabel = true` so the region name is what Gmsh and the `.unv` carry. They survive meshing at every
point. At the baseline:

| Region | Faces | Surface elements | Nodes | Fallback C3D10 (section 5) |
| --- | --- | --- | --- | --- |
| `pin_bore` | 2 | 1,024 | 2,208 | 2,601 |
| `clevis_arm` | 10 | 3,762 | 7,856 | 11,226 |
| `arm_root_fillet` | 8 | 2,838 | 6,066 | 14,083 |
| `base_plate` | 37 | 9,634 | 19,612 | 32,695 |
| `bolt_boss` | 8 | 666 | 1,478 | 1,623 |

**Surface elements partition the surface**: the five sets are pairwise disjoint and together cover all
17,924 Triangle6 elements, at every one of the 13 points.

**Node sets overlap, and must.** 1,384 nodes at the baseline lie in two regions — 320 on
`pin_bore|clevis_arm`, 348 on `clevis_arm|arm_root_fillet`, 432 on `arm_root_fillet|base_plate`,
284 on `base_plate|bolt_boss` — because a node on the edge between two regions belongs to both. The
overlap is 1,336–1,444 nodes across the 13 points. This is the "overlapping surface-node regions" the
[21 Sep audit](progress-review-2026-09-21.md) flagged, and it is not a defect to fix: it is what node
sets on a shared boundary are. It does mean **a node set cannot answer "which region is the peak in"**
without a tie-break, which is the second reason the fallback exists.

## 4. What reaches the deck

**Through ccxtools — nothing.** At all 13 points the LC1 deck contains exactly these sets:

```
Eall, MaterialSolid, Fixed_bolt_hole_2..5, Pin, Pin_RefNode, Pin_RotNode
```

`Eall` and `MaterialSolid` are the whole part; the rest come from the constraints. **No D-06 label is
present.** The cause is not configuration and not the geometry: FreeCAD 1.1.3 hard-codes it in
`vendor/fem-env/Mod/Fem/femsolver/calculix/write_mesh.py`:

```python
element_param = 1      # highest element order only
group_param = False    # do not write mesh group data
```

The script reads that literal out of the installed source at run time and records it
(`ccx_writer_group_param` in `labels.json`), so the finding cannot go stale silently against a
FreeCAD upgrade.

**Through `FemMesh.writeABAQUS(path, 1, True)` — all ten sets.** The same mesh written directly, with
group data on, carries `arm_root_fillet_Nodes`, `arm_root_fillet_Faces` and the eight others, at every
point. So the information is in the `FemMesh`; only ccxtools' writer drops it. But what arrives is
`*NSET`s that overlap (section 3) and `*ELSET`s of **surface** elements. Neither labels a single one
of the part's 62,228 volume elements, so neither can answer REQ-OPT-002's question about where a
result lives.

## 5. D-06's fallback: element-centroid membership

D-06 names the fallback and this implements it. Every C3D10 element's corner centroid is matched to
the closest surface triangle (VTK cell locator), and takes that triangle's region. The labels still
originate at the geometric predicate — the surface triangles come from the D-06 mesh groups — and the
result is a partition **by construction**: one closest cell per element gives disjointness, and every
element has one, which gives exhaustiveness.

At all 13 points: **exhaustive** (labelled = `VolumeCount`), **disjoint** (no element in two regions),
and **every region non-empty**. The script writes it as an `.inp` include, one `*ELSET` per region:

```
*ELSET,ELSET=arm_root_fillet
1, 2, 7, 11, …
```

Two honest limits:

1. **Deep interior elements are labelled by proximity, not by meaning.** An element in the middle of
   the base plate gets `base_plate` because that is the nearest surface, which is right; an element
   deep under an arm root gets whichever surface happens to be closest. For the use D-06 has — naming
   the region a *peak* sits in, and peaks sit at surfaces — this is sound. For anything that reasons
   about interior volume it is not, and it should not be quietly reused there.
2. **It is post-processing, not a deck the solver reads.** The `*ELSET`s are written beside the deck,
   not by ccxtools into it. M3.x has to either include them or apply the same labelling to the parsed
   result; this run does not choose between those.

## 6. Every point

All 13 points pass. `grp` is the count of D-06 sets in the group-enabled deck (5 regions × Nodes and
Faces), `ccx` the count in the ccxtools deck.

| Point | Faces | C3D10 | Surface | grp | ccx | Node overlap | Surface overlap | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 65 | 62,228 | 17,924 | 10 | 0 | 1,384 | 0 | ok |
| `base_thickness=min` | 65 | 51,936 | 17,614 | 10 | 0 | 1,348 | 0 | ok |
| `base_thickness=max` | 65 | 70,553 | 17,702 | 10 | 0 | 1,408 | 0 | ok |
| `arm_thickness=min` | 65 | 55,167 | 17,468 | 10 | 0 | 1,344 | 0 | ok |
| `arm_thickness=max` | 65 | 69,687 | 18,992 | 10 | 0 | 1,424 | 0 | ok |
| `lug_wall=min` | 65 | 57,103 | 16,596 | 10 | 0 | 1,336 | 0 | ok |
| `lug_wall=max` | 65 | 70,304 | 19,752 | 10 | 0 | 1,444 | 0 | ok |
| `arm_root_fillet=min` | 65 | 59,169 | 17,234 | 10 | 0 | 1,356 | 0 | ok |
| `arm_root_fillet=max` | **67** | 65,313 | 18,196 | 10 | 0 | 1,436 | 0 | ok |
| `base_pocket_depth=min` | 65 | 63,197 | 17,728 | 10 | 0 | 1,384 | 0 | ok |
| `base_pocket_depth=max` | 65 | 59,196 | 18,252 | 10 | 0 | 1,384 | 0 | ok |
| `centre_hole_diameter=min` | 65 | 63,953 | 18,186 | 10 | 0 | 1,384 | 0 | ok |
| `centre_hole_diameter=max` | 65 | 62,698 | 17,870 | 10 | 0 | 1,384 | 0 | ok |

## 7. What this means for the decisions

1. **D-06 must state that the labels are applied after the solve, not carried in the deck.** The Mesh
   Group route to a CalculiX deck does not exist in FreeCAD 1.1.3, and the group-enabled route gives
   surface sets, not volume sets. The element-centroid fallback is not a contingency here; it is the
   route. M3.1/M3.4 should be written that way rather than discovering it again.
2. **REQ-OPT-002 and REQ-OPT-005 are supportable** — every candidate result can be given an
   exhaustive, disjoint region label — **but only through the fallback**, and REQ-OPT-005's prediction
   scoring must compare labels produced by it, not by node sets.
3. **The topological-naming risk is closed for this part.** 77 CAD points, and 13 of them carried
   through meshing and deck writing.

## 8. What this does not establish

- **No solve.** No `ccx` run, so no result has actually been labelled — only the elements that would
  carry one. M2.5 ([#48](https://github.com/sujitojha1/3d-part-optimization-agent/issues/48)) owns it.
- **One parameter at a time through the mesh.** The 64 bound corners are checked in CAD only; the 13
  meshed points move one parameter each. A corner that breaks only after meshing would not be seen.
- **Nothing about the interior labelling's correctness**, beyond it being a partition — see the two
  limits in section 5.
- **Nothing about the manual M2A study**, which runs on a different part.

## 9. Reproducing

```
vendor/fem-env/bin/python scripts/ge_bracket_check.py --corners     # 77 CAD points
vendor/fem-env/bin/python scripts/ge_bracket_labels.py              # 13 meshed points
vendor/fem-env/bin/python scripts/ge_bracket_labels.py --points baseline arm_root_fillet=max
```

Exit 0 when every point's chain checks pass, 2 otherwise. Each point writes
`out/ge_bracket_labels/<point>/` — the FCStd, Gmsh's working files, the ccxtools deck, the
group-enabled `mesh_groups.inp` and the fallback `d06_elsets.inp` — plus its entry in
`out/ge_bracket_labels/labels.json`. About 430 MB in total; `out/` is gitignored.

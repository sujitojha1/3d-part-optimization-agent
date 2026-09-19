# GE geometry visual comparison — 19 September 2026

**Selected for the manual M2A study: `data/simjeb/Iteration1.stp`.** It is the closest visual match among the seven local files to the stored GE original-bracket image: broad sloped body, continuous four-corner base, twin narrow clevis arms with root gussets, and four recessed bolt locations. This is a qualitative visual selection, not proof of original-file identity or challenge compliance.

Compared with both [GE original image](assets/ge-bracket/original-bracket.png) and [GE load/interface graphic](assets/ge-bracket/load-conditions-and-interfaces.png), already sourced in [the GE brief](ge-jet-engine-bracket.md). No new geometry was downloaded.

## Comparison

| Candidate | Visual assessment |
| --- | --- |
| `Iteration1.stp` | Closest overall; preserves the broad sloped body and narrow gusseted twin lugs. Recess details/fillets still differ from the illustration. |
| `Bracket_Modified_FVZ.stp` | Close second; similar envelope and recessed bolt regions, with altered/sharper transitions around the lug roots and body. |
| `Redesign.STEP` | Similar broad body, but thicker-looking clevis arms and different root/body transitions. |
| `parts/ge_bracket.FCStd` | Simplified parametric rebuild: flatter base, extra centre hole, fewer original-style sloping body features. |
| `148.stp` | Lightweight entry with prominent cutouts; substantially different from the original's solid sloped body. |
| `GENERAL_ELECTRIC_JET_ENGINE_FINAL.stp` | Much narrower, reduced body and prominent separated bolt pads. |
| `TJ_final_GE_bracket.stp` | Sculpted body with deep reliefs/cutouts; less like the original solid body. |

## Method and artifacts

Ran `vendor/fem-env/bin/python scripts/ge_geometry_compare.py`: imported each STEP or opened the existing FCStd without saving modifications, checked B-rep validity and solid count, tessellated for display, and rendered four views per file (isometric, opposite, top, front). All seven imported as valid single solids. The display triangle mesh is not an FEA mesh and its appearance is not a mesh-quality assessment.

The renderer normalizes display orientation using bolt-cylinder and pin-bore axes, and records its rotation/origin. Cameras use parallel projection; each part is independently fitted to the image, so screen size is not a dimension comparison. Approximate axis alignment for display is not the verified solver coordinate transform.

Local generated artifacts (gitignored, regenerate from fetched/local CAD):

- [All-candidate comparison](../out/ge_geometry_comparison/comparison.png)
- [Selected candidate, isometric](../out/ge_geometry_comparison/Iteration1_iso.png)
- [Selected candidate, top](../out/ge_geometry_comparison/Iteration1_top.png)
- [Selected candidate, front](../out/ge_geometry_comparison/Iteration1_front.png)
- [Geometry inventory: checksums, bounds, volume and display transforms](../out/ge_geometry_comparison/geometry-inventory.json)

`Iteration1.stp` SHA-256: `a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e`.

## Still required before analysis

Complete M2A.1: verify source attribution, STEP units, the four nut-seat patches, pin/bolt interface dimensions, and the load coordinate transform. In particular, this STEP is stored in a tilted frame; do not paste SimJEB load vectors into its original axes. Inspect the approximately 9.557 mm pin-bore radius against the GE 9.525 mm radius and document clearance/deviations. The original-envelope match cannot be established from a perspective image. No stress analysis, material assignment or CAM-readiness claim is made by this comparison.

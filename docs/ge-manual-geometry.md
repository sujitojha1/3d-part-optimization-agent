# GE manual geometry — frozen source record (M2A.1)

| | |
| --- | --- |
| Task | M2A.1 ([#59](https://github.com/sujitojha1/3d-part-optimization-agent/issues/59)) · [M2A workflow](ge-manual-workflow.md) |
| Frozen | 2026-09-19 |
| Selected file | `data/simjeb/Iteration1.stp` (gitignored; licensed non-commercial by GrabCAD) |
| SHA-256 | `a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e` (918,340 bytes) |
| Working copy | `data/ge_manual/Iteration1_manual.FCStd`, built from `data/ge_manual/Iteration1_deck_frame.step` (both gitignored) |
| Check | `vendor/fem-env/bin/python scripts/ge_manual_geometry.py` (about 5 min, FreeCAD 1.1.3) → `out/ge_manual_geometry/geometry-check.json` and annotated views |
| Selection basis | [Visual comparison](ge-geometry-comparison.md) of seven local candidates |

The manual M2A study uses exactly one geometry file, the one in the table above. The parametric agent baseline
`parts/ge_bracket.FCStd` ([part record](ge-bracket-part.md)) stays separate and unchanged.

**This file is not GE's original part.** It is a 2013 challenge entry (section 1), selected because it looks
closest to the original. Nothing on this page verifies the original part's envelope, because no reference for it
exists: the challenge's `original.stp` link returns 404 ([GE brief §1](ge-jet-engine-bracket.md)).

## 1. Identity and provenance

| Item | Value | Source |
| --- | --- | --- |
| Design identity | GrabCAD GE challenge entry `ge-engine-bracket-17`, file `Iteration1.stp` | `all_bracket_metadata.tab` row id 474 |
| Attribution | **Kiran Kumar A** (GrabCAD `kiran.kumar.a-1`). CAD licensed for non-commercial use by GrabCAD; the SimJEB metadata is ODC-By (cite Whalen, Beyene & Mueller 2021) | Metadata; [SimJEB README](simjeb-dataset.md) |
| Entry URL | `https://grabcad.com/library/ge-engine-bracket-17` (inferred from the `link_name` column, following the pattern of design 148's README URL; not fetched) | Metadata |
| SimJEB record | id **474**, category `block`, metadata volume 283,997.6 mm³, mass 1.2695 kg (SimJEB's ρ = 4.47×10⁻³ g/mm³), `test_split_2` = True. The same entry also has `Iteration2.stp` (id 476) and `Iteration3.stp` (id 475) | Metadata |
| CAD system | CATIA V5 Release 19 GA, `CATIA V5 STEP AP203`, schema `CONFIG_CONTROL_DESIGN` | STEP header |
| Source revision | Header `FILE_NAME` is `J:\Bracket analysis\new\bracket ITER8.stp`, timestamp **2013-08-07T17:35:35Z** (two days before Phase I closed); product name `Part3`. The internal name "ITER8" and the published name "Iteration1" disagree; no other revision information exists | STEP header |
| Units | Declared `SI_UNIT(.MILLI.,.METRE.)`, distance accuracy 0.005 mm. Cross-check: B-rep volume 283,729.59 mm³ against SimJEB's 283,997.6 mm³ mesh volume (+0.09 %). Inches would be off by 25.4³ | STEP; this check |
| Local acquisition | **Not recorded.** The file appeared in `data/simjeb/` on 2026-09-18 23:45, together with four other candidate STEPs. `scripts/fetch_simjeb.py` does not fetch it. Its tilted native pose and original CATIA header show it is the **raw submission**, not SimJEB's cleaned canonical-pose `474.stp`. Likely sources are `all_uncleaned_cad.zip` or the GrabCAD entry | File mtime; this check |

**Open provenance item.** Record how the file was obtained, including the archive or URL and that archive's checksum,
so it can be re-fetched. Until then, the SHA-256 above is the file's only identity.

## 2. Solid checks

| Check | Result |
| --- | --- |
| B-rep validity (`isValid`) | **Valid** |
| Solids / shells | **1 solid, 1 closed shell**, connected; 399 faces, 1,000 edges |
| BOP checker (`check(True)`) | 194 edges/faces flagged `BOPAlgo_InvalidCurveOnSurface`. The largest vertex/edge tolerance is 0.0049 mm, inside the file's 0.005 mm accuracy. This is typical of a CATIA AP203 export. `isValid` passes, but **M2A.2 should expect meshing to need healing** if Gmsh fails on these edges |
| Volume / area | 283,729.590 mm³ / 80,054.6 mm² |
| Bounding box, native frame | x −164.552…16.496, y −43.617…47.100, z −22.263…89.706 mm |
| Bounding box, deck frame (section 3) | x −40.196…68.469, y −164.676…18.002, z 0…63.577 mm (108.7 × 182.7 × 63.6) |
| Minimum wall (sampled) | **4.66 mm**, 1st percentile 4.74 mm; 0 samples below GE's 1.27 mm minimum feature. Method: an inward ray from each of 149,670 triangle centroids (0.05 mm-deflection tessellation) to the next surface. The thinnest sections are the base end walls near (−14.5, −152.6, 21) and (−14.4, 4.9, 21) in the deck frame. This is an estimate from samples, not an exact B-rep distance |

## 3. Coordinate frame and load transform

**Native frame.** The file is stored tilted. The pin axis lies exactly along native +x, and the base normal (the
bolt axis, oriented toward the pin) is (0, 0.662599, 0.748974). That is 41.50° from native z. **Do not apply SimJEB
load vectors in the native axes.**

**Deck frame.** This is the frame of the SimJEB `148.fem` deck, which fixes the GE load vectors
([SimJEB §2](simjeb-dataset.md)): +z vertical up, "out" is −x, and z = 0 is the base bottom plane. The four bolt axes
were fitted rigidly, in plane, to the deck's RBE2 spider centres (nodes 129261–129264). The fit residuals are
0.07, 0.22, 0.18 and 0.14 mm. The transform is p_deck = R · p_native + t:

```
R = [[ 0.030277763545,  0.748630626819, -0.662295584783],
     [-0.999541523417,  0.022677258094, -0.020062027083],
     [ 0.0,             0.662599371079,  0.748974013866]]
t = [38.027871, -147.035461, 0.0] mm
```

**Independent check.** The deck's RBE3 pin load node (129265) was not used in the fit. It lies at
(−21.036, −75.065, 44.801); this file's pin reference transforms to **(−20.974, −74.760, 44.725)**. The difference
is (0.06, 0.30, −0.08) mm, mostly along the pin axis, which is within SimJEB's stated picking accuracy. The body's
centre of mass sits at x = +19.8, so −x points from the body toward the clevis: "out" is consistent.

**Pin axis is not exactly along y.** In the deck frame the pin axis is (0.0303, −0.9995, 0), 1.73° from y. This
matches the 148 bore and SimJEB's pose. LC2 and LC3's "out" component (−x) is therefore 1.73° off perpendicular to
the pin. M2A.5 should apply the SimJEB vectors unchanged in the deck frame, to stay comparable with SimJEB, and
record this.

## 4. Interfaces against the GE brief

Bolt labels B1–B4 follow the `148.fem` RBE2 order, which is also Interfaces 2–5 in the
[part record](ge-bracket-part.md). M2A.4 assigns the final GE interface numbering.

### Interface 1 — pin and lug bores

| Item | This file | GE brief / reference | Status |
| --- | --- | --- | --- |
| Bore diameter, both lugs | **Ø 19.1135** (0.7525 in), one common axis | Pin Ø 19.05 (0.75 in) | Pin fits: **0.0635 mm diametral clearance** |
| Lug (bore) length | 6.35 each (0.250 in) | — | Matches SimJEB 148 |
| Clevis gap / outer span | 22.225 (0.875 in) / 34.925 (1.375 in) | — | Matches SimJEB 148. The parametric rebuild uses a 21.64 gap |
| Bore centres (deck) | (−21.406, −60.480, 44.725) and (−20.541, −89.041, 44.725) | — | — |
| **Pin reference point** (pin centreline × clevis midplane) | **(−20.974, −74.760, 44.725)** deck; 44.725 above base bottom | RBE3 node (−21.036, −75.065, 44.801) | Load and moment reference for M2A.4/M2A.5 |

### Interfaces 2–5 — bolts and nut seats

| Bolt | Axis (x, y) deck | Hole Ø | Clearance on Ø 9.525 bolt | Nut seat |
| --- | --- | --- | --- | --- |
| B1 (node 129261) | (52.003, 1.512) | 10.3124 (0.406 in) | 0.787 | Face 9, z = 7.849, flat annulus Ø 10.31–16.00, 117.6 mm² |
| B2 (node 129262) | (−0.044, −0.064) | **10.668 (0.420 in)** | **1.143** | Face 10, z = 7.849, flat annulus Ø 10.67–16.00, 111.7 mm² |
| B3 (node 129263) | (−0.056, −148.189) | 10.3124 | 0.787 | Face 11, z = 7.849, flat annulus Ø 10.31–16.00, 117.6 mm² |
| B4 (node 129264) | (38.028, −147.035) | 10.3124 | 0.787 | Face 8, z = 7.849, flat annulus Ø 10.31–16.00, 117.6 mm² |

- **Seats.** Each nut seats on a flat annular boss top, 7.849 mm (0.309 in) above the base bottom. The boss is
  Ø 16.00 OD and sits in a Ø 21.08 recess. The GE nut face (Ø 10.287 max ID, Ø 14.173 min OD) fits inside every
  boss top, with 0.91 mm radial margin to the Ø 16.00 edge. The base bottom (face 381, z = 0, 7,433 mm²) is one
  plane and is the mating face.
- **Contact patch for M2A.4.** Each hole is larger than the nut face's maximum ID, so the nut bears on an annulus
  from the hole edge out to Ø 14.173: **74.2 mm²** at B1, B3 and B4, and **68.4 mm²** at B2. This must be a
  partitioned patch. The boss top as a whole reaches Ø 16.00.
- **Hole diameters: this file versus the rebuild.** GE specifies the bolt (Ø 9.525) and the nut face, not the hole.
  The parametric rebuild uses Ø 10.30 clearance holes throughout, taken from SimJEB. This file has Ø 10.3124 at B1,
  B3 and B4, and **Ø 10.668 at B2**. B2 is a deviation from the other three holes and from the rebuild. It still
  clears the bolt and still carries the GE nut face, but its contact annulus is 8 % smaller.
- **Bolt pattern.** The spacing is **not** a rectangle: B1–B2 is 52.07 mm, B3–B4 is 38.10 mm, B2–B3 is 148.13 mm
  and B1–B4 is 149.20 mm. This is the same pattern as SimJEB's deck; all four holes fit it within 0.22 mm.

### Envelope

Not verified. There is no original-envelope reference. The deck-frame bounding box in section 2 describes this
entrant's design, not GE's envelope.

## 5. Working copy and symmetry

**Working copy.** `data/ge_manual/Iteration1_manual.FCStd` holds:

- `Bracket`: the solid in the deck frame, with an identity Placement;
- `PinReference`: a vertex at the pin reference point.

The script moves the source into the deck frame and writes `Iteration1_deck_frame.step`, reads it back, and saves
the result in the document. It never writes to the frozen source; the checksum is re-verified after the run.

The STEP round trip is deliberate. When the transform is left as a Placement, BRepCheck flags four located chamfer
cones on the lug bores as "Unorientable", although the unlocated source passes. FEM would inherit that located
shape. The round-trip solid is valid, with 399 faces and a volume change of +0.09 mm³ (3×10⁻⁷). It still carries
177 of the BOP curve-on-surface flags, and its largest tolerance is 0.0019 mm. The saved document reopens as
1 valid solid.

| Artifact (this build) | SHA-256 |
| --- | --- |
| `data/ge_manual/Iteration1_deck_frame.step` | `64cb1d948bef97e1880103617188e9b54ad497b91b2fe92500afb8b5182f4142` |
| `data/ge_manual/Iteration1_manual.FCStd` | `fcc77c9841f5b874492c35ac6084ef059a32d3133267d7f36a973dcb63096c8b` |

Both derived files embed timestamps, so re-running the script changes their checksums. Downstream M2A records
should cite the checksum of the working copy they actually used. The stable identity is the source SHA-256.

**Full model required.** The geometry is not mirror-symmetric about the clevis midplane:

- mirrored surface vertices deviate by up to 18.3 mm;
- 66 % of them deviate by more than 0.1 mm;
- the bolt pattern is a trapezoid (52.07 versus 38.10 mm);
- B2's hole is oversize.

LC4's torque about z would be antisymmetric even on symmetric geometry. **Use the full model for all four cases.**

## 6. Annotated views

The views are generated locally and gitignored:

- `out/ge_manual_geometry/interfaces_iso.png`
- `out/ge_manual_geometry/interfaces_top.png`
- `out/ge_manual_geometry/interfaces_front.png`
- `out/ge_manual_geometry/interfaces_side.png`

Each shows the deck frame, the Ø 19.05 pin through both bores with its reference coordinates, each bolt axis with
its hole Ø and seat height, the GE nut-face annulus drawn on each seat, and the −x "out" arrow. In the top view the
B3 label overlaps B4's.

## 7. Status against the M2A.1 checklist

| Step | Status |
| --- | --- |
| 1. Record path, identity, attribution, SHA-256, units, frame, CAD version, revision | Done (sections 1 and 3); local acquisition route is open |
| 2. Validity, connectivity, bbox, volume, minimum walls, four nut/bolt locations, both lug bores, annotated views | Done by script (sections 2, 4 and 6). **A person still needs to open the file in the FreeCAD GUI** to confirm the views and face picks visually; everything here ran headless in FreeCAD 1.1.3 |
| 3. Pin Ø 19.05 and bolt/nut interfaces; 10.30 versus bolt distinction; deviations; envelope not claimed | Done (section 4) |
| 4. Separate working copy, source intact; full model unless symmetry justified | Done (section 5); full model |

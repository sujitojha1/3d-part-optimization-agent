# GE manual materials — five cards, assignment and deck check (M2A.3)

| | |
| --- | --- |
| Task | M2A.3 ([#61](https://github.com/sujitojha1/3d-part-optimization-agent/issues/61)) · [M2A workflow](ge-manual-workflow.md) |
| Date | 2026-09-19 |
| Geometry / mesh | Working copy from [M2A.1](ge-manual-geometry.md), volume **283,729.68 mm³**. L1 mesh from [M2A.2](ge-manual-mesh.md), meshed on the [M2A.4 partitioned copy](ge-manual-boundary-conditions.md): connectivity SHA-256 `342e0de4…280b83`, 90,353 C3D10 elements. First recorded on L2, then re-run on L1 after L2 was dropped |
| Script | `vendor/fem-env/bin/python scripts/ge_manual_materials.py` (about 1 min). It builds the same objects as section 3's manual steps and writes `out/ge_manual_materials/materials.json` |
| Decision | [D-09](requirements.md) names these five alloys and conditions: Ti-6Al-4V annealed, 7075-T6, 6061-T6, 17-4PH H1025, and 4140 quenched and tempered. This page fixes the product form, the governing specification and each value |

**Scope.** GE fixes **Ti-6Al-4V** and additive manufacture ([GE brief §4](ge-jet-engine-bracket.md)), so
Ti-6Al-4V is the **challenge baseline**. The other four are **project comparisons outside the challenge brief**,
chosen as machinable wrought stock for the CNC readiness extension (M2A.7). None of them is "challenge-compliant".

## 1. Cards as used

All properties are room-temperature values, 21–24 °C (70–75 °F). GE's service temperature is 75 °F
(23.9 °C), so no temperature correction applies. Solver units are FreeCAD's CalculiX set: mm, N, s, t, MPa.

| Card | Condition and product form | E (MPa) | ν | ρ (kg/m³) | ρ in solver units (t/mm³) | Yield used (MPa) | Yield basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Ti-6Al-4V** (challenge baseline) | As specified by the GE challenge. D-09 condition: annealed | 113,800 | 0.342 | 4,430 | 4.430E-09 | **903.2** | GE-prescribed, 131 ksi |
| Al 7075-T651 | T651 **plate, 2.501–3.000 in** thick. Solution heat treated, stretched, artificially aged | 71,705 | 0.33 | 2,810 | 2.810E-09 | **421.3** | Specification minimum, 61.1 ksi (AMS-QQ-A-250/12, that thickness) |
| Al 6061-T651 | T651 **plate, 0.250–4.000 in** | 68,948 | 0.33 | 2,700 | 2.700E-09 | **241.3** | Specification minimum, 35 ksi (ASTM B209) |
| 17-4PH H1025 (UNS S17400) | **Bar, AMS 5643**. Condition A (solution treated at 1900 °F) then aged 4 h at 1025 °F and air cooled | 199,948 | 0.272 | 7,806 | 7.806E-09 | **999.7** | Specification minimum, 145 ksi, H1025 |
| AISI 4140 Q&T | **Bar, ASTM A434 Class BD** (hot-wrought, oil quenched and tempered). Stock about 5 in | 199,948 | 0.29 | 7,806 | 7.806E-09 | **689.5** | Specification-minimum floor, 100 ksi. A434 BD's lowest row, covering all sizes to 9.5 in |

**Conversions.**
- 1 ksi = 6.894757 MPa; 1 Msi = 6,894.757 MPa.
- 1 lb/in³ = 27,679.90 kg/m³.
- kg/m³ × 1e-12 = t/mm³.
- Mass (g) = volume (mm³) × ρ (kg/m³) × 1e-6.

### Why these conditions and product forms

- **Stock size decides the minimum for the alternatives.** The part's bounding box is 108.7 × 182.7 × 63.6 mm.
  - Machined from plate, it needs plate thicker than 2.5 in (63.5 mm), so 7075 falls in the **2.501–3.000 in**
    row. That row's minimum yield (421 MPa) is 10 % below the 0.500–1.000 in row (469 MPa).
  - As bar, the section diagonal needs about a 5 in (127 mm) diameter.
- **4140's condition is chosen, not generic.** "4140 Q&T" has no single yield. A434 Class BD's minimum yield falls
  from 130 ksi at 1.5 in and under to **100 ksi at 9.5 in**. The row for 4.0–7.0 in stock could not be read from
  a public source; the standard is paywalled. The floor of 100 ksi is used and is conservative for any size.
- **Minimums, not typical values, for the four alternatives.** The typical values are higher:
  - 7075-T6: 503 MPa;
  - 6061-T6: 270 MPa;
  - 17-4PH H1025: 165 ksi (1,138 MPa).

  Ti keeps GE's prescribed 903.2 MPa, which the challenge fixes; it is not a specification minimum. **So the
  comparison is Ti at GE's value against the others at specification minimum.** State this whenever the
  materials are ranked.

### Ti-6Al-4V density: one source

E, ν and ρ all come from the SimJEB `148.fem` `MAT1` card: 113,800 MPa, 0.342 and **4.43e-9 t/mm³**
([SimJEB §2](simjeb-dataset.md)). This is the D-09 requirement, and it keeps the Ti comparison consistent with
SimJEB's solver. SimJEB's metadata `mass` column uses 4.47e-3 g/mm³ instead (0.9 % heavier: 1,268.3 g for this
volume, against 1,256.9 g). **That density is not used here.** When comparing masses with the SimJEB metadata,
rescale by 4430/4470.

## 2. Sources

| Card | Property | Source | Note |
| --- | --- | --- | --- |
| Ti-6Al-4V | Yield 131 ksi | GE challenge page, "Assume yield strength is 131 ksi" ([brief §4](ge-jet-engine-bracket.md)) | Primary |
| Ti-6Al-4V | E, ν, ρ | SimJEB design 148 deck `148.fem`, `MAT1` (Whalen, Beyene & Mueller, Harvard Dataverse [doi:10.7910/DVN/XFUWJG](https://doi.org/10.7910/DVN/XFUWJG)) | Primary. Local `data/simjeb/148.fem` |
| 7075-T651 | Minimum yield 61.1 ksi and tensile 71.9 ksi for plate 2.501–3.000 in; E 10,400 ksi; ν 0.33; ρ 2.81 g/cm³ (Aluminum Association typical) | Clinton Aluminum, [7075-T6/T651 datasheet](https://www.clintonaluminum.com/wp-content/uploads/2014/08/Grade-7075-Text-data.pdf) | **A reprint in MatWeb format**, which D-09 excludes as a provenance. The thickness row corroborates the tensile minimum only: Smiths, [AMS-QQ-A-250/12 datasheet](https://www.smithmetal.com/pdf/aluminium/us/ams-qqa-250-12.pdf), 72.0 ksi for 2.501–3.000 in, E 72 GPa, ρ 2.81. **Open:** verify 61.1 ksi against AMS-QQ-A-250/12 or ASTM B209 directly |
| 6061-T651 | Minimum yield 35 ksi and tensile 42 ksi; E 69 GPa (10,000 ksi); ν 0.33; ρ 2.70 g/cm³ | [Wikipedia, 6061 aluminium alloy](https://en.wikipedia.org/wiki/6061_aluminium_alloy), citing ASTM B209 | **Secondary.** **Open:** verify the minimum for the chosen plate thickness in ASTM B209 |
| 17-4PH H1025 | Minimum yield 145 ksi and tensile 155 ksi; density 0.2820 lb/in³ | United Performance Metals, [17-4 PH datasheet, AMS 5604/5643](https://www.upmet.com/sites/default/files/datasheets/17-4-ph.pdf) | Producer datasheet; bar up to 5.000 in |
| 17-4PH H1025 | E 29.0 Msi (dynamic, 70 °F), ν 0.272, ρ 0.282 lb/in³, heat-treatment definition, typical yield 165 ksi | Rolled Alloys, [17-4 Stainless data sheet](https://www.rolledalloys.com/wp-content/uploads/17-4_Data-sheet-rolled-alloys.pdf), bulletin 1740USe 12/17 | Producer datasheet. E is the dynamic modulus |
| 4140 Q&T | Class BD minimum yield, 130 ksi (≤ 1.5 in) down to 100 ksi (9.5 in) | ASTM A434, as summarised by [AMS Resources](https://amsresources.com/a-434-steel-bas-alloy-hot-wrought-or-cold-finished-quenched-tempered/) | **Secondary.** **Open:** the size-class row for the stock in the standard itself |
| 4140 Q&T | E 29 Msi (200 GPa), ρ 0.282 lb/in³ | SB Specialty Metals, [4140 HT technical data](https://sb-specialty-metals.com/wp-content/uploads/2022/07/Data-Sheet-4140-HRHT-SBSM.pdf); Eastern Tool Steel, [4140 HT](https://easterntoolsteel.com/4140-ht/) (7,810 kg/m³) | Producer and distributor datasheets |
| 4140 Q&T | ν 0.29 | MW Components, [Alloy Steel Grade 4140 fact sheet](https://www.mwcomponents.com/uploads/Resource-Center/Elgin-Material-Sheets/Alloy-Steel-Grade-4140-Fact-Sheet_Elgin-Website.pdf) ("calculated", "typical for steel") | MatWeb-format reprint; generic for steel |

Everything was accessed 2026-09-19. **Three cards rest partly on secondary or MatWeb-format sources**: the 7075
yield, the 6061 minimums, and the 4140 size row and ν. Each is marked **Open** above. They're good enough for
screening comparisons. They are not design allowables, and they should be checked against the governing
specification before any claim is made about a specific alloy. None of these values is an MMPDS A- or B-basis
allowable.

## 3. Manual assignment (FreeCAD 1.1.3 GUI)

Repeat these steps for each card. Geometry, mesh, supports and loads stay fixed. Only the material changes.

1. **Open the mesh document.** Open the mesh document
   `data/ge_manual/mesh/L1/Iteration1_mesh_L1.FCStd` from M2A.2. Switch to the FEM workbench.
2. **Add the solver.** Select `Analysis`, then Solve → **Solver CalculiX Standard**.
3. **Add the material.** Model → Materials → **Material for solid**.
   - In the task panel, choose any metal as a template, then click **Edit** or open the property editor.
   - Enter the card from section 1: **Young's modulus** in MPa, **Poisson ratio**, **Density** in kg/m³, and
     **Yield strength** in MPa. CalculiX ignores yield, but it records the card.
   - Name it after the card key, for example `Material_ti6al4v`.
4. **Assign it to the whole solid.** In the reference list, click **Add** and pick the solid (`Solid1` of
   `Bracket`). With one solid, leaving the list empty also means "all", but the explicit reference is what the
   script uses.
5. **Save** as `Iteration1_<card>_L1.FCStd`.
6. **Check the exported deck.** Select the solver, choose **Write .inp file**, then open the deck:
   - `*MATERIAL, NAME=…` is followed by `*ELASTIC` with `E,ν` in MPa.
   - `*SOLID SECTION, ELSET=MaterialSolid, MATERIAL=…` appears exactly once.
   - `*ELSET,ELSET=MaterialSolid` names `Evolumes`, the set that `*Element, TYPE=C3D10` fills, so every element
     is assigned.
   - **A static deck contains no `*DENSITY`.** FreeCAD writes density only for frequency, self-weight,
     centrifugal and transient thermal analyses. The GE loads have no self-weight, so density does not affect
     stress or displacement.
   - To see the density conversion, set the solver's `AnalysisType` to `frequency`, write the deck again, check
     `*DENSITY` in t/mm³, and set it back to `static`.

Two FreeCAD 1.1.3 behaviours matter here:
- `FemToolsCcx.write_inp_file()` ignores the working directory set with `setup_working_dir()` and writes into a
  temporary folder. The script copies the deck out.
- In the GUI the deck goes to the solver's working directory preference.

## 4. Verification and mass

The script's check found every card **verified** in both decks. Decks are in `data/ge_manual/materials/<card>/`
(gitignored); checksums are in `materials.json`.

| Card | `*ELASTIC` line in the static deck | Elements in the material section | `*DENSITY` in the frequency deck | **Mass (g)** |
| --- | --- | --- | --- | --- |
| Ti-6Al-4V | `113800,0.342` | 90,353 of 90,353 | `4.43E-09` | **1,256.9** |
| Al 7075-T651 | `71705,0.33` | 90,353 of 90,353 | `2.81E-09` | **797.3** |
| Al 6061-T651 | `68948,0.33` | 90,353 of 90,353 | `2.7E-09` | **766.1** |
| 17-4PH H1025 | `199948,0.272` | 90,353 of 90,353 | `7.806E-09` | **2,214.8** |
| AISI 4140 Q&T | `199948,0.29` | 90,353 of 90,353 | `7.806E-09` | **2,214.8** |

- **Volume.** Mass uses the working-copy B-rep volume, 283,729.68 mm³. It is the same geometry for every card
  and every load case, so M2A.6 repeats one mass per material across LC1–LC4. The M2A.4 partition changes it
  by −0.002 mm³ (283,729.678), which does not show in the masses.
- **Steel masses match.** 17-4PH and 4140 come out identical because both datasheets give 0.282 lb/in³. The
  4140 fact sheet above gives 0.284 lb/in³ (7,850 kg/m³), which would be +0.6 %.
- **Scale check.** GE's original part was reported unverified at about 2.05 kg. This entrant design is 1,257 g
  in Ti.

## 5. Project criteria, kept separate from the challenge

| Criterion | Value | Status |
| --- | --- | --- |
| Stress criterion | Peak von Mises below yield under each load case | **Challenge, implied** ([brief §6](ge-jet-engine-bracket.md)) |
| Ti yield | 903.2 MPa | **Challenge** |
| Safety factor | 1.5 on yield, so Ti allowable is 602 MPa and each alternative's is yield / 1.5 | **Project choice**, not GE-prescribed ([brief §7](ge-jet-engine-bracket.md)). GE prescribes no safety factor |
| Displacement limit | 1.1 × baseline maximum displacement | **Project choice** (the [LC1 record](ge-bracket-lc1.md) sets it for the parametric agent task; the M2A baseline value comes from the Ti run in M2A.6) |
| Alternative materials | Four cards above | **Project extension**; the challenge fixes Ti-6Al-4V |

## 6. Status against the M2A.3 checklist

| Item | Status |
| --- | --- |
| Five cards with product form and heat treatment (17-4PH and 4140 specified) | Done (section 1) |
| Cited E, ν, density with solver-unit conversion, yield, temperature and source | Done (sections 1 and 2). **Open:** check the three secondary or MatWeb-format items against the governing specifications |
| GE 903.2 MPa for Ti; one consistent density | Done (the deck's 4,430 kg/m³, not the metadata's 4,470) |
| Assign to the complete solid in a manual Analysis and verify in the exported deck | Done (sections 3 and 4). **A person still needs to do one GUI pass**; the numbers come from the script |
| Record volume and mass in grams | Done (section 4) |
| Geometry, mesh, supports and loads fixed across cards | Geometry and mesh fixed. Supports and loads come in M2A.4/M2A.5 and must be added identically to each card's document. Re-run on L1 after L2 was dropped; every card verified again, and mass is unchanged |
| Ti baseline versus project comparisons; project safety factor and displacement criteria labelled | Done (scope note and section 5) |

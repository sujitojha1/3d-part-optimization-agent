# M2A — Manual GE challenge analysis and CAM readiness

[GitHub milestone](https://github.com/sujitojha1/3d-part-optimization-agent/milestone/7) · [Project board](https://github.com/users/sujitojha1/projects/10)

This milestone establishes a manually configured engineering workflow on one selected geometry in FreeCAD FEM and CAM. It needs no agent setup, LLM integration, gateway or automated optimization. Existing M2 evidence may be reused with explicit links; completion of an older LC1 task alone does not complete four-case coverage.

**Placement:** after the existing geometry/load groundwork in M2 and before M3 promotes the engineering workflow into pipeline code. M2A may start without waiting for M2's LLM exchange/specification tasks. Existing M1–M6 numbering is preserved.

**Schedule:** unscheduled additional scope as of 19 September 2026. The original 3 October deadline remains recorded; existing effort totals exclude M2A. Re-estimate remaining work and update roadmap dates before treating the old schedule as feasible. Do not silently fit this into the old M2 window.

**Geometry selection:** `data/simjeb/Iteration1.stp` is selected by visual comparison with the stored GE challenge images; see [geometry comparison](ge-geometry-comparison.md). Its SHA-256 is `a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e`. It is the closest-looking local candidate, not a verified original GE file. M2A.1 must still verify provenance, units, dimensions and interfaces. The parametric agent baseline `parts/ge_bracket.FCStd` remains separate.

**Exit criterion:** one frozen geometry; a reproducible mesh procedure with accepted quality and convergence evidence; five sourced material cards; documented fixed nut locations and lug load transfer; four independent GE loading conditions; a traceable 20-run report with stress/displacement maps and mass per case; and a manual CAM readiness assessment with blockers recorded.

**Scope:** GE fixes Ti-6Al-4V and uses additive manufacture. The Ti four-case analysis is the challenge-aligned baseline. Alternative materials and CNC CAM readiness are explicitly identified project extensions. Project safety factor and displacement limits are not GE-prescribed values. This manual milestone extends study coverage without silently changing the agent task's existing LC1 contract.

Sources: [GE brief](ge-jet-engine-bracket.md), [SimJEB](simjeb-dataset.md), [frozen part](ge-bracket-part.md), [existing LC1 record](ge-bracket-lc1.md).

## M2A.1 — Identify and freeze the selected GE geometry file

Task: [#59](https://github.com/sujitojha1/3d-part-optimization-agent/issues/59) · Record: [ge-manual-geometry.md](ge-manual-geometry.md)

Use `data/simjeb/Iteration1.stp`, selected after rendering all seven local candidates against the GE challenge images. SHA-256: `a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e`. See `docs/ge-geometry-comparison.md`. Visual selection is complete; provenance, dimensional and interface checks below remain open. This file has not been established as GE's original CAD. Preserve the separate parametric agent baseline.

1. Record the selected path, source/design identity, attribution, SHA-256, units, coordinate frame, CAD version and source revision in `docs/ge-manual-geometry.md`.
2. Open it manually in FreeCAD; check solid validity, connected solids, bounding box, volume, minimum walls, four nut/bolt locations and both lug bores. Save annotated interface views.
3. Check pin diameter 19.05 mm and bolt/nut interfaces against the GE brief. The current rebuild has 10.30 mm clearance holes for 9.525 mm bolts: record the distinction and any interface deviations. Do not claim the original envelope is verified unless an original-envelope reference exists.
4. Save a separate manual-analysis working copy, keeping the frozen source intact. Use a full model for all four cases unless symmetry is independently justified for each case, especially torsion.

Done when: exactly one file and checksum are selected, the working copy opens, and geometry/interface checks and deviations are recorded.

## M2A.2 — Document manual meshing steps and report mesh quality

Task: [#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60) · Record: [ge-manual-mesh.md](ge-manual-mesh.md)

Depends on M2A.1.

1. Open the working copy in FreeCAD FEM, create an Analysis, and add a Gmsh mesh of the selected solid. Select second-order tetrahedra (C3D10).
2. Record every setting: global maximum/minimum size, growth control where supported, element order and curved/linear midside setting. Start from existing M2 mesh evidence; use local MeshRegions at arm-root fillets, lug bores, nut-seat patches and thin sections.
3. Generate the mesh manually and inspect sections through fillets, holes and thicknesses. Record mesher version, node/element counts by type, elapsed time, mesh file and checksum.
4. Report quality with named metric definitions and tool/version: minimum signed Jacobian, inverted/zero-volume element count, aspect-ratio and scaled-Jacobian distributions where supported (minimum, relevant percentiles, worst element IDs and locations). State unavailable metrics explicitly. Save a histogram and annotated worst-element views.
5. Require zero inverted/degenerate elements before solving. Define and record tool-specific quality thresholds before accepting the mesh; correct failures through local sizing or geometry repair. If curved quadratic elements invert, record a trial with linear midside placement and recheck quality.
6. Compare at least three mesh levels using Ti-6Al-4V across LC1–LC4 after loads are set up. Record displacement, reactions, raw stress and stress away from explicitly documented constraint singularities. Set convergence tolerances before comparison; flag non-convergent peaks rather than hiding them. Freeze the accepted mesh.

Done when: `docs/ge-manual-mesh.md` contains repeatable click-by-click steps, settings, quality results, acceptance thresholds and convergence evidence. Mesh generation precedes material/BC setup; convergence completes after M2A.5 and feeds M2A.6.

## M2A.3 — Prepare and assign five material options manually

Task: [#61](https://github.com/sujitojha1/3d-part-optimization-agent/issues/61)

Depends on M2A.1 and initial mesh generation in M2A.2.

Prepare Ti-6Al-4V, Al 7075-T6, Al 6061-T6, 17-4PH stainless steel, and 4140 steel. Specify product form and heat-treatment condition, particularly for 17-4PH and 4140; do not assign generic yield values to unspecified conditions.

For each card record cited Young's modulus (MPa), Poisson's ratio, density with explicit conversion to solver units, yield strength (MPa), temperature and source. Use the GE prescribed approximately 903 MPa yield for the Ti challenge baseline; document the density choice consistently instead of mixing SimJEB metadata and deck densities.

In the manual FreeCAD Analysis, assign each card to the complete solid and verify it in the exported solver deck. Record volume and calculate mass in grams from that material's density. Keep geometry, accepted mesh, supports and loads fixed for comparison.

Done when: `docs/ge-manual-materials.md` contains five sourced, fully specified cards and manual assignment steps. Ti is the challenge baseline; four alternatives are project comparisons outside the challenge's fixed-material brief. Any project safety factor or displacement criterion is labelled separately from challenge requirements.

## M2A.4 — Fix the four nut locations and define lug load transfer

Task: [#62](https://github.com/sujitojha1/3d-part-optimization-agent/issues/62)

Depends on M2A.1–M2A.3.

1. Identify and annotate Interfaces 2–5 at the four nut locations. Create/select actual nut-seat contact patches, using the GE nut annulus dimensions (10.287 mm ID, 14.173 mm OD) and intersecting with real solid material/clearance holes. Partition faces in the working copy if needed; do not accidentally fix the entire base-top face.
2. Apply fixed translation at the four patches or a documented rigid support/reference-node representation of infinitely stiff bolts. Record restrained degrees of freedom. If an existing bore-coupled support is reused, label it as a different idealisation and compare it with the requested nut-seat setup before adoption.
3. At Interface 1 define a rigid pin spanning both lug bores, with its reference point at the pin centreline/clevis midplane. Apply force or moment through that reference point, not a single surface node. Verify moment transfer is supported for LC4.
4. Record selected faces/node sets, reference coordinates, coupling definitions, support and load screenshots, and exported deck cards. Verify that all four supports and both lug bores are included, with no accidental extra restraints.

Done when: `docs/ge-manual-boundary-conditions.md` describes a reproducible manual setup for fixed nut locations and lug loading, including singularity risks at idealised supports and rigid pin boundaries. Reaction force and moment balance is checked in M2A.6.

## M2A.5 — Set up four independent GE static load cases

Task: [#63](https://github.com/sujitojha1/3d-part-optimization-agent/issues/63)

Depends on M2A.4. Use the full model and the documented SimJEB frame (+z up, outward −x). If the selected CAD uses a different frame, record and apply the coordinate transform to loads and reference points.

| Case | Force (N) | Moment (N·mm) |
| --- | --- | --- |
| LC1 vertical | (0, 0, +35585.77) | (0, 0, 0) |
| LC2 horizontal | (−37809.9, 0, 0) | (0, 0, 0) |
| LC3 diagonal, 42° from vertical | (−28276.2, 0, +31403.9) | (0, 0, 0) |
| LC4 torsion about +z | (0, 0, 0) | (0, 0, +564924.2) |

Create four separate manual analyses or solver decks sharing the same accepted geometry, material and support definitions. Apply each case independently; remove preceding loads and prevent load accumulation. Inspect exported force/moment signs, units, load point and coupling cards against the table. Save arrows/axis screenshots.

Done when: `docs/ge-manual-load-cases.md` and four named setups reproduce these vectors, with LC4 torque transferred through the pin. Sources: `docs/ge-jet-engine-bracket.md` §3 and `docs/simjeb-dataset.md` §2.

## M2A.6 — Run the manual material/load matrix and publish stress, mass and displacement report

Task: [#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64)

Depends on M2A.2–M2A.5, including accepted quality and completed convergence checks.

Manually run all four independent load cases for each of the five material cards (20 analyses). Use FreeCAD FEM/CalculiX, retaining the working documents, input decks, solver logs and result files. No agent, gateway, capability registration or optimization loop is required.

For each run record solve status/warnings, wall time, mesh ID, material condition, full-part mass (g), maximum von Mises stress (MPa) and location, maximum displacement magnitude (mm) and location. Check summed support forces AND moments against applied loads about a common origin, with recorded acceptance tolerances. A failed or invalid solve is reported as such, never as zero stress or a pass.

Export labelled stress maps and displacement maps for every material/case pair, with units, view, deformation scale and consistent stress extraction/averaging. Use fixed cameras and common legend ranges for comparisons; supplementary close-ups may use clearly marked ranges. Report raw maxima alongside any stress excluding a defined support singularity zone, with the exclusion and convergence evidence visible.

Publish `docs/ge-manual-analysis-report.md` plus a CSV containing 20 rows: geometry/mesh identity, material, LC, status, mass_g, max_vm_MPa, peak_location, max_disp_mm, displacement_location, yield/SF margin, reaction residuals, timing and artifact links. Mass is repeated per case and should be identical across LC1–LC4 for a fixed geometry/material. Identify the governing case for stress and displacement per material. Label Ti as the challenge baseline; do not call alternative materials challenge-compliant. Yield exceedance in a linear-elastic solve is a failed screening result, not a plastic-collapse prediction.

Done when: all 20 combinations have traceable records, valid solves have maps and metrics, and unresolved failures/quality issues are explicit. The milestone cannot be declared fully analysed while required combinations remain invalid.

## M2A.7 — Walk through CAM readiness manually and document blockers

Task: [#65](https://github.com/sujitojha1/3d-part-optimization-agent/issues/65)

Depends on M2A.1 and material selection in M2A.3; may proceed while analysis results are being reviewed.

1. Open the same selected geometry in FreeCAD CAM. Record stock, work coordinate systems, fixture/clamp regions, top/bottom/side setups and tool approach directions.
2. Define a ToolBit library and material-specific feeds/speeds with sources or documented shop assumptions. Check tool diameter, flute/reach length, holder clearance, internal radii, deep pockets, lug-bore access, minimum walls and undercuts.
3. Manually create Adaptive/Pocket, Profile and Drilling/boring operations as appropriate to the real features. Recompute and inspect paths, remaining-stock strategy and setup transfers.
4. Post-process using a named machine/controller postprocessor; replay available simulation, inspect residual stock, gouging and tool/fixture collisions. Record checks the simulator cannot establish as unverified and requiring machine/fixture review.
5. Save screenshots, working CAM document, tool/operation/setup sheets, G-code and simulation evidence. Classify each feature ready, blocked or unverified, and identify corrective actions. Overall readiness remains conditional on unresolved checks.

Done when: `docs/ge-manual-cam-readiness.md` provides repeatable manual steps and an evidence-backed readiness assessment. CNC readiness is a project extension to GE's additive-manufacturing brief, not certification that a part is safe to machine.

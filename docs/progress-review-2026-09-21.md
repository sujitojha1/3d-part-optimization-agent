# Progress and requirements audit — 21 September 2026

Reviewed original intent, all 35 normative requirement rows, D-01–D-24, the plan, architecture, all 63 GitHub board items, tracked scripts/configuration, and current local JSON/CSV evidence. This is an evidence audit, not a new solver execution or independent physics validation. GitHub closure is retained as historical evidence where its external harness/video work cannot be independently reproduced here.

## Overall finding

The project has engineering prototypes and recorded solves, but has not yet demonstrated the intent’s read → predict → one edit → re-solve → score loop. None of the five Route B deliverables is demonstrated end to end. Do not equate closed issue percentage with product completeness. M1 has 11 closed issues; M2 is partial; M2A is blocked on geometry/mesh acceptance and record reconciliation; M3–M6 remain open. #51 was merged into #50, not experimentally completed.

## Current evidence and blocking discrepancies

1. **Geometry identity changed.** `scripts/ge_part.py` selects `GE_Challenge_Bracket`, source SHA `d34fab379fd6293e862a5db22fe42421e3a32c9ee865706e6fc3ed2b9a5b0dc9`. Manual documents still describe Iteration1. FVZ is the donor; the parametric agent `parts/ge_bracket.FCStd` remains a different part. Carry geometry and mesh hashes through every result; never transplant the old report’s conclusions.
2. **Current mesh rejected.** `out/ge_manual_mesh/mesh-quality.json`: 93,659 nodes, 57,835 C3D10 elements; six of seven rules pass; gamma minimum 0.014992566 fails 0.05. No required three-level/four-case convergence record. `out/ge_manual_geometry/geometry-check.json` also has 28 edge and 28 face curve-on-surface BOP errors. The solid-export summary’s zero flag total does not override these exceptions.
3. **20 solves are solver-valid, not verified.** Current matrix/CSV has 20 rows, five materials × four cases, identical current geometry/mesh IDs, and all 60 deck/FRD/map paths exist. Times 39.5–41.1 s. Ti LC1: 2052.2 g, raw 1521.8 MPa, outside-zone 336.5 MPa, 0.2278 mm. The written report’s 1256.9 g / 427.2 MPa / 0.4142 mm describes the earlier Iteration1 study. The pre-existing CSV edit is preserved.
4. **Structural pass semantics disagree.** Requirements use max von Mises with SF; LC1/manual records screen outside excluded support zones. Raw parametric baseline is 781 MPa versus ~602 MPa allowable. Exclusion alone is not D-12 singularity verification. Resolve in #27/#29 before a baseline can pass. Fixed bore supports also differ from the prescribed rigid-body coupling; V3 must test the chosen setup.
5. **Symmetry assumption disproved.** The frozen parametric record uses a full model because the bolt pattern is asymmetric. Correct D-23 and timing assumptions; do not halve loads or double full-model mass. The earlier 16.45 s LC1 solve is evidence against a timing-only fallback, not proof of the final mesh/CAM budget.
6. **CAM remains experimental.** Four setup paths exist; op20 reports 31,634.32 mm² sampled gouge area. Diagnose geometry/stock/setup/simulation before interpreting this as a physical cut. No final CAM readiness report exists. Gate 4 uses 0.5 mm residual tolerance, while D-11 requires 0.2 mm. The environment now includes opencamlib and experimental CAM code, despite D-17/section 6 exclusions. Keep manual experiments separate from release acceptance.
7. **Vision transport passed, interpretation did not always pass.** Gate 2b has ok=true but contour_1600 reading.peak_quadrant=false. Transport is complete; region reasoning/readability must still be demonstrated in #49/#50.
8. **Packaging and records remain incomplete.** Root README has only a title; no bundled task, harness lock, verifiers or mutation suite here. Mutable shared output folders can overwrite geometry-specific provenance; keep accepted snapshots by part/hash. Do not commit fetched or derived SimJEB CAD merely because #66 asks for a committed source.

## Every normative requirement

Status means accepted evidence for the complete requirement; Partial never means release pass.

| Requirement | Priority | Status | Owner issue | Evidence / missing acceptance |
| --- | --- | --- | --- | --- |
| REQ-IN-001 | Must | Not implemented | #20 | No versioned task schema or intake fixtures in this repository. |
| REQ-IN-002 | Must | Partial | #20 | Manual deck unit checks exist; runtime field-specific rejection and mutation fixture absent. |
| REQ-IN-003 | Must | Partial | #21 | Baseline FEM evidence exists; no integrated baseline including manufacturing. |
| REQ-IN-004 | Must | Not implemented | #21 | No invalid-baseline termination fixture. |
| REQ-OPT-001 | Must | Partial | #17 | render_field.py and manual maps exist; matching agent image trace and locked cross-iteration legend not proved. |
| REQ-OPT-002 | Must | Partial | #22 | Surface labels exist; gateway transport does not establish correct closed-set region interpretation. |
| REQ-OPT-003 | Must | Not implemented | #23 | CAD bounds helpers do not enforce exactly one geometry/material edit in the agent runtime. |
| REQ-OPT-008 | Must | Partial | #47 | ge_bracket_check.py exercises CAD bounds; FEM/CAM predicates and zero/multiple-match unverified result need integration. |
| REQ-OPT-004 | Must | Not implemented | #24 | No rationale/prediction persisted before a candidate tool call. |
| REQ-OPT-005 | Must | Not implemented | #25 | No stored region/direction/band scoring or fixtures. |
| REQ-OPT-006 | Must | Partial | #26 | Five manual material cards exist; D-10 cost, machinability, corrosion, availability and agent trace contract incomplete. |
| REQ-OPT-007 | Must | Not implemented | #26 | Required-property null exclusion is not enforced in a candidate runtime. |
| REQ-VER-001 | Must | Partial | #27 | Manual B-rep volume × density mass exists; task tolerance fixture and integrated full-part reporting remain. |
| REQ-VER-002 | Must | Partial | #27 | Manual screens exist; invalid mesh and exclusion-zone conflicts prevent release acceptance; boundary fixtures absent. |
| REQ-VER-003 | Must | Partial | #28 | Gate 4 block/undercut and manual CAM experiments exist; current-part 0.2 mm residual, min-wall, gouge and invalid fixtures not proved. |
| REQ-VER-004 | Must | Partial | #27 | Scripts record errors, but the current matrix labels runs valid despite rejected upstream mesh; integrated validity gate missing. |
| REQ-VER-005 | Must | Not implemented | #29 | No calibrated nominal-versus-zero fillet refinement protocol with matched controls. |
| REQ-VER-006 | Must | Partial | #30 | Deck vectors checked in manual loads; sign-flipped mutation and scoring-time rejection remain. |
| REQ-OUT-001 | Must | Not implemented | #37 | No integrated eight-evaluation/20-minute budget and in-flight completion fixture. |
| REQ-OUT-002 | Must | Not implemented | #37 | Six terminal outcomes and repeat-failure fixtures absent. |
| REQ-OUT-003 | Must | Not implemented | #38 | Material comparisons are not a searched geometry/material frontier or scoped refusal fixture. |
| REQ-OUT-004 | Must | Not implemented | #39 | No end-to-end recommendation linked to baseline, edits and recorded evaluations. |
| REQ-DEL-001 | Must | Partial | #19 | S17 fork closure is recorded on GitHub; integrated project loop and its dependency audit are not present here. |
| REQ-DEL-002 | Must | Partial | #19 | Standalone FreeCAD/Gmsh/ccxtools scripts exist; typed run_sim/read_result process contracts absent. |
| REQ-DEL-003 | Must | Partial | #40 | FEM explicit lock/setup exist; harness uv lock/bootstrap and clean-Mac task execution absent here. |
| REQ-DEL-004 | Must | Not implemented | #31 | Three executable task predicates absent. |
| REQ-DEL-005 | Must | Not implemented | #32 | Three paired mutants and measured detection/false-positive rates absent; report not evaluated. |
| REQ-DEL-006 | Must | Partial | #24 | Raw manual artifacts exist; complete ordered run record and write-failure-before-scoring gate absent. |
| REQ-DEL-007 | Must | Not implemented | #35 | Report-only plotting is not offline agent rescoring with model and solver disabled. |
| REQ-DEL-008 | Must | Partial | #19 | Manual scripts retain diagnostics; integrated candidate-ID failure records need fault injection. |
| REQ-DEL-009 | Must | Partial | #15 | Bundled cantilever -86.9271 mm passes its gate; slender V1 and V3 displacement/reaction release tests absent (also #57). |
| REQ-DEL-010 | Must | Not implemented | #19 | Rerunnable capabilities and repeated-call execution fixture absent. |
| REQ-DEL-011 | Must | Not implemented | #34 | Protected judge/task/material/mutation/tooling paths are not integrated and tested. |
| REQ-DEL-012 | Should | Deferred (Should) | #42 | Manual matrix is not the required agent-run summary. |
| REQ-DEL-013 | Should | Deferred (Should) | #41 | No matched skill/no-skill agent runs. |

## Decision review (D-01–D-24)

| Decisions | Audit result |
| --- | --- |
| D-01–D-03 | Linear static and pinned FreeCAD-driven CalculiX/Gmsh exist. C3D10 does not by itself establish mesh quality or convergence. |
| D-04–D-06 | Six bounded spreadsheet parameters and geometric CAD predicates exist for ge_bracket. Replacement manual CAD is not its parametric substitute. Region sets need disjoint volume coverage and predicate failure behavior. |
| D-07–D-08 | Prediction schema not implemented. Agent remains single LC1; four-case manual study is additional scope. |
| D-09–D-10 | Five engineering cards exist; T651 manual records differ from named T6 requirements. Freeze product/temper/source identity and complete all material tradeoff fields before runtime use. |
| D-11–D-12 | CAM and singularity verifiers incomplete. Screening exclusions and exploratory CAM do not satisfy these decisions. |
| D-13–D-14 | Solve-only timings exist; combined evaluation timing and a valid structural/manufacturing baseline do not. Keep ge_bracket as demo, L_bracket fallback only if timing fails after required accuracy. |
| D-15–D-16 | Three tasks and three paired mutants remain to build; four-case material study does not replace them. |
| D-17–D-18 | FEM lock and gateway image transport demonstrated. Harness packaging and experimental opencamlib scope need reconciliation. |
| D-19–D-21 | Rerunnable capabilities, protected paths and runtime mesh-edit refusal remain to integrate. |
| D-22 | Bundled cantilever gate passed; slender V1 and V3 remain release blockers. |
| D-23 | Full model required by measured asymmetric bolt pattern; corrected in requirements/plan. |
| D-24 | Parametric MeshRegion sizing and the minimum-fillet check are now recorded ([ge-bracket-mesh.md](ge-bracket-mesh.md)); the sizes are provisional pending M2.5, D-24 omits the load-bearing `OptimizeNetgen` setting, the retry path is only exercised under force, and the current manual mesh is still rejected. |

OD-B and OD-C remain unset. Define V1/V3 and numerical tolerances before evaluating validation fixtures; freeze prediction/mutation thresholds before the scored evaluation set, not after viewing those scores. No deadline trigger may silently remove a Must test.

## Board reconciliation

Existing closed issues are historical completion records. Open tasks with concrete artifacts move to In Progress; no issue is newly closed on this audit. #59/#61 retain historical closure but replacement-geometry work remains in #66/#60/#62–#65.

| Issue | Status after audit | Evidence / remaining work |
| --- | --- | --- |
| #45 | In Progress | Nominal parametric LC1 mesh exists. Minimum-fillet D-24 MeshRegion evidence and the inversion/retry check were added later the same day in [ge-bracket-mesh.md](ge-bracket-mesh.md) — four cases accepted at max 4.0 / min 1.0 / region 1.5, no inverted elements at either radius, retry recorded only under `--force-retry`. The sizes remain provisional until M2.5 solves on them, and no solve, convergence or element-set evidence exists yet. |
| #47 | In Progress | CAD predicate checks exist at parameter bounds and were rerun 21 Sep (77 points pass). The overlapping surface-node regions are now measured and explained, and the deck route is settled later the same day in [ge-bracket-labels.md](ge-bracket-labels.md): **no D-06 label reaches the ccxtools deck** (`group_param = False`, hard-coded in FreeCAD 1.1.3), and the group-enabled deck gives surface sets, not volume sets. The D-06 element-centroid fallback is implemented and is exhaustive, disjoint and non-empty at all 13 meshed points. No solve has yet labelled a result. |
| #48 | In Progress | ccxtools LC1 solves and parsed results exist (rigid full model about 16.45 s). Final D-24 mesh, full-part mass/result contract and unambiguous element-region evidence remain. |
| #49 | In Progress | Renderer and reference/manual-study maps exist. Freeze and visually accept the parametric bracket camera/legend settings, then check SimJEB 148; generic gateway transport is insufficient. |
| #53 | In Progress | 21 September intent-to-requirement audit and revised plan now exist locally. Full M2 walkthrough, render freeze and LLM integration spec remain outstanding. |
| #59 | Done (historical scope) | Earlier closure records Iteration1 geometry. Current GE_Challenge_Bracket requires refreshed geometry documentation, interface/GUI evidence and quality acceptance through #66; the prior closure does not certify the replacement. |
| #61 | Done (historical scope) | Five engineering cards and deck checks exist and have been rerun on the current mesh. Refresh stale geometry references/manual GUI evidence. This does not complete the D-10 agent material library (#26). |
| #60 | In Progress | Current GE_Challenge_Bracket L1 has 93,659 nodes / 57,835 C3D10 elements. Six of seven quality rules pass; gamma_min=0.014993 fails >=0.05. accepted=false. Required three-level/four-case convergence evidence remains missing. Do not relax thresholds to mark Done. |
| #62 | In Progress | Current-part nut-patch and rigid-pin decks exist; four supports contain 525 fixed nodes with no fixed/pin overlap and no extra restraints. Written Iteration1 face references and manual GUI evidence need reconciliation. |
| #63 | In Progress | Current-part LC1-LC4 decks exist; all_checks_pass=true. Refresh geometry/mesh/face references in the written load-case record and retain the required manual inspection evidence. |
| #64 | In Progress | Current GE_Challenge_Bracket matrix has 20/20 solver-valid runs, all 60 CSV deck/FRD/map paths exist. Ti LC1: 2052.2 g, raw max 1521.8 MPa, outside-zone max 336.5 MPa, displacement 0.2278 mm; solves 39.5-41.1 s. Mesh is rejected and convergence absent. Existing report describes Iteration1 (1256.9 g), so it is historical, not current acceptance. Refresh the report only with explicit geometry provenance; never count solver-valid as engineering-verified. |
| #65 | In Progress | Four setup G-codes and experimental simulation records exist. op20 reports 31634.32 mm2 sampled gouge area; this must be diagnosed, not treated as manufacturing acceptance. Final ge-manual-cam-readiness.md is absent; establish current geometry provenance, fix paths/stock/simulation, document setup/tool/fixture limitations and GUI evidence. |
| #66 | In Progress | Outer-shell solid and STEP round-trip exist; generated source SHA d34fab379fd6293e862a5db22fe42421e3a32c9ee865706e6fc3ed2b9a5b0dc9. Current L1 still fails gamma_min (0.014993 <0.05), and geometry check reports 28 edge plus 28 face InvalidCurveOnSurface flags. Interface/documentation/quality exit is not met. Preserve source licensing/fetch policy; do not interpret the old issue wording as permission to redistribute derived SimJEB CAD. |

## Complete board snapshot

Dates below are current recovery targets, not a claim that the fixed deadline is feasible. Should items remain unscheduled. Historical completed-item dates are preserved.

| Issue | Task | Status | Start | Target |
| --- | --- | --- | --- | --- |
| #3 | M1.3 GATE 1 — configure the S17 environment and prove a prompt routes 8113 to 8111 | Done | 2026-09-19 | 2026-09-19 |
| #44 | M2.1 Build the parametric ge_bracket FreeCAD document and freeze its parameter record | Done | 2026-09-19 | 2026-09-20 |
| #46 | M2.2 Freeze the LC1 load record, SF, displacement limit and pin-load model, with a hand calculation | Done | 2026-09-20 | 2026-09-20 |
| #45 | M2.3 Hand-mesh ge_bracket with FemMeshGmsh at nominal and minimum fillet | In Progress | 2026-09-21 | 2026-09-23 |
| #47 | M2.4 Verify mesh groups and face predicates survive into the .inp at parameter bounds | In Progress | 2026-09-21 | 2026-09-23 |
| #54 | M1.8 Go through the Session 17 video — time-boxed to 1 h | Done | 2026-09-17 | 2026-09-17 |
| #55 | M1.9 Verify all LLM providers, refresh the model list and .env, add a second Gemini API key | Done | 2026-09-19 | 2026-09-19 |
| #48 | M2.5 Hand-run the ccxtools solve, parse it and measure it | In Progress | 2026-09-21 | 2026-09-23 |
| #2 | M1.2 Serve the glc_v5 gateway on 8111 and configure provider keys | Done | 2026-09-08 | 2026-09-10 |
| #1 | M1.1 Fork and clone S17Code, confirm its test suite is green | Done | 2026-09-08 | 2026-09-12 |
| #4 | M1.4 GATE 2a — prove pyvista renders off-screen on macOS | Done | 2026-09-18 | 2026-09-19 |
| #5 | M1.5 GATE 2b — prove an image reaches a vision model through glc_v5 | Done | 2026-09-19 | 2026-09-19 |
| #6 | M1.6 Create the FEM environment — FreeCAD (FEM and CAM), Gmsh, CalculiX from a conda-forge explicit lock | Done | 2026-09-17 | 2026-09-18 |
| #10 | M1.7 GATE 3 — run FreeCAD's bundled CalculiX cantilever headless and reproduce -86.93 mm | Done | 2026-09-18 | 2026-09-18 |
| #11 | M3.1 Promote the ge_bracket FreeCAD document — parameters in, predicate-selected faces out | Todo | 2026-09-24 | 2026-09-26 |
| #12 | M3.2 FemMeshGmsh sizing per D-24, with the negative-Jacobian retry | Todo | 2026-09-24 | 2026-09-26 |
| #13 | M3.3 FEM analysis assembly — material, rigid-body supports, pin load, symmetry — written by ccxtools | Todo | 2026-09-24 | 2026-09-26 |
| #14 | M3.4 Parse .frd to full-part mass, max von Mises, max displacement, peak region label | Todo | 2026-09-24 | 2026-09-26 |
| #15 | M3.5 V1 validation — FreeCAD cantilever and a slender cantilever against closed form | Todo | 2026-09-24 | 2026-09-26 |
| #16 | M3.6 V2 validation (Should) — shoulder-fillet stepped bar against a published Kt | Todo | — | — |
| #17 | M3.7 Contour renderer with fixed camera set and locked legend range | Todo | 2026-09-24 | 2026-09-26 |
| #18 | M3.8 Measure per-iteration wall time and confirm or revise the budget | Todo | 2026-09-24 | 2026-09-26 |
| #19 | M4.1 Register run_sim, read_result and check_manufacturing as rerunnable capabilities | Todo | 2026-09-27 | 2026-09-29 |
| #20 | M4.2 Task schema and validation, including unit-consistency rejection | Todo | 2026-09-27 | 2026-09-29 |
| #21 | M4.3 Baseline evaluation and invalid-baseline termination | Todo | 2026-09-27 | 2026-09-29 |
| #22 | M4.4 Vision step — contour into the model, concentration recorded as a region label | Todo | 2026-09-27 | 2026-09-29 |
| #23 | M4.5 Single-edit enforcement in the runtime, mesh changes refused | Todo | 2026-09-27 | 2026-09-29 |
| #24 | M4.6 Prediction record in the D-07 schema, persisted before the tool call | Todo | 2026-09-27 | 2026-09-29 |
| #25 | M4.7 Score the prediction against the next evaluation as three booleans | Todo | 2026-09-27 | 2026-09-29 |
| #26 | M4.8 Material library — 5 machinable alloys, all D-10 fields with cited sources | Todo | 2026-09-27 | 2026-09-29 |
| #27 | M5.1 Structural and mass verifiers, with invalid results never passing | Todo | 2026-09-30 | 2026-10-01 |
| #28 | M5.2 cnc_3axis check — CAM Workbench job per setup, PathSimulator residual stock, minimum wall | Todo | 2026-09-30 | 2026-10-01 |
| #29 | M5.3 Singularity protocol — halved MeshRegion re-solve, 20% rule calibrated on ge_bracket | Todo | 2026-09-30 | 2026-10-01 |
| #31 | M5.5 The 3-task set with an executable predicate each | Todo | 2026-09-30 | 2026-10-01 |
| #32 | M5.6 The 3-mutant corpus with paired valid controls | Todo | 2026-09-30 | 2026-10-01 |
| #33 | M5.7 Report detection fraction and control false-positive rate | Todo | 2026-09-30 | 2026-10-01 |
| #34 | M5.8 Enforce protected paths and record every refusal | Todo | 2026-09-30 | 2026-10-01 |
| #35 | M5.9 Offline rescoring with model and solver disabled | Todo | 2026-09-30 | 2026-10-01 |
| #36 | M5.10 The FEA-reasoning SKILL.md | Todo | 2026-09-30 | 2026-10-01 |
| #37 | M6.1 Budget and repeat-failure ceilings, and the six terminal outcomes | Todo | 2026-10-02 | 2026-10-02 |
| #38 | M6.2 Explored frontier with scoped infeasibility wording | Todo | 2026-10-02 | 2026-10-02 |
| #39 | M6.3 Link the recommendation to baseline, change history and evidence | Todo | 2026-10-02 | 2026-10-02 |
| #40 | M6.4 Clean-machine run on macOS — one documented command from the pinned locks | Todo | 2026-10-02 | 2026-10-02 |
| #41 | M6.5 Skill A/B (Should) — one task with and without the SKILL.md | Todo | — | — |
| #42 | M6.6 Run report (Should) — mass delta, margins, prediction accuracy, mutation detection | Todo | — | — |
| #43 | M6.7 README and demo video, including the failures and the refusal | Todo | 2026-10-02 | 2026-10-03 |
| #30 | M5.4 Load-direction check against the generated .inp | Todo | 2026-09-30 | 2026-10-01 |
| #49 | M2.6 Render the contour by hand and judge whether it is readable | In Progress | 2026-09-21 | 2026-09-23 |
| #50 | M2.7 Run one real exchange through glc_v5 by hand, image-only and image-plus-numbers | Todo | 2026-09-21 | 2026-09-23 |
| #51 | M2.8 Settle numbers-before-or-after-picture by experiment | Done | 2026-09-18 | 2026-09-18 |
| #52 | M2.9 Write the LLM integration spec | Todo | 2026-09-21 | 2026-09-23 |
| #53 | M2.10 Walkthrough record and plan delta | In Progress | 2026-09-21 | 2026-09-23 |
| #56 | M1.10 Fetch SimJEB sample and metadata by pinned file ID and checksum into gitignored data/ | Done | 2026-09-17 | 2026-09-17 |
| #57 | M3.9 V3 validation — SimJEB design 148 LC1 displacement against the OptiStruct field | Todo | 2026-09-24 | 2026-09-26 |
| #58 | M1.11 GATE 4 — a FreeCAD CAM Job runs headless: operations, post-processed G-code, PathSimulator stock | Done | 2026-09-18 | 2026-09-18 |
| #59 | M2A.1 Identify and freeze the selected GE geometry file | Done | 2026-09-20 | 2026-09-20 |
| #60 | M2A.2 Document manual meshing steps and report mesh quality | In Progress | 2026-09-21 | 2026-09-23 |
| #61 | M2A.3 Prepare and assign five material options manually | Done | 2026-09-20 | 2026-09-20 |
| #62 | M2A.4 Fix the four nut locations and define lug load transfer | In Progress | 2026-09-21 | 2026-09-23 |
| #63 | M2A.5 Set up four independent GE static load cases | In Progress | 2026-09-21 | 2026-09-23 |
| #64 | M2A.6 Run the manual material/load matrix and publish stress, mass and displacement report | In Progress | 2026-09-21 | 2026-09-23 |
| #65 | M2A.7 Walk through CAM readiness manually and document blockers | In Progress | 2026-09-21 | 2026-09-23 |
| #66 | M2A.8 Build a simplified GE challenge CAD model from the FVZ outer surface | In Progress | 2026-09-21 | 2026-09-23 |

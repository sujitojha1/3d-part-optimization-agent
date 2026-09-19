# Execution Plan — 3D Part Optimization Agent

| Attribute | Value |
| --- | --- |
| Version | 0.6 |
| Date | 2026-09-19 |
| Owner | Sujit Ojha |
| Budget | 12 Sep → **Sat 3 Oct 2026, fixed**. Re-planned on 17 Sep with 17 days left. See [Timeline](#timeline) |
| Board | [Project #10](https://github.com/users/sujitojha1/projects/10) — milestones, tasks and dates below are mirrored there |
| Companion documents | [Intent](intent.md) — why · [Requirements](requirements.md) v0.5 — what · [Solution architecture](solution-architecture.md) — how · this — when and in what order |
| Reference inputs | [GE jet engine bracket brief](ge-jet-engine-bracket.md) — the demo part · [SimJEB dataset](simjeb-dataset.md) — interface coordinates, load vectors, V3 · [FEM Workbench](fem-workbench.md), [CAM Workbench](freecad-cam-workbench.md), [FEM geometry preparation](fem-geometry-preparation.md), [FreeCAD tutorials](freecad-tutorials.md) — the stack's own documentation |

Seven milestones: M1–M6 plus M2A, numbered as on the board. Each states an **expectation** (what it is for), an **exit criterion** (a single observable fact that ends it), and its tasks. Where this document and `requirements.md` disagree, requirements win on *what* and this wins on *order*.

---

## v0.6 addition — manual GE challenge workflow

Added **M2A — Manual GE challenge analysis and CAM readiness**, requested on 19 September: identify one geometry, document meshing and quality, assign five material options, fix the nut locations, load the lug under all four GE cases, report stress maps/mass/displacement for 20 combinations, and assess CAM readiness manually. See [the detailed procedure and deliverables](ge-manual-workflow.md). It requires no agent setup. Existing M2 evidence can be reused; M2A is additional scope with dates and effort unassigned. The fixed release date is unchanged, but the original totals below exclude this addition and require re-estimation.

## Why v0.5 exists

**Where the project stood on 17 Sep.** Two of 55 issues were closed (M1.1, M1.2). All three gates were still open, three days after M1's window ended. The board showed M2.1–M2.5 *In Progress*, but no FEA tool was installed on the build machine, so no hand solve could have happened. The work on 17 Sep went into three reference pages on FreeCAD — about 1,460 lines — while the plan still listed FreeCAD as dropped.

**Four owner decisions on 17 Sep**, recorded as requirements v0.5:

1. **macOS arm64 only.** The Windows toolchain in v0.4 — the GE `ccx` 2.10 build and `win_amd64` wheels — does not run on the build machine.
2. **3 Oct is fixed.** Seventeen days remain, not the 22 the v0.4 timeline assumed.
3. **The GE-style jet engine bracket is the demo part.** `L_bracket` is now only the fallback.
4. **The intent's stack, centred on FreeCAD.** FreeCAD 1.1.3 drives Gmsh and CalculiX through its FEM Workbench, and its **CAM Workbench** is the manufacturability check: 3-axis machining, not printing. No other CAD tool, and no slicer. CadQuery is withdrawn.

Decision 4 makes the FreeCAD reference pages useful. They now document the stack we use, rather than a tool we dropped, and most of their eleven proposed changes are folded into the tasks below.

**What changed in the plan:**

- M1 gains a CAM gate, and Gate 3 runs FreeCAD's bundled cantilever.
- The M2 hand walk builds the FreeCAD bracket, which M3 then promotes to pipeline code. That saves M3's CAD work.
- The `.inp` writer is FreeCAD's `ccxtools`, not ours.
- V3 becomes a gate, because the demo part carries its loads through couplings. V2 becomes Should.
- The task set drops from 9 to 3 and the mutation corpus from 6 to 3. The material library now has 5 machinable alloys.
- The skill A/B and the run report are Should.

---

## Milestone map

| # | Milestone | Window | Exit criterion |
| --- | --- | --- | --- |
| **M1** | Foundations and de-risking | 17–19 Sep | Four gates pass, or a named fallback is written down |
| **M2** | One part, one load case, walked by hand | 19–22 Sep | A frozen FreeCAD `ge_bracket` and LC1 record, one hand pass to a contour, and a written LLM integration spec |
| **M2A** | Manual GE challenge analysis and CAM readiness | Unscheduled; before M3 | One geometry, accepted mesh, five materials × four cases reported, and manual CAM readiness assessed |
| **M3** | Engineering loop, no agent | 23–25 Sep | A parameter dict returns a verified result, and V1 and V3 pass |
| **M4** | The agent loop closes | 26–28 Sep | One full cycle on disk: read → predict → edit → re-run → score |
| **M5** | Judgement | 29 Sep – 1 Oct | Mutation detection and false-positive rates are reportable numbers |
| **M6** | Refusal and packaging | 1–3 Oct | Someone else runs one command on a clean Mac and gets a result |

Four hard orderings:

- **Nothing depends on the vision path** until M1 Gate 2b answers `OD-D`.
- **No pipeline code before M2 has walked the chain by hand** on the frozen part and load case. The decisions M3 would otherwise make silently are still cheap to change there: face predicates, mesh groups, the pin-load model, the camera set, the legend, and the exchange shape.
- **M2A completes the manual four-case engineering study before M3 promotion.** It does not wait for M2’s LLM tasks; reuse evidence where applicable and re-estimate the schedule.
- **No agent work before V1 and V3 pass.** An agent reasoning over wrong physics produces confident nonsense that looks like a working demo.

---

## Timeline

Thu 17 Sep → Sat 3 Oct: **17 days**. Each task shows its window and an effort band. A milestone ends on the day the next one starts, and that shared day holds the handover work.

### Milestone windows

The dated table below is the original M1–M6 baseline. M2A adds seven required tasks with effort and dates to be estimated; totals and daily effort below exclude M2A.

| Milestone | Window | Days | Must tasks | Should | Must effort |
| --- | --- | --- | --- | --- | --- |
| **M1** Foundations and de-risking | 17 Sep → 19 Sep | 3 | 9 | — | 15–25 h |
| **M2** One part, one load case, walked by hand | 19 Sep → 22 Sep | 4 | 9 | — | 20–34 h |
| **M3** Engineering loop, no agent | 23 Sep → 25 Sep | 3 | 8 | 1 | 19–30 h |
| **M4** The agent loop closes | 26 Sep → 28 Sep | 3 | 8 | — | 16–24 h |
| **M5** Judgement | 29 Sep → 1 Oct | 3 | 10 | — | 20–32 h |
| **M6** Refusal and packaging | 1 Oct → 3 Oct | 3 | 5 | 2 | 10–17 h |
| **Total** | **17 → 3 Oct** | **17** | **49** | **3** | **100–162 h** |

That is **5.9–9.5 h a day, every day, weekends included**. The Must work only fits at the low end of every band, so the plan carries **dated cut triggers** instead of a cut list to consult when things are already late.

### Cut triggers

| Check on | If this is not true | Then |
| --- | --- | --- |
| End of 19 Sep | Gates 2b, 3 and 4 pass | Take the Gate 2b or Gate 4 fallback in [M1](#m1--foundations-and-de-risking-1719-sep). If Gate 3 fails, stop and re-plan, because nothing downstream runs |
| End of 21 Sep | `ge_bracket` meshes and solves by hand in ≤ 60 s (half model) | Switch the demo part to `L_bracket` (D-14 fallback). M2.1–M2.5 repeat on it for about 6 h |
| End of 22 Sep | The integration spec exists | Merge M2.10 into M2.9. M3 may proceed once the manual M2A exit criterion is met; the LLM spec is M4's input, not M3's |
| End of 25 Sep | V1 and V3 pass | Reduce V3 to reactions balance only. Release is still gated on V1 |
| End of 28 Sep | One scored cycle is on disk | Drop M5.10 to a one-page skill and fold M5.9 into M5.7 |
| End of 1 Oct | Detection and false-positive rates are computed | Ship with the mutation numbers as they stand. M6.4 and M6.7 are not cut |

Should items (M3.6, M6.5, M6.6, and requirements' LC2 tasks and second mutant instances) start only when their milestone's exit criterion has already been met.

### Task ranges

**M1 — Foundations and de-risking** · 17 Sep → 19 Sep

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M1.8 Go through the Session 17 video — time-boxed to 1 h | [#54](https://github.com/sujitojha1/3d-part-optimization-agent/issues/54) | 17 Sep | 17 Sep | 1 h |
| M1.10 Fetch SimJEB sample and metadata by pinned file ID and checksum into gitignored data/ | [#56](https://github.com/sujitojha1/3d-part-optimization-agent/issues/56) | 17 Sep | 17 Sep | 1–2 h |
| M1.6 Create the FEM environment — FreeCAD (FEM and CAM), Gmsh, CalculiX from a conda-forge explicit lock | [#6](https://github.com/sujitojha1/3d-part-optimization-agent/issues/6) | 17 Sep | 18 Sep | 3–5 h |
| M1.7 GATE 3 — run FreeCAD's bundled CalculiX cantilever headless and reproduce -86.93 mm | [#10](https://github.com/sujitojha1/3d-part-optimization-agent/issues/10) | 18 Sep | 18 Sep | 2–3 h |
| M1.11 GATE 4 — a FreeCAD CAM Job runs headless: operations, post-processed G-code, PathSimulator stock | [#58](https://github.com/sujitojha1/3d-part-optimization-agent/issues/58) | 18 Sep | 18 Sep | 2–4 h |
| M1.4 GATE 2a — prove pyvista renders off-screen on macOS | [#4](https://github.com/sujitojha1/3d-part-optimization-agent/issues/4) | 18 Sep | 19 Sep | 1–3 h |
| M1.9 Verify all LLM providers, refresh the model list and .env, add a second Gemini API key | [#55](https://github.com/sujitojha1/3d-part-optimization-agent/issues/55) | 19 Sep | 19 Sep | 1 h |
| M1.5 GATE 2b — prove an image reaches a vision model through glc_v5 | [#5](https://github.com/sujitojha1/3d-part-optimization-agent/issues/5) | 19 Sep | 19 Sep | 2–3 h |
| M1.3 GATE 1 — configure the S17 environment and prove a prompt routes 8113 to 8111 | [#3](https://github.com/sujitojha1/3d-part-optimization-agent/issues/3) | 19 Sep | 19 Sep | 2–3 h |

**M2 — One part, one load case, walked by hand** · 19 Sep → 22 Sep

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M2.1 Build the parametric ge_bracket FreeCAD document and freeze its parameter record | [#44](https://github.com/sujitojha1/3d-part-optimization-agent/issues/44) | 19 Sep | 20 Sep | 4–6 h |
| M2.2 Freeze the LC1 load record, SF, displacement limit and pin-load model, with a hand calculation | [#46](https://github.com/sujitojha1/3d-part-optimization-agent/issues/46) | 20 Sep | 20 Sep | 2–4 h |
| M2.3 Hand-mesh ge_bracket with FemMeshGmsh at nominal and minimum fillet | [#45](https://github.com/sujitojha1/3d-part-optimization-agent/issues/45) | 20 Sep | 21 Sep | 2–4 h |
| M2.4 Verify mesh groups and face predicates survive into the .inp at parameter bounds | [#47](https://github.com/sujitojha1/3d-part-optimization-agent/issues/47) | 21 Sep | 21 Sep | 2–3 h |
| M2.5 Hand-run the ccxtools solve, parse it and measure it | [#48](https://github.com/sujitojha1/3d-part-optimization-agent/issues/48) | 21 Sep | 21 Sep | 2–4 h |
| M2.6 Render the contour by hand and judge whether it is readable | [#49](https://github.com/sujitojha1/3d-part-optimization-agent/issues/49) | 21 Sep | 22 Sep | 2–3 h |
| M2.7 Run one real exchange through glc_v5 by hand, image-only and image-plus-numbers | [#50](https://github.com/sujitojha1/3d-part-optimization-agent/issues/50) | 22 Sep | 22 Sep | 3–5 h |
| M2.9 Write the LLM integration spec | [#52](https://github.com/sujitojha1/3d-part-optimization-agent/issues/52) | 22 Sep | 22 Sep | 2–3 h |
| M2.10 Walkthrough record and plan delta | [#53](https://github.com/sujitojha1/3d-part-optimization-agent/issues/53) | 22 Sep | 22 Sep | 1–2 h |

**M3 — Engineering loop, no agent** · 23 Sep → 25 Sep

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M3.1 Promote the ge_bracket FreeCAD document — parameters in, predicate-selected faces out | [#11](https://github.com/sujitojha1/3d-part-optimization-agent/issues/11) | 23 Sep | 23 Sep | 2–4 h |
| M3.2 FemMeshGmsh sizing per D-24, with the negative-Jacobian retry | [#12](https://github.com/sujitojha1/3d-part-optimization-agent/issues/12) | 23 Sep | 23 Sep | 2–3 h |
| M3.3 FEM analysis assembly — material, rigid-body supports, pin load, symmetry — written by ccxtools | [#13](https://github.com/sujitojha1/3d-part-optimization-agent/issues/13) | 23 Sep | 24 Sep | 3–5 h |
| M3.4 Parse .frd to full-part mass, max von Mises, max displacement, peak region label | [#14](https://github.com/sujitojha1/3d-part-optimization-agent/issues/14) | 24 Sep | 24 Sep | 3–4 h |
| M3.5 V1 validation — FreeCAD cantilever and a slender cantilever against closed form | [#15](https://github.com/sujitojha1/3d-part-optimization-agent/issues/15) | 24 Sep | 24 Sep | 2–3 h |
| M3.9 V3 validation — SimJEB design 148 LC1 displacement against the OptiStruct field | [#57](https://github.com/sujitojha1/3d-part-optimization-agent/issues/57) | 24 Sep | 25 Sep | 4–6 h |
| M3.7 Contour renderer with fixed camera set and locked legend range | [#17](https://github.com/sujitojha1/3d-part-optimization-agent/issues/17) | 25 Sep | 25 Sep | 2–3 h |
| M3.8 Measure per-iteration wall time and confirm or revise the budget | [#18](https://github.com/sujitojha1/3d-part-optimization-agent/issues/18) | 25 Sep | 25 Sep | 1–2 h |
| M3.6 V2 validation (Should) — shoulder-fillet stepped bar against a published Kt | [#16](https://github.com/sujitojha1/3d-part-optimization-agent/issues/16) | 25 Sep | 25 Sep | 3–5 h |

**M4 — The agent loop closes** · 26 Sep → 28 Sep

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M4.1 Register run_sim, read_result and check_manufacturing as rerunnable capabilities | [#19](https://github.com/sujitojha1/3d-part-optimization-agent/issues/19) | 26 Sep | 26 Sep | 3–4 h |
| M4.2 Task schema and validation, including unit-consistency rejection | [#20](https://github.com/sujitojha1/3d-part-optimization-agent/issues/20) | 26 Sep | 26 Sep | 2–3 h |
| M4.8 Material library — 5 machinable alloys, all D-10 fields with cited sources | [#26](https://github.com/sujitojha1/3d-part-optimization-agent/issues/26) | 26 Sep | 26 Sep | 1–2 h |
| M4.3 Baseline evaluation and invalid-baseline termination | [#21](https://github.com/sujitojha1/3d-part-optimization-agent/issues/21) | 27 Sep | 27 Sep | 1–2 h |
| M4.4 Vision step — contour into the model, concentration recorded as a region label | [#22](https://github.com/sujitojha1/3d-part-optimization-agent/issues/22) | 27 Sep | 27 Sep | 3–4 h |
| M4.5 Single-edit enforcement in the runtime, mesh changes refused | [#23](https://github.com/sujitojha1/3d-part-optimization-agent/issues/23) | 27 Sep | 28 Sep | 2–3 h |
| M4.6 Prediction record in the D-07 schema, persisted before the tool call | [#24](https://github.com/sujitojha1/3d-part-optimization-agent/issues/24) | 28 Sep | 28 Sep | 2–3 h |
| M4.7 Score the prediction against the next evaluation as three booleans | [#25](https://github.com/sujitojha1/3d-part-optimization-agent/issues/25) | 28 Sep | 28 Sep | 2–3 h |

**M5 — Judgement** · 29 Sep → 1 Oct

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M5.1 Structural and mass verifiers, with invalid results never passing | [#27](https://github.com/sujitojha1/3d-part-optimization-agent/issues/27) | 29 Sep | 29 Sep | 2–3 h |
| M5.2 cnc_3axis check — CAM Workbench job per setup, PathSimulator residual stock, minimum wall | [#28](https://github.com/sujitojha1/3d-part-optimization-agent/issues/28) | 29 Sep | 29 Sep | 5–8 h |
| M5.4 Load-direction check against the generated .inp | [#30](https://github.com/sujitojha1/3d-part-optimization-agent/issues/30) | 29 Sep | 29 Sep | 1–2 h |
| M5.10 The FEA-reasoning SKILL.md | [#36](https://github.com/sujitojha1/3d-part-optimization-agent/issues/36) | 29 Sep | 1 Oct | 2–3 h |
| M5.3 Singularity protocol — halved MeshRegion re-solve, 20% rule calibrated on ge_bracket | [#29](https://github.com/sujitojha1/3d-part-optimization-agent/issues/29) | 30 Sep | 30 Sep | 3–4 h |
| M5.5 The 3-task set with an executable predicate each | [#31](https://github.com/sujitojha1/3d-part-optimization-agent/issues/31) | 30 Sep | 30 Sep | 2–3 h |
| M5.6 The 3-mutant corpus with paired valid controls | [#32](https://github.com/sujitojha1/3d-part-optimization-agent/issues/32) | 30 Sep | 30 Sep | 2–3 h |
| M5.7 Report detection fraction and control false-positive rate | [#33](https://github.com/sujitojha1/3d-part-optimization-agent/issues/33) | 1 Oct | 1 Oct | 1–2 h |
| M5.8 Enforce protected paths and record every refusal | [#34](https://github.com/sujitojha1/3d-part-optimization-agent/issues/34) | 1 Oct | 1 Oct | 1–2 h |
| M5.9 Offline rescoring with model and solver disabled | [#35](https://github.com/sujitojha1/3d-part-optimization-agent/issues/35) | 1 Oct | 1 Oct | 1–2 h |

**M6 — Refusal and packaging** · 1 Oct → 3 Oct

| Task | Issue | Start | Target | Effort |
| --- | --- | --- | --- | --- |
| M6.1 Budget and repeat-failure ceilings, and the six terminal outcomes | [#37](https://github.com/sujitojha1/3d-part-optimization-agent/issues/37) | 1 Oct | 2 Oct | 2–3 h |
| M6.2 Explored frontier with scoped infeasibility wording | [#38](https://github.com/sujitojha1/3d-part-optimization-agent/issues/38) | 2 Oct | 2 Oct | 2–3 h |
| M6.3 Link the recommendation to baseline, change history and evidence | [#39](https://github.com/sujitojha1/3d-part-optimization-agent/issues/39) | 2 Oct | 2 Oct | 1–2 h |
| M6.4 Clean-machine run on macOS — one documented command from the pinned locks | [#40](https://github.com/sujitojha1/3d-part-optimization-agent/issues/40) | 2 Oct | 2 Oct | 2–4 h |
| M6.7 README and demo video, including the failures and the refusal | [#43](https://github.com/sujitojha1/3d-part-optimization-agent/issues/43) | 2 Oct | 3 Oct | 3–5 h |
| M6.5 Skill A/B (Should) — one task with and without the SKILL.md | [#41](https://github.com/sujitojha1/3d-part-optimization-agent/issues/41) | 3 Oct | 3 Oct | 2–3 h |
| M6.6 Run report (Should) — mass delta, margins, prediction accuracy, mutation detection | [#42](https://github.com/sujitojha1/3d-part-optimization-agent/issues/42) | 3 Oct | 3 Oct | 2–3 h |

M1.1 (#1) and M1.2 (#2) are closed. M2.8 (#51) is merged into M2.7. M1.11 (#58) is new in v0.5. Rows marked *(Should)* are excluded from the effort totals.

**Ordering the dates respect:**

- M1.10 precedes M1.4, because Gate 2a renders a SimJEB field. M1.6 precedes M1.7 and M1.11.
- M2.1 needs M1.10, because the interface coordinates come from SimJEB.
- M2.8 is merged into M2.7 (#51 closed), since both experiments use the same session.
- M3.9 needs M3.3 and M3.4. No M4 work starts before M3.5 and M3.9 pass.
- M5.7 needs M5.5 and M5.6. M6.4 runs against the finished locks, so only the README and video follow it.
- M4.8, the material library, has no upstream dependency. Pull it into any blocked hour.

---

## M1 — Foundations and de-risking (17–19 Sep)

**Expectation.** Four things in this project have never run together on this Mac. Finding out in M3 that one of them does not work would cost the project. M1 writes no engineering code, and each gate is answered by running something, not by reading.

**Exit criterion.** Gates 1–4 all pass, or a named fallback is chosen and written down.

| Gate | Question |
| --- | --- |
| 1 | Does a prompt route 8113 → 8111 and come back, with both test suites green? |
| 2 | Can a contour image be rendered off-screen here **and** reach a vision model through the gateway? |
| 3 | Does FreeCAD, run headless from the FEM environment, mesh and solve its bundled CalculiX cantilever and reproduce −86.93 mm? |
| 4 | Does a FreeCAD CAM Job run headless — operations recompute, G-code post-processes, and `PathSimulator` returns a stock mesh? |

**Tasks.** Most of the time goes to M1.6, which builds the FEM environment:

1. Install a pinned `micromamba` binary.
2. Solve `freecad=1.1.3`, `gmsh=4.15.2`, `calculix=2.23`, `pyvista` and `ccx2paraview` for `osx-arm64` once.
3. Freeze the result as an explicit lock (package URLs plus SHA-256) and create `vendor/fem-env` from that lock.
4. Commit the lock, not the environment.

M1.7 then runs `ccxtools` on FreeCAD's bundled cantilever through `vendor/fem-env/bin/python`, and it doubles as V1's first half. M1.11 builds a CAM Job headless on a pocketed test block, using the pattern FreeCAD's own `CAMTests` use (`Path.Main.Job.Create`, `Path.Op.Profile.Create`, GUI calls guarded off). It adds Adaptive, Profile and Drilling operations from a committed ToolBit library, post-processes G-code, and replays it through `PathSimulator.PathSim` (`BeginSimulation`, `ApplyCommand`, `GetResultMesh`). A test block with a deliberate undercut must show residual stock, and the same block without it must not. Time each step, because the check runs on every evaluation.

**Gate 2b fallbacks, in preference order:**

1. Add a multimodal path to your own `glc_v5` fork. It is your fork, and this doubles as a course Part-2 contribution.
2. Call the vision model directly from the capability, route only text through the gateway, and document the deviation.
3. Drop to a numeric-plus-region-label encoding, and revise the intent's vision claim honestly.

**Gate 4 fallback.** If `PathSimulator` will not run headless, keep the CAM Job and `cam_ops` rule, and replace `residual_stock` with ray-cast tool access along each setup direction plus concave radius ≥ smallest tool radius (D-11).

**Gate 3 fallback.** If conda-forge FreeCAD will not run headless, use the signed FreeCAD 1.1.3 app's `FreeCADCmd` with conda-forge `calculix` beside it. The package pins change; the architecture does not.

---

## M2 — One part, one load case, walked by hand (19–22 Sep)

**Expectation.** M1 proves that each tool runs, and M3 automates the pipeline. Between them sits an untested assumption: that FreeCAD → Gmsh → CalculiX composes *on this bracket*, and that the agent's information survives the chain. That means faces that stay selected after a parameter change, mesh groups that reach the `.inp`, a contour a human can read, and numbers that arrive in the right order. One deliberate pass by hand, with eyes on every intermediate artifact, is the cheapest place to find out.

The FreeCAD document built in M2.1 **is kept** and becomes M3.1's starting point. Everything else here is scratch.

**Exit criterion.** Three things are true:

- `ge_bracket` and its LC1 record are frozen in writing.
- A hand pass from spreadsheet parameters to a contour PNG exists, with every intermediate artifact kept.
- The LLM integration is specified and backed by at least one real exchange through `glc_v5` that returned a region label from the closed set and a complete D-07 prediction.

**Tasks**

1. **Build the parametric `ge_bracket` and freeze it** (M2.1).
   - Build a FreeCAD document with a Spreadsheet of named parameters: base plate, four bolt bosses, two clevis arms, arm-root fillets, and base pockets or lightening holes. Place the interfaces at SimJEB's coordinates: pin Ø 19.05 mm, bolt holes Ø 9.525 mm.
   - Write the frozen record: baseline values, at most six parameters, each with its D-05 kind and min/max/step, and every thickness ≥ 1.27 mm.
   - Write the D-06 region labels, and one **geometric face predicate** per constraint, mesh group and CAM operation (D-04).
   - Declare the `cnc_3axis` setups (top, bottom, side for the pin bore and arm profile) and the ToolBit library. Record, for each `fillet_radius`, the smallest tool radius that can cut it.
   - Record why the other parts are deferred, and the `L_bracket` fallback trigger.
2. **Freeze the load case** (M2.2).
   - LC1 `(0, 0, +35,585.77) N` in the SimJEB frame. Ti-6Al-4V at 903 MPa, SF 1.5 (602 MPa allowable), and a displacement limit of 1.1 × baseline.
   - **Choose the pin-load model.** FreeCAD has no `*DISTRIBUTING COUPLING` tool, so try both options — a Rigid Body Constraint on the bore with the force at its reference point, or a Force constraint on the upper half-bore — and record the choice. The challenge calls the pin infinitely stiff, which argues for the first.
   - **Decide on the half model** (D-23).
   - Record that the bolt-hole rigid supports are a singularity source, not only the load ([fem-geometry-preparation §13](fem-geometry-preparation.md)).
   - Hand-calculate that the baseline passes and where the peak should land.
3. **Hand-mesh** (M2.3). Use `FemMeshGmsh` with D-24's max size, min size and `MeshRegion`, at nominal `arm_root_fillet` **and at its minimum**. Watch for negative Jacobians and try `SecondOrderLinear` if they appear. Keep element counts and timings.
4. **Verify the label chain survives** (M2.4).
   - Mesh Groups → `.inp` element sets, checked by reading the deck: every D-06 label is present, non-overlapping, and covers the part.
   - At each parameter's min and max, every face predicate matches exactly one face.
   - This is where the checkable-spatial-claim promise, and the topological-naming risk, get settled.
5. **Hand-run the solve and parse it** (M2.5).
   - Run `ccxtools` `write_inp_file` → `ccx_run` → `load_results`.
   - Extract full-part mass in grams, max von Mises, max displacement, and peak element → label.
   - Compare with M2.2's hand calculation and record wall time. **This is the `L_bracket` trigger.**
6. **Hand-render the contour and judge its readability** (M2.6).
   - Fixed cameras and a locked legend. Is `arm_root_fillet` versus `clevis_arm` versus `bolt_boss` visibly distinguishable at this image size, camera count and colormap? Fix those settings now.
   - Apply the same settings to SimJEB design 148 from `148.csv`. If a setting only works on our bracket, record that as a finding.
7. **Run one real exchange through `glc_v5`, both ways** (M2.7, which absorbs M2.8).
   - Send the contour plus prompt by hand. Does the model name a region from the closed set, and fill D-07 unaided?
   - Repeat with the numerics added, and check whether the region claim moves. That settles architecture question 1.
   - Keep the transcripts, token counts and latency.
8. **Write the LLM integration spec** (M2.9). Cover turn structure, image encoding and size, the prompt and response contracts, where the single-edit rule is enforced, what belongs in `SKILL.md` versus the runtime, and the cost and latency of one iteration.
9. **Write the walkthrough record and plan delta** (M2.10). One page covering what the pass proved and what broke, the frozen records, measured timings, and every decision this milestone changes: D-13, D-23, D-24, the render settings, and architecture questions 1, 2 and 6.

---

## M2A — Manual GE challenge analysis and CAM readiness (unscheduled)

**Expectation.** Manually establish the complete engineering study on the selected geometry before automating it. No agent or LLM setup is required.

**Exit criterion.** One frozen geometry, accepted mesh-quality and convergence report, five sourced material cards, fixed nut locations and lug load transfer, four independent load cases, a 20-combination stress/mass/displacement report with maps, and a documented CAM readiness assessment.

**Selected geometry:** `data/simjeb/Iteration1.stp`, the closest visual match among seven local candidates to the GE challenge images. See [the comparison and checksum](ge-geometry-comparison.md). M2A.1 still verifies provenance, units, dimensions, interfaces and the load-frame transform before analysis. This selection applies to the manual study; `parts/ge_bracket.FCStd` remains the separate parametric agent baseline.

**Study matrix:** Ti-6Al-4V, Al 7075-T6, Al 6061-T6, 17-4PH and 4140 steel, each under LC1 vertical, LC2 horizontal, LC3 diagonal (42° from vertical), and LC4 torsion. Twenty manual analyses report stress maps, maximum von Mises stress, mass and maximum displacement; the CAM assessment covers the selected geometry and material-specific tooling/setup assumptions.

See [M2A detailed steps](ge-manual-workflow.md) for procedures, dependencies and acceptance criteria.

[GitHub milestone](https://github.com/sujitojha1/3d-part-optimization-agent/milestone/7)

| Task | Issue | Schedule |
| --- | --- | --- |
| M2A.1 Identify and freeze the selected GE geometry file | [#59](https://github.com/sujitojha1/3d-part-optimization-agent/issues/59) | Unassigned |
| M2A.2 Document manual meshing steps and report mesh quality | [#60](https://github.com/sujitojha1/3d-part-optimization-agent/issues/60) | Unassigned |
| M2A.3 Prepare and assign five material options manually | [#61](https://github.com/sujitojha1/3d-part-optimization-agent/issues/61) | Unassigned |
| M2A.4 Fix the four nut locations and define lug load transfer | [#62](https://github.com/sujitojha1/3d-part-optimization-agent/issues/62) | Unassigned |
| M2A.5 Set up four independent GE static load cases | [#63](https://github.com/sujitojha1/3d-part-optimization-agent/issues/63) | Unassigned |
| M2A.6 Run the manual material/load matrix and publish stress, mass and displacement report | [#64](https://github.com/sujitojha1/3d-part-optimization-agent/issues/64) | Unassigned |
| M2A.7 Walk through CAM readiness manually and document blockers | [#65](https://github.com/sujitojha1/3d-part-optimization-agent/issues/65) | Unassigned |

M2A expands the manual engineering study; the existing agent task remains LC1 until separately revised. Ti-6Al-4V is the GE material baseline; other materials and CNC readiness are project extensions. Dates and effort are not yet assigned; the old M3 window must be reviewed against this added predecessor.

---

## M3 — Engineering loop, no agent (23–25 Sep)

**Expectation.** Prove the physics before adding judgement. Every downstream number inherits the solver's correctness, so this milestone ends with evidence the FEA is right, not merely running.

**Exit criterion.** A script in the FEM environment takes a parameter dict and returns `{mass_g, max_vm, max_disp, peak_region, contour_png}`, and V1 and V3 pass.

**Tasks**

1. **Promote the M2.1 document** (M3.1): parameters in, recompute, faces re-selected by predicate, with `unverified` when a predicate does not match exactly one face (`REQ-OPT-008`).
2. **Mesh sizing** (M3.2): `FemMeshGmsh` sizing per D-24, with one retry under `SecondOrderLinear` when elements invert, and a mesh diagnostic otherwise.
3. **Analysis assembly** (M3.3): material card with explicit units, Rigid Body Constraints at the bolt holes, the M2.2 pin-load model, and the D-23 symmetry constraint, written by **`ccxtools`**. Read `femtools/ccxtools` and its `.inp` writer before extending anything. Remember that a failed write can return an empty path even though the file exists ([freecad-tutorials §4.2](freecad-tutorials.md)).
4. **Result parsing** (M3.4): `.frd` → mass for the full part, max von Mises, max displacement, peak region label. Add an element count by type as a sanity check: a count that changes when only the material changed means something is wrong upstream.
5. **V1** (M3.5): FreeCAD's bundled cantilever must reproduce −86.93 mm, and a slender cantilever (*L*/*h* ≥ 20) must agree with `δ = PL³/3EI` and `σ = Mc/I` within a **signed** band. A clamped stubby bar reads stiff, so a symmetric tolerance around the formula would hide that offset.
6. **V3** (M3.9): import `148.stp` and mesh at SimJEB's sizes (2.0 mm average, 0.6 mm minimum). Add Rigid Body Constraints at the four bolt holes, the M2.2 pin model, and LC1 only.
   - **Section Print** first, to confirm reactions sum to the applied load.
   - Then compare nodal displacement magnitude against `148.csv`.
   - Compare displacement only.
   - SimJEB used RBE3 at the pin. If our pin model differs, a disagreement near the bore is expected, so record it rather than tuning it away.
7. **Renderer** (M3.7): contour PNG with a fixed camera set and a legend range locked across a run (`REQ-OPT-001`).
8. **Budget check** (M3.8): measure per-iteration wall time, CAM jobs and simulation included, and confirm or revise D-13. Levers, in order: half model, min element size, and only then a coarser base mesh.
9. *Should:* **V2** (M3.6), a stepped bar against a published `Kt`.

---

## M4 — The agent loop closes (26–28 Sep)

**Expectation.** The agent reads a picture, commits to a prediction *before* acting, makes exactly one change, and is scored against what actually happened. The prediction-before-execution ordering is the whole novelty; it is worthless if written afterwards.

**Exit criterion.** A run record on disk shows an image input, a prediction persisted before its tool call, and that prediction scored against the next evaluation.

**Tasks**

1. Register `run_sim`, `read_result` and `check_manufacturing` as capabilities, **declared rerunnable**. Each one calls into `vendor/fem-env` as a subprocess and returns errors as values. *(D-19, `REQ-DEL-010`)*
2. Task schema and validation, including unit-consistency rejection with the offending field named. *(`REQ-IN-001`, `REQ-IN-002`)*
3. Baseline evaluation and `invalid-baseline` termination. *(`REQ-IN-003`, `REQ-IN-004`)*
4. Vision step: contour image into the model, with the identified concentration recorded as one region label. *(`REQ-OPT-002`)*
5. Single-edit enforcement **in the runtime**, with mesh-altering proposals refused. The edit is a spreadsheet cell or a material ID and nothing else. *(`REQ-OPT-003`, D-21)*
6. Prediction record in the D-07 schema, persisted with its rationale before the tool call. *(`REQ-OPT-004`)*
7. Prediction scoring against the next valid evaluation: region, direction and band as three booleans. *(`REQ-OPT-005`)*
8. Material library JSON: 5 machinable alloys — Ti-6Al-4V, Al 7075-T6, Al 6061-T6, 17-4PH, 4140 — with all D-10 fields, a cited machinability index, with explicit nulls and a cited source each, plus the exclusion rule. Ti-6Al-4V uses E = 113.8 GPa and ν = 0.342, matching SimJEB, with one cited density; SimJEB's deck (4.43 g/cm³) and its metadata (4.47) disagree. *(`REQ-OPT-006`, `REQ-OPT-007`)*

> Task 1 will cost a day if it is missed. The harness deduplicates identical capability calls, but re-solving the same parameters after an edit is not a duplicate. Without the declaration, the loop silently stops iterating and looks like a hang.

---

## M5 — Judgement (29 Sep – 1 Oct)

**Expectation.** The verifiers decide, not the prose. This milestone produces the numbers the project is graded on, and puts the judge beyond the agent's reach.

**Exit criterion.** Mutation detection fraction and control false-positive rate are computed from stored records, and scoring runs with the model and solver disabled.

**Tasks**

1. Structural and mass verifiers. Invalid results are classified `unverified` and never pass. *(`REQ-VER-001`, `REQ-VER-002`, `REQ-VER-004`)*
2. `cnc_3axis` check in the CAM Workbench, per declared setup: create the CAM Job headless with Adaptive, Profile and Drilling operations on predicate-selected faces; recompute; run Sanity Check; post-process G-code; replay through `PathSimulator`. The rules are `cam_ops` (non-empty paths, no errors), `residual_stock` (every part-surface sample reached within 0.2 mm by some setup, no setup cutting into the part) and `min_wall` (≥ 1.27 mm by ray cast). A CAM error or missing simulator result is `invalid`. Builds on Gate 4. *(`REQ-VER-003`, D-11)*
3. Singularity protocol: halve the `MeshRegion` size, apply the 20% rise rule, and classify the result unverified unless it survives. Calibrate the threshold on `ge_bracket`, with `arm_root_fillet` at nominal against zero, at 3–4 refinement levels, so the threshold sits on a curve and not a slope. *(`REQ-VER-005`, D-12)*
4. Load-direction check, comparing task intent with the generated `.inp`. *(`REQ-VER-006`)*
5. The 3-task set — geometry-led, material-led, unachievable-target — each with an executable predicate that reads only structured output. Calibrate the unachievable target against the explored space and SimJEB's LC1 results. *(`REQ-DEL-004`, D-15)*
6. The 3-mutant corpus with paired controls: `arm_root_fillet = 0`, LC1 sign-flipped, and the Ti card in Pa declared as MPa. *(`REQ-DEL-005`, D-16)*
7. Detection-fraction and false-positive reporting, with zero executions reported as `not evaluated`. *(`REQ-DEL-005`)*
8. Protected paths enforced over verifiers, tasks, materials, mutations and tooling, with every refusal recorded. *(`REQ-DEL-011`, D-20)*
9. Offline rescoring with model and solver access disabled. *(`REQ-DEL-007`)*
10. The FEA-reasoning `SKILL.md`: behaviour in markdown, never authority. Write it from [fem-geometry-preparation §12–13](fem-geometry-preparation.md) — the four singularity causes and four remedies, why displacement converges when stress does not, and why a rigid support at a bolt hole reads hot.

---

## M6 — Refusal and packaging (1–3 Oct)

**Expectation.** The most interesting result in the intent is the honest no. Ship the frontier, the scoped refusal, and a package someone else can run. Then show it failing as well as working.

**Exit criterion.** A clean macOS arm64 account runs one documented command from the pinned locks and produces a result.

**Tasks**

1. Budget and repeat-failure ceilings, and the six terminal outcomes. *(`REQ-OUT-001`, `REQ-OUT-002`)*
2. Explored frontier with scoped infeasibility wording, never a universal claim. *(`REQ-OUT-003`)*
3. Recommendation linked to baseline comparison, change history and stored evidence. *(`REQ-OUT-004`)*
4. Clean-machine run on a fresh macOS user account: one command that installs the FEM lock and the harness lock, then runs a bundled task. This is on 2 Oct, not the last day. *(`REQ-DEL-003`)*
5. README someone can follow, and the demo video, including the failure cases and the refusal. The README cites SimJEB and the GE challenge as their licences require, and says the SimJEB files are fetched, not shipped.
6. *Should:* skill A/B, one task with and without `SKILL.md`. *(`REQ-DEL-013`)*
7. *Should:* run report covering mass delta, margins, prediction accuracy and mutation detection. *(`REQ-DEL-012`)*

---

## Reference — the stack

The intent's stack, on macOS arm64. Availability was checked on 2026-09-17; nothing has been run yet.

| Layer | Choice | Status |
| --- | --- | --- |
| Parametric CAD | FreeCAD 1.1.3, conda-forge `osx-arm64` (Python 3.11) | **Available** — build `freecad-1.1.3-py311h7740527_0`. Headless run unproven (Gate 3) |
| Mesh | Gmsh 4.15.2, conda-forge, driven by `FemMeshGmsh` | **Available** — FreeCAD's conda package depends on it |
| FEA | CalculiX `ccx` 2.23, conda-forge `calculix-2.23-pl5321h33a25c5_4` | **Available** — links arpack, BLAS, gfortran and OpenMP, so it installs from the lock, not a zip |
| Manufacturability | FreeCAD CAM Workbench and `PathSimulator`, in the same conda-forge FreeCAD | **Available**. FreeCAD's own `CAMTests` build Jobs and operations headless, and `PathSimulator` is an App module with a Python API. Not yet run here (Gate 4) |
| Result parsing and render | `ccx2paraview`, `pyvista` in the FEM environment | Off-screen rendering on macOS unproven (Gate 2a) |
| Harness | S17Code fork, its own `uv` lock | Forked and green (M1.1) |
| Reference data | SimJEB sample (design 148) and metadata, Harvard Dataverse | Pins in [simjeb-dataset.md](simjeb-dataset.md). Dev-time only, never shipped |

Nothing binary is committed. The FEM environment — FreeCAD with its FEM and CAM workbenches, Gmsh, and CalculiX (GPL, while this repo is public) — is fetched from an explicit lock of package URLs plus SHA-256. The ToolBit library and post-processor choice are committed as data. SimJEB follows the same fetch-and-pin rule, because its CAD is licensed non-commercial.

---

## Reference — the demo problem

**`ge_bracket` — the demo part.** A parametric FreeCAD rebuild of the GE jet engine bracket: base plate, four bolt bosses, two clevis arms and arm-root fillets around SimJEB's interface coordinates. It uses LC1 vertical, Ti-6Al-4V at 903 MPa, SF 1.5, and the half model about the clevis midplane.

- The peak should land at the arm-root fillet or the bolt bosses. M2.2 predicts which, and M2.5 checks the prediction, so a correct visual reading is a checkable claim.
- The mass levers are wall thickness (base, arms), fillet radius, and pocket or lightening-hole size. All are ordinary 2.5D milling features, and the original GE bracket was a machined part.
- Setting `arm_root_fillet` to 0 gives the sharp-corner mutant, and flipping LC1 gives the wrong-direction mutant.
- The refusal target has an external reference: 381 human designs in SimJEB.

**V1 — cantilevers.** FreeCAD's bundled 8 m × 1 m × 1 m steel box must reproduce −86.93 mm, which is FreeCAD's own CalculiX answer. A slender bar must match closed form within a signed band. Together they validate units, material card, boundary conditions, element formulation and extraction. The slender bar also gives the Pa/MPa mutation a ground truth, where a unit error shows up as a factor of 10⁶.

**V3 — SimJEB design 148, LC1.** A real bracket with rigid supports at the bolt holes and a published nodal field. It is the only validation of the coupling setup the demo part itself uses, and it compares displacement, not stress.

**V2 — stepped bar (Should).** Checks the published `Kt`. D-12's calibration no longer depends on it.

**`L_bracket` — the fallback.** Switch to it if the 21 Sep trigger fires.

---

## Risk register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `glc_v5` cannot carry images | Kills the vision thesis | Gate 2b on 19 Sep, with three named fallbacks |
| FreeCAD will not run headless from the conda environment | No pipeline | Gate 3 on 18 Sep. Fallback: the signed app's `FreeCADCmd` with conda-forge `calculix` |
| **Topological naming:** a parameter change renumbers faces, and a constraint silently lands on the wrong face | A plausible, wrong result that every verifier passes | D-04's geometric predicates, re-evaluated after every recompute. M2.4 checks each at parameter bounds, and `REQ-OPT-008` makes an ambiguous match `unverified` |
| **Second-order meshing inverts elements at small fillet radii** | The agent's own `fillet_radius` edit fails at mesh time, not solve time | M2.3 meshes at the minimum radius. D-24 retries once with `SecondOrderLinear`, then marks the candidate `unverified` |
| `ge_bracket` solves too slowly for D-13 | The loop cannot finish 8 evaluations | Measured in M2.5, with the 21 Sep trigger. Levers in order: half model (D-23), min element size (D-24), coarser base mesh last, then `L_bracket` |
| No `*DISTRIBUTING COUPLING` in FreeCAD | The pin-load model differs from SimJEB's RBE3, so V3 disagrees near the bore | M2.2 chooses the pin model explicitly, and V3 records disagreement near the bore rather than tuning it away |
| `PathSimulator` will not run headless, or is too slow at a useful resolution | No `residual_stock` rule, or evaluations blow D-13 | Gate 4 measures both. Fallback: ray-cast tool access plus minimum concave radius (D-11). Simulator resolution is task data, like mesh size |
| CAM operations reference faces that renumber after a parameter change | Operations cut the wrong feature, or produce empty paths that read as "unmachinable" | The same D-04 predicates select CAM faces; M2.4 checks them at parameter bounds, and a zero or multiple match is `unverified`, not a manufacturing fail |
| The sharp-fillet mutant fails manufacturability as well as singularity | Detection could be credited to the wrong check | D-16 scores that mutant on the `REQ-VER-005` flag only |
| Off-screen render fails on macOS | No contour to read | Gate 2a. Fallback: matplotlib over the surface mesh |
| Label chain does not survive into the `.inp` | Spatial claims become unscoreable | M2.4, with element-centroid membership as the fallback (D-06) |
| The contour renders but cannot be read | The vision step degrades to noise while every metric still looks fine | M2.6, judged by eye |
| Capability dedupe swallows re-solves | The loop appears to hang | M4.1, asserted by a test |
| SimJEB licence: the CAD is non-commercial | A public commit breaks licence terms | Fetch by pinned ID and checksum into gitignored `data/` (M1.10); cite in the README (M6.7) |
| **Schedule:** 5.7–9.2 h/day with no slack, after a 5-day slip in M1 | M6 is squeezed and the package does not ship | Dated cut triggers above. M6.4 moved to 2 Oct |

---

## Not covered or not clear

Ranked. The first two are settled by M1 and M2; the rest are live.

1. **Images through the gateway are unproven.** → Gate 2b, then exercised on the real contour in M2.7.
2. **The pin-load model has no FreeCAD tool that matches SimJEB.** → M2.2.
3. **Material data provenance.** MatWeb's data is not freely redistributable, so use published handbook or public datasheet values, cited per record.
4. **Single process only.** The harness's JSON stores are unsafe across processes, so candidates cannot be evaluated in parallel. That is a real throughput ceiling.
5. **The Route B rubric is unstated.** The Session 16 and 17 rubrics in the class notes are different assignments.
6. **`OD-B` and `OD-C` are unset** — release thresholds and numeric tolerances. They are correctly deferred to M5 data, but required before calling anything acceptable.
7. **Machining the arm-root fillet needs a side setup.** The fillet's axis is horizontal, so a flat endmill from +z cannot cut it; a Profile from the side setup can. Whether a 2.5D Profile on the arm outline is enough, or a 3D operation (which needs `opencamlib`, not in the lock) is required, is settled in M2.1 on the real geometry.

---

## Parked questions

1. **What is the actual Route B rubric?** It decides where M6 effort goes.

v0.4's questions about the `S17Code` fork and the reusable base are closed: the fork exists and passes its tests (M1.1). Whether a vision model is configured in `glc_v5` is answered by Gate 2b.

---

## Standing decisions this plan adds

1. **Nothing is built on unvalidated physics.** V1 and V3 pass before M4 starts.
2. **The vision path is proven before it is depended on.** Gate 2b comes before all engineering work.
3. **The chain is walked by hand before it is automated.** One part and one load case, with every intermediate artifact inspected. The integration shape is measured, not assumed.
4. **The judge is unreachable.** Verifiers, tasks, materials, mutations and the ToolBit library are protected paths.
5. **The solver is a capability, not an allowlisted command.** A tight allowlist and a typed contract, crossing a process boundary into the FEM environment.
6. **Re-solving is not a duplicate.** Declared rerunnable, and asserted by a test.
7. **Binaries are fetched, never committed.** FreeCAD, Gmsh and CalculiX come from an explicit lock of URLs and SHA-256.
8. **Reference data is fetched, never committed, and never treated as ground truth.** SimJEB displacements are a cross-check; its first-order stresses are not a target.
9. **Faces are found by geometry, never by index.** Every constraint and mesh group is re-selected after every recompute.
10. **No new reference documents until M4 exits.** The stack's documentation — FEM, CAM, geometry preparation — is captured, and any further research is attached to the task that needs it.

---

## Revision log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-09 | Initial execution plan |
| 0.2 | 2026-09-09 | Design section and execution order |
| 0.3 | 2026-09-12 | M0.5 hand walk added |
| 0.4 | 2026-09-13 | Three-week timeline with per-task dates; GE bracket and SimJEB as reference inputs |
| 0.5 | 2026-09-17 | Re-planned from 17 Sep with a fixed 3 Oct end. Milestones renamed M1–M6 to match the board. macOS arm64 only. The intent's stack restored and centred on FreeCAD: FEM Workbench for Gmsh and CalculiX, CAM Workbench for manufacturability (no slicer). `ge_bracket` is the demo part, with `L_bracket` as fallback. Gate 4 (headless CAM Job and `PathSimulator`) added as M1.11; M2.8 merged into M2.7; V3 promoted and V2 made Should; 3 tasks, 3 mutants, 5 machinable alloys; skill A/B and run report made Should. Dated cut triggers replace the cut list. FreeCAD-reference changes 1–11 folded into tasks |

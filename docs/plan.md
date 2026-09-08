# Execution Plan — 3D Part Optimization Agent

| Attribute | Value |
| --- | --- |
| Version | 0.2 |
| Date | 2026-09-09 |
| Owner | Sujit Ojha |
| Budget | Four weeks, one engineer, plus a Phase 0 of about three days |
| Board | [Project #10](https://github.com/users/sujitojha1/projects/10) — milestones and tasks below are mirrored there |
| Companion documents | [Intent](intent.md) — why · [Requirements](requirements.md) — what · this — when and in what order |

Five milestones. Each states an **expectation** (what it is for), an **exit criterion** (a single observable fact that ends it), and its tasks. Where this document and `requirements.md` disagree, requirements win on *what* and this wins on *order*.

---

## Milestone map

| # | Milestone | Duration | Exit criterion |
| --- | --- | --- | --- |
| **M0** | Foundations and de-risking | ~3 days | Three gates pass |
| **M1** | Engineering loop, no agent | Week 1 | A parameter dict returns a verified result, and closed-form validation agrees |
| **M2** | The agent loop closes | Week 2 | One full cycle on disk: read → predict → edit → re-run → score |
| **M3** | Judgement | Week 3 | Mutation detection and false-positive rates are reportable numbers |
| **M4** | Refusal and packaging | Week 4 | Someone else runs one command on a clean machine and gets a result |

Two hard orderings: nothing depends on the vision path until M0 Gate 2 answers `OD-D`, and **no agent work starts before M1's closed-form validation passes**. An agent reasoning over wrong physics produces confident nonsense that looks like a working demo and is not caught later.

---

## M0 — Foundations and de-risking (~3 days)

**Expectation.** Three things in this project have never been run together. Finding out in week 2 that one of them does not work costs the project. M0 buys that knowledge for three days and writes no engineering code. Each gate is answered by running something, not by reading.

**Exit criterion.** Gates 1, 2 and 3 all pass, or a named fallback is chosen and written down.

| Gate | Question |
| --- | --- |
| 1 | Does a prompt route 8113 → 8111 and come back, with both test suites green? |
| 2 | Can a contour image be rendered off-screen here **and** reach a vision model through the gateway? |
| 3 | Does `ccx` solve a bundled example on this machine, from a script, exit code checked? |

**Tasks**

1. Fork and clone `S17Code`; `uv sync`; confirm 478 tests pass.
2. Clone the `glc_v5` fork, serve on 8111, configure provider keys at `/channels`.
3. Configure the S17 environment — control token, workspace, allowed commands, protected paths, skills dir — and prove a prompt routes 8113 → 8111. *(Gate 1)*
4. Prove `pyvista` renders off-screen on Windows with no display. *(Gate 2a)*
5. Prove an image reaches a vision-capable model through `glc_v5`; if not, choose and record a fallback. *(Gate 2b, resolves `OD-D`)*
6. Create the `uv` project and lock the CAD, mesh and render stack.
7. Fetch CalculiX 2.10 by pinned URL and SHA-256, unzip to a gitignored `vendor/`, solve a bundled example. *(Gate 3)*

**Gate 2 fallbacks, in preference order.** Add a multimodal path to your own `glc_v5` fork — it is your fork, and this doubles as a course Part-2 contribution. Or call the vision model directly from the capability, routing only text through the gateway, and document the deviation. Or drop to a numeric-plus-region-label encoding and revise the intent's vision claim honestly.

---

## M1 — Engineering loop, no agent (week 1)

**Expectation.** Prove the physics before adding judgement. Every downstream number — prediction accuracy, mutation detection, the frontier — inherits the solver's correctness, so this milestone ends with evidence the FEA is right rather than merely running.

**Exit criterion.** A script takes a parameter dict and returns `{mass_g, max_vm, max_disp, peak_region, contour_png}`, and the cantilever case agrees with closed form within tolerance.

**Tasks**

1. `L_bracket` CadQuery parametric model: named parameters per D-05, labeled regions per D-06.
2. Parameters → STEP → Gmsh second-order tet mesh, with local refinement at named regions only.
3. Mesh → CalculiX `.inp` writer: material card, single load case, supports.
4. `.frd` parser → mass in grams, max von Mises, max displacement, peak region label.
5. **V1 validation** — tip-loaded cantilever against `δ = PL³/3EI` and `σ = Mc/I`. *(`REQ-DEL-009`)*
6. **V2 validation** — shoulder-fillet stepped bar against a published `Kt`; use its refinement behaviour to calibrate D-12's 20% threshold.
7. Contour PNG renderer with a fixed camera set and a legend range locked across a run. *(`REQ-OPT-001`)*
8. Measure per-iteration wall time; confirm or revise D-13's budget of 8 evaluations in 20 minutes.

---

## M2 — The agent loop closes (week 2)

**Expectation.** The agent reads a picture, commits to a prediction *before* acting, makes exactly one change, and is scored against what actually happened. The prediction-before-execution ordering is the whole novelty; it is worthless if written afterwards.

**Exit criterion.** A run record on disk shows an image input, a prediction persisted before its tool call, and that prediction scored against the next evaluation.

**Tasks**

1. Register `run_sim`, `read_result` and `check_manufacturing` as capabilities, **declared rerunnable**. *(D-19, `REQ-DEL-010`)*
2. Task schema and validation, including unit-consistency rejection with the offending field named. *(`REQ-IN-001`, `REQ-IN-002`)*
3. Baseline evaluation and `invalid-baseline` termination. *(`REQ-IN-003`, `REQ-IN-004`)*
4. Vision step: contour image into the model, identified concentration recorded as one region label. *(`REQ-OPT-002`)*
5. Single-edit enforcement **in the runtime**, with mesh-altering proposals refused. *(`REQ-OPT-003`, D-21)*
6. Prediction record in the D-07 schema, persisted with its rationale before the tool call. *(`REQ-OPT-004`)*
7. Prediction scoring against the next valid evaluation — region, direction and band as three booleans. *(`REQ-OPT-005`)*
8. Material library JSON: 8 alloys, all D-10 fields with explicit nulls and a cited source each; exclusion rule for missing properties. *(`REQ-OPT-006`, `REQ-OPT-007`)*

> Task 1 is the one that will cost a day if missed. The harness deduplicates identical capability calls, and re-solving the same parameter set after an edit is not a duplicate — the geometry changed in between. Without the declaration the loop silently stops iterating and looks like a hang.

---

## M3 — Judgement (week 3)

**Expectation.** The verifiers decide, not the prose. This milestone produces the numbers the project is actually graded on, and puts the judge beyond the agent's reach.

**Exit criterion.** Mutation detection fraction and control false-positive rate are computed from stored records, and scoring runs with the model and solver disabled.

**Tasks**

1. Structural and mass verifiers, with invalid results classified `unverified` and never passing. *(`REQ-VER-001`, `REQ-VER-002`, `REQ-VER-004`)*
2. FDM manufacturing checker: ray-cast minimum wall, facet-normal overhang angle. *(`REQ-VER-003`, D-11)*
3. Singularity protocol: 0.5× local re-solve, 20% rise rule, unverified unless it survives. *(`REQ-VER-005`, D-12)*
4. Load-direction check comparing task intent against the generated `.inp`. *(`REQ-VER-006`)*
5. The 9-task set with an executable predicate each, reading only structured tool output. *(`REQ-DEL-004`)*
6. The 6-mutant corpus with paired valid controls. *(`REQ-DEL-005`)*
7. Detection-fraction and false-positive reporting, with zero executions reported as `not evaluated`. *(`REQ-DEL-005`)*
8. Protected paths enforced over verifiers, tasks, materials and mutations, with every refusal recorded. *(`REQ-DEL-011`, D-20)*
9. Offline rescoring with model and solver access disabled. *(`REQ-DEL-007`)*
10. The FEA-reasoning `SKILL.md` — behaviour in markdown, never authority.

---

## M4 — Refusal and packaging (week 4)

**Expectation.** The most interesting result in the intent is the honest no. Ship the frontier, the scoped refusal, and a package someone else can run — then show it failing as well as working.

**Exit criterion.** A clean Windows machine runs one documented command from the lockfile and produces a result.

**Tasks**

1. Budget and repeat-failure ceilings; the six terminal outcomes. *(`REQ-OUT-001`, `REQ-OUT-002`)*
2. Explored frontier with scoped infeasibility wording — never a universal claim. *(`REQ-OUT-003`)*
3. Recommendation linked to baseline comparison, change history and stored evidence. *(`REQ-OUT-004`)*
4. Clean-machine run: one documented command, lockfile only, no undeclared preinstalled dependency. *(`REQ-DEL-003`)*
5. Skill A/B — one task run with and without the `SKILL.md`, both stored, reporting the win and the cost. *(`REQ-DEL-013`)*
6. Run report: mass delta, constraint margins, prediction accuracy, mutation detection. *(`REQ-DEL-012`)*
7. README someone can follow, and the demo video — including the failure cases and the refusal.

---

## Reference — the verified stack

Probed on this machine: Python 3.13.3, `uv` 0.6.14, no conda, no FEA tooling preinstalled.

| Layer | Choice | Status |
| --- | --- | --- |
| Parametric CAD | `cadquery` 2.8.0 + `cadquery-ocp` 7.9.3.1.1 | **Verified** — cp313 `win_amd64` wheels exist; resolves under uv |
| Mesh | `gmsh` 4.15.2 | **Verified** — `py2.py3-none-win_amd64` wheel bundles binary and Python API |
| FEA | CalculiX `ccx` 2.10 | **Located** — `GeneralElectric/CalculiX`, `releases/CalculiX-GE-OSS-2.10-win-x64.zip`, 17.9 MB, native Windows x64. Not yet run |
| Result parsing | `ccx2paraview` 3.2.0, `meshio` 5.3.5 | **Verified** — resolve clean |
| Render | `pyvista` 0.49.0 + `vtk` 9.7.0 | **Verified** to resolve; off-screen rendering unproven (Gate 2) |

CalculiX is the only non-PyPI artifact. Fetch by pinned URL and SHA-256; do not commit it — `ccx` is GPL and this repo is public.

---

## Reference — the demo problem

One family of geometry serves validation, the demo, and two of three mutation categories.

**V1 — tip-loaded cantilever.** Closed form for deflection and root stress. Validates units, material card, boundary conditions, element formulation and stress extraction as one chain. Also gives the MPa/Pa mutation a ground truth, where a unit error appears as a factor of 10⁶ rather than a subtle drift.

**V2 — stepped flat bar with a shoulder fillet.** Published `Kt` for the `D/d` and `r/d` ratios proves the mesh resolves the fillet instead of smearing it, and calibrates D-12's threshold on geometry whose true answer is known.

**`L_bracket` — the demo part.** A plate bent through 90°, one flange fixed, load on the other, fillet at the inner corner. The peak lands at the fillet rather than the flange — literally the intent's own sentence, so a correct visual reading is a checkable claim. Three mass levers: fillet radius, wall thickness, and a lightening hole in the low-stress flange. Set the inner radius to zero and the sharp-corner singularity mutant falls out of the same parameter space; flip the load vector and so does the wrong-direction mutant.

Build `L_bracket` first and completely. The other two parts are M3 breadth and are the first thing to cut.

---

## Risk register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `glc_v5` cannot carry images | Kills the vision thesis | M0 Gate 2, before any engineering work. Three named fallbacks |
| Off-screen render fails on Windows | No contour to read | M0 Gate 2. Fallback: matplotlib over the surface mesh |
| `ccx` build does not run here | No solver | M0 Gate 3. Check WSL2 with a distro-packaged `ccx`, or `scikit-fem`, which resolves clean but deviates from the intent's named solver |
| Iteration too slow for the budget | D-13 is unvalidated | M1 task 8. Shrink the part or coarsen the base mesh before cutting iterations |
| Capability dedupe swallows re-solves | The loop appears to hang | M2 task 1, asserted by a test |
| Second-order tets blow up DOF count | Slow solve | Small parts; refine locally at named regions only |

---

## Not covered or not clear

Ranked. The first three are fixed by M0 and M1; the rest are live.

1. **Images through the gateway are unproven.** The intent's central claim depends on a path nothing in the course notes exercises. → M0 Gate 2.
2. **Solver correctness had no requirement.** Added as `REQ-DEL-009`. → M1 tasks 5–6.
3. **Minimum wall thickness had no algorithm.** Now a ray cast along facet normals; the cheap fallback is checking the driven parameter, which misses thin regions emerging where a hole sits near an edge. → M3 task 2.
4. **Does the agent get code-editing capability at all?** This project mostly calls tools. Cleaner to disable those capabilities explicitly than to leave them registered behind a guard.
5. **Material data provenance.** MatWeb's data is not freely redistributable; use published handbook or public datasheet values, cited per record.
6. **Per-iteration runtime is a guess.** D-13's budget was set before anything was measured.
7. **Single process only.** The harness's JSON stores are unsafe across processes, so no parallel candidate evaluation. A real throughput ceiling.
8. **The Route B rubric is unstated.** The Session 16 and 17 rubrics in the class notes are different assignments and do not apply.
9. **`OD-B` and `OD-C` are unset** — release thresholds and numeric tolerances. Correctly deferred to M3 data, but required before calling anything acceptable.

---

## Parked questions

Owner-directed, parked as of 2026-09-09 — recorded, not being chased. Q1–Q3 are answerable by running something (fork `S17Code` and read it; run the Gate 2 spike). Only Q4 needs an answer that cannot be obtained that way, and it does not bite until M4.

1. **You have no `S17Code` fork.** Your account has `glc_v5`, `S16Code` and `S15Code`, with no local clone of S17Code. S17Code carries the coding capabilities, skills loader and protected-paths guard. Fork it, or is the intended harness your own `S16Code` extended by hand?
2. **Which is the reusable base** — upstream `theschoolofai/S17Code`, or work already in your forks that I have not seen?
3. **Is a vision-capable model already configured** in your `glc_v5` fork, and has any image ever been sent through it?
4. **What is the actual Route B rubric?** It decides where M4 effort goes.

---

## Standing decisions this plan adds

1. **Nothing is built on unvalidated physics.** M1's V1 passes before M2 starts.
2. **The vision path is proven before it is depended on.** M0 Gate 2, ahead of all engineering work.
3. **The judge is unreachable.** Verifiers, tasks, materials and mutations are protected paths.
4. **The solver is a capability, not an allowlisted command.** Tight allowlist, typed contract.
5. **Re-solving is not a duplicate.** Declared rerunnable, asserted by a test.
6. **The GPL binary is fetched, not vendored.** Pinned URL and SHA-256; the lockfile carries the rest.

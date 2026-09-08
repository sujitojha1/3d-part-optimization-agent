# Requirements — 3D Part Optimization Agent

| Attribute | Value |
| --- | --- |
| Version | 0.3 |
| Date | 2026-09-09 |
| Status | Draft for owner approval |
| Owner | Sujit Ojha |
| Budget | Four weeks, one engineer |
| Scope source | [Project intent](intent.md) |
| Execution order | [Plan](plan.md) — milestones M0 to M4 |
| Design | [Solution architecture](solution-architecture.md) — how it is built |
| Conventions | EARS statements ([Mavin](https://alistairmavin.com/ears/)); structure informed by ISO/IEC/IEEE 29148:2018, tailored — not audited compliance |

## 1. How to read this

Only `REQ-*` lines are normative. `Must` = required to ship in four weeks. `Should` = build only if section 8's schedule holds. Everything else is definition, rationale, or a decision record.

Section 2 fixes the choices the v0.1 draft left open. A four-week build cannot run a decision-review process, so the defaults below are **decided** with rationale; the owner overrides any of them by editing section 2, and the requirements follow. Only section 7 stays genuinely open.

## 2. Fixed decisions

These were open decisions `OD-01`–`OD-10` in v0.1. Each is now resolved toward the cheapest option that still satisfies the intent.

| # | Decision | Rationale |
| --- | --- | --- |
| D-01 | **Analysis:** linear static, small strain, isotropic elastic. Failure mode: von Mises against yield only. Buckling, fatigue, contact, thermal, and plasticity are out of scope. | The intent's loop is stress-contour reasoning. Anything nonlinear multiplies solve time and debugging with no gain to the thesis. |
| D-02 | **Solver:** CalculiX (`ccx`) 2.10, the native Windows x64 build published in `GeneralElectric/CalculiX` under `releases/`. Fetched at setup time by pinned URL and SHA-256, **not committed** to this repo. FEniCS dropped. | Text `.inp` in, `.frd` out; both trivially scriptable and diffable. `ccx` is GPL and this repo is public, so fetching rather than vendoring avoids a source-offer obligation while keeping the build reproducible. FEniCS drags a dependency chain that will not survive "runs on a clean machine". |
| D-03 | **Mesh:** Gmsh, second-order tetrahedra (`C3D10`), one task-declared characteristic length with a local refinement factor at named regions. | First-order tets are over-stiff and report bad stress — they would poison the entire prediction-accuracy metric. |
| D-04 | **Geometry:** one **CadQuery** parametric script per benchmark part. Edits set **named parameters**; the agent never performs free-form CAD and never writes CAD code. FreeCAD dropped. | Two cuts in one. Arbitrary CAD editing is its own multi-week project and is where builds of this shape usually die. FreeCAD additionally has no reliable pip path on Windows and expects its own interpreter; CadQuery 2.8.0 on `cadquery-ocp` 7.9.3.1.1 has verified cp313 `win_amd64` wheels and installs alongside everything else. |
| D-05 | **Permitted edit vocabulary** (closed set of four): `fillet_radius`, `wall_thickness`, `hole_diameter`, `pocket_depth`. Each task declares which apply, with min/max/step. | Makes `REQ-OPT-003` checkable, and makes the refusal case (D-09) a finite, enumerable claim. |
| D-06 | **Named regions:** each parametric model exports labeled element sets (e.g. `fillet_A`, `web`, `hole_edge`, `bulk`). Spatial claims resolve to one label. | Turns "where is the stress" from an open representation problem into a set-membership check. Resolves v0.1's `OD-02` region question. |
| D-07 | **Prediction schema:** `{region, metric, direction, band}` where `metric ∈ {max_vm, max_disp, mass}`, `direction ∈ {up, down, flat}`, `band ∈ {0–5%, 5–15%, 15–30%, >30%}`. Scored as three independent booleans — region hit, direction hit, band hit — reported separately and as a conjunction. | The intent's headline metric had no scoring rule, and free-text reasons collide with `REQ-DEL-004`. This makes the reasoning score a predicate over structured data. |
| D-08 | **Load cases:** exactly one per task in v1. | Multi-case support multiplies solve time and result plumbing for no thesis value. Deferred (section 6). |
| D-09 | **Material library:** closed JSON file, 8 alloys (Al 6061-T6, Al 7075-T6, steel 1018, 4140, 304 SS, Ti-6Al-4V, brass 360, cast iron). Fields per D-10. Provenance is a cited source string per record. | Finite and enumerable, so "no material in the library works" is provable by exhaustion. |
| D-10 | **Material fields:** `yield_mpa`, `density_kg_m3`, `youngs_gpa`, `poisson`, `cost_per_kg`, `machinability`, `corrosion_resistance`, `availability`, `source`. Unknowns are explicit `null`, never omitted. | Intent calls out all six selection attributes; explicit `null` keeps `REQ-OPT-007` decidable. |
| D-11 | **Manufacturing check:** FDM profile only — minimum wall thickness and maximum overhang angle. Overhang is the angle between each surface facet's normal and the build direction. Minimum wall is a ray cast inward along each facet normal, taking the distance to the next surface as local thickness. PrusaSlicer and CAM are out; draft angle is not applicable to FDM and is dropped. | A geometric rule check is hours of work; driving a slicer and parsing its output is days, and adds a fragile external process to the packaged run. The ray cast is named because "computed geometrically" hid a real algorithm choice; checking the driven thickness parameter instead is the cheap fallback, but it misses thin regions that emerge where a hole sits near an edge. |
| D-12 | **Singularity protocol:** re-solve the flagged candidate at 0.5× characteristic length in the affected region. If peak von Mises rises more than 20%, the peak is treated as mesh-driven and the result is unverified. | One extra solve, no convergence-study machinery. Catches the sharp-corner mutation. |
| D-13 | **Budget:** 8 candidate evaluations or 20 minutes wall clock per run, whichever comes first. Per-tool timeout 180 s. In-flight work finishes; no new evaluation launches. | Bounds the run and forces benchmark parts small enough to solve in seconds. |
| D-14 | **Benchmark parts (3):** `L_bracket` (fillet-driven), `cantilever_plate_with_hole` (hole and thickness), `ribbed_beam` (web and pocket). Each ships a baseline that passes all checks. | Enough to cover the edit vocabulary and show a material trade; more is schedule risk. |
| D-15 | **Task set:** 9 tasks — each part × {geometry-led, material-led, unachievable-target}. | Gives every validation scenario at least one fixture. |
| D-16 | **Mutation corpus:** 3 categories × 2 instances = 6 mutants, each paired with a valid control. Categories per intent: sharp-corner singularity, wrong load direction, MPa/Pa material-unit mismatch. | Small enough to run every commit; paired controls make the false-positive rate reportable. |
| D-17 | **Environment:** Windows 11, Python 3.13, **`uv` lockfile** — `cadquery`, `gmsh` 4.15.2, `meshio`, `ccx2paraview`, `pyvista`/`vtk`. conda dropped. `ccx` per D-02 is the only non-PyPI artifact. One documented entry command. | The full stack was verified to resolve under `uv` on Python 3.13 Windows with no conda present, which is what the target machine actually has. Dropping conda removes the hardest part of "runs on a clean machine". |
| D-18 | **Model access:** the vision step sends rendered contour images and numeric summaries to a hosted model **through the `glc_v5` gateway on 8111**; the agent process holds no credential. No customer geometry — benchmark parts are project-authored. Records stay local. | Matches the course harness split. Whether the gateway can carry an image part at all is unproven and is `OD-D`. |
| D-19 | **Rerunnable capabilities:** `run_sim`, `read_result`, and the manufacturing check are declared rerunnable in the capability registry. | The harness deduplicates identical capability calls. Re-solving the same parameter set after an edit is not a duplicate — the geometry changed in between — and without this the loop silently stops iterating. |
| D-20 | **Protected paths:** `verifiers/**`, `tasks/**`, `materials/**`, and `mutations/**` join the harness defaults (`tests/**`, `conftest.py`, `.github/**`). The solver is exposed as a capability, not added to the command allowlist. Code-editing capabilities are disabled unless D-21 work requires them. | The judge must be unreachable by the thing being judged: an agent asked to reduce mass that can edit `tasks/` will lower the safety factor instead of removing material. A typed `run_sim` contract also satisfies `REQ-DEL-002` for free. |
| D-21 | **Mesh density is not an agent-controllable parameter.** Characteristic length and refinement factors are task data, and a proposal that changes them is refused. | The cheapest way to make a stress concentration disappear is to coarsen the mesh until it vanishes. D-05 already excludes it; this makes the exclusion an explicit refusal rather than an omission. |
| D-22 | **Solver validation gate:** two closed-form cases ship as tests and must pass before any agent result is meaningful — a tip-loaded cantilever (`δ = PL³/3EI`, `σ = Mc/I`) and a shoulder-fillet stepped bar checked against a published `Kt`. | Prediction accuracy, mutation detection, and the frontier all inherit the solver's correctness. The cantilever also gives the MPa/Pa mutation a ground truth, where a unit error appears as a factor of 10⁶. The fillet case calibrates D-12's 20% threshold on geometry whose true answer is known, instead of guessing it. |

Two rendering constraints follow from D-07 and are normative, not stylistic: contour images use a **fixed camera set and a legend range locked across all iterations of a run** (`REQ-OPT-001`). An auto-rescaling color bar makes cross-iteration visual comparison meaningless.

## 3. Acceptance semantics

| Term | Meaning |
| --- | --- |
| Task | Part ID, units, single load case, supports, material library reference, permitted edits with bounds, safety factor `SF ≥ 1`, displacement limit, manufacturing profile, optional mass target, budget |
| Baseline | The task's initial parameter set, evaluated under identical conditions to every candidate |
| Candidate | One parameter set plus one material assignment |
| Structural pass | Valid `max_vm ≤ yield_mpa / SF` **and** `max_disp ≤ limit` |
| Manufacturing pass | Every enabled rule in the task's profile passes |
| Successful reduction | Mass at least 1% below baseline (task-overridable), with structural and manufacturing pass |
| Target achieved | Successful reduction that also meets the task's mass target |
| Explored frontier | Recorded nondominated candidates on (mass, violation). Evidence of search, not proof of optimality |
| Prediction score | D-07's three booleans, compared against the next valid evaluation |
| Invalid | Missing, failed, non-finite, timed-out, or setup-inconsistent evidence. Never a pass |

## 4. Requirements

### 4.1 Intake and baseline

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-IN-001 | When a task is submitted, the system shall validate it against the versioned task schema. | Must | One complete fixture plus one missing-field fixture per required field. |
| REQ-IN-002 | If a task declares inconsistent or unsupported units, then the system shall reject it and name the offending field. | Must | Pa/MPa mismatch and an unsupported unit both rejected with field-specific diagnostics. |
| REQ-IN-003 | When a valid task starts, the system shall evaluate the initial parameter set as the baseline. | Must | Baseline record holds mass, stress, displacement, and manufacturing results. |
| REQ-IN-004 | If any baseline check is invalid, then the system shall terminate with `invalid-baseline`. | Must | Failed and non-finite baseline fixtures produce no successful outcome. |

### 4.2 Reasoning loop

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-OPT-001 | When valid results are available, the system shall render the stress contour using the run's fixed camera set and locked legend range, and supply the image to the agent's visual step. | Must | Trace shows an image input bound to the matching result; two iterations of one run share an identical legend range. |
| REQ-OPT-002 | When the agent interprets a contour, the system shall record the identified concentration as one region label from D-06. | Must | The `L_bracket` fixture with a known fillet concentration yields a label the predicate can score. |
| REQ-OPT-003 | When the agent proposes a candidate, the system shall accept exactly one D-05 parameter change or one material substitution, within declared bounds, and shall refuse any proposal that changes mesh settings. | Must | Compound, out-of-bounds, and mesh-altering proposals rejected; each permitted single edit accepted. Enforced in the runtime, not in a skill. |
| REQ-OPT-004 | Before a change is executed, the system shall persist the agent's rationale and its D-07 structured prediction. | Must | Record ordering shows both persisted before the tool invocation. |
| REQ-OPT-005 | When the next valid evaluation completes, the system shall score the preceding prediction per D-07 and store all three booleans. | Must | Known-correct and known-wrong predictions receive the expected sub-scores. |
| REQ-OPT-006 | When the agent considers a material, the system shall supply all D-10 fields, including explicit `null`. | Must | Trace shows every field for each considered material. |
| REQ-OPT-007 | If a material lacks a property an enabled check requires, then the system shall exclude it from accepted candidates. | Must | A record with `null` yield strength cannot produce an accepted candidate. |

### 4.3 Verification

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-VER-001 | When a candidate is evaluated, the system shall report mass in grams. | Must | Known volume × known density, within declared tolerance. |
| REQ-VER-002 | When valid structural results exist, the system shall decide structural pass per section 3. | Must | Boundary fixtures at, below, and above both limits. |
| REQ-VER-003 | When a candidate is evaluated, the system shall decide manufacturing pass using the task's FDM profile. | Must | Fixtures violating minimum wall and overhang each fail the matching rule. |
| REQ-VER-004 | If any required check is invalid, then the system shall classify the candidate `unverified`, and an unverified candidate shall never count as a pass. | Must | Timeout, missing-output, and non-finite fixtures never pass. |
| REQ-VER-005 | If a peak meets the D-12 singularity criteria, then the system shall run the D-12 refinement re-solve and classify the result `unverified` unless it survives. | Must | Both sharp-corner mutants flagged; the smooth control is not. |
| REQ-VER-006 | If the solver's applied load direction differs from the task's declared direction, then the system shall reject the setup before scoring. | Must | Both wrong-direction mutants detected by comparing task intent with the generated `.inp`. |

### 4.4 Termination and explanation

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-OUT-001 | When the D-13 budget is exhausted, the system shall launch no further evaluation. | Must | Small-budget fixture stops; in-flight work completes. |
| REQ-OUT-002 | When a run ends, the system shall report exactly one of `target-achieved`, `improved-without-target`, `target-not-achieved`, `invalid-input`, `invalid-baseline`, `execution-failed`. | Must | One fixture per status with matching machine-readable outcome. |
| REQ-OUT-003 | When a valid search ends without the target, the system shall report the explored frontier with each candidate's parameters, material, mass, and constraint results, and shall scope the claim to the declared search space rather than asserting universal infeasibility. | Must | Unachievable-target fixture returns a frontier and scoped wording; budget-exhaustion fixture asserts nothing stronger. |
| REQ-OUT-004 | When a run returns a recommendation, the system shall link it to the baseline comparison, change history, and stored evidence. | Must | Every reported metric resolves to a persisted artifact. |

### 4.5 Delivery — the five course deliverables

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-DEL-001 | The system shall orchestrate its loop in a project-owned harness with no agent framework. | Must | Dependency and source inspection finds no LangChain, CrewAI, or equivalent. |
| REQ-DEL-002 | The system shall expose CalculiX through callable `run_sim` and `read_result` tools per section 5. | Must | Integration fixture exercises both contracts. |
| REQ-DEL-003 | The distribution shall pin every tool dependency in the D-17 lockfile and provide one documented command that runs a bundled task end to end on a clean machine. | Must | Clean-VM install and run with no undeclared preinstalled dependency. |
| REQ-DEL-004 | The system shall provide an executable acceptance predicate per task in D-15, deriving its decision exclusively from structured tool outputs. | Must | Editing agent prose alone leaves every score unchanged. |
| REQ-DEL-005 | The distribution shall include the D-16 corpus and shall report detections ÷ executions, plus the control false-positive rate. | Must | Controlled outcomes yield the expected numerator, denominator, and rates; zero executions report `not evaluated`. |
| REQ-DEL-006 | Before scoring, the system shall persist the raw run record — inputs, tool calls, outputs, artifact references, predictions, tool versions, and terminal status — to disk, and a write failure shall prevent scoring. | Must | Scoring blocked until the record is readable; every evaluation resolves to its exact inputs and versions. |
| REQ-DEL-007 | When a saved run is rescored, the system shall compute the new score with no model or solver access. | Must | Rescore a saved fixture with both disabled. |
| REQ-DEL-008 | If a tool execution fails, then the system shall persist its diagnostics against the candidate ID. | Must | Injected solver and checker failures retrievable by candidate. |
| REQ-DEL-009 | The distribution shall include the D-22 validation cases as tests, and their failure shall block release. | Must | Both cases agree with closed form within the declared tolerance; an injected unit error in the material card fails the cantilever case. |
| REQ-DEL-010 | The system shall declare `run_sim`, `read_result`, and the manufacturing check rerunnable, and shall not deduplicate them. | Must | Two identical `run_sim` calls separated by an edit both execute and both appear in the run record. |
| REQ-DEL-011 | The system shall refuse edits to every D-20 protected path and shall record each refusal. | Must | An attempted edit to a task, verifier, material record, and mutation is refused, and each refusal is retrievable. |
| REQ-DEL-012 | The system should publish a run report summarizing mass delta, constraint margins, prediction accuracy, and mutation detection. | Should | Report generated from stored records alone. |
| REQ-DEL-013 | The system should record an A/B of one benchmark task run with and without the FEA-reasoning skill loaded. | Should | Both runs stored, differing only by the skill being available. |

## 5. Interface contracts

Logical content; encodings are JSON on disk unless noted.

| Interface | Content |
| --- | --- |
| Task | `task_id`; part ID and units; single load case and supports; material library ref; permitted edits with bounds; `SF`; displacement limit; manufacturing profile; optional mass target; tolerances; budget |
| `run_sim` request | `run_id`, `candidate_id`; parameter set; material ID; mesh settings; load case; solver settings |
| `run_sim` response | Status; solver version; generated `.inp` reference; result artifact refs; diagnostics |
| `read_result` response | Validity; `mass_g`; `max_vm` and `max_disp` with units; peak region label; contour image ref |
| Manufacturing result | `candidate_id`; checker version; profile; per-rule pass/fail/invalid with measured value |
| Prediction record | `candidate_id`, `parent_id`; D-07 schema; rationale ref; scored booleans |
| Run record | Task, config, versions, ordered tool I/O, artifact refs, predictions, diagnostics, terminal status |

## 6. Explicitly deferred

Named so that absence is a decision, not an oversight: multiple load cases; buckling, fatigue, and nonlinear material; free-form CAD editing; CAM and slicer-based manufacturability; mesh convergence studies beyond D-12; multi-objective optimization over cost; non-Windows packaging; and any performance, retention, or privacy threshold beyond D-18.

Dropped from v0.1 as redundant or merged, IDs retired and not reused: v0.1 `OPT-004`/`OPT-006` (merged into the new `OPT-004`), `VER-006` (merged into `VER-005`), `VER-008` (a restatement of section 3), `OUT-004` (merged into `OUT-003`), and `DEL-010`/`DEL-011` (merged into `DEL-006`). Note that `OPT-005`–`OPT-009`, `VER-007`, and `OUT-005` were renumbered by the merges; compare against v0.1 in git before citing an old ID. Section 4's source register and section 9's lifecycle process from v0.1 are removed — single-owner traceability is served by git history.

## 7. Still open

| ID | Question | Blocks |
| --- | --- | --- |
| OD-A | Which harness is the reusable base? `S17Code` carries the capability registry, skills loader, and protected-paths guard, but the owner's account has forks of `glc_v5`, `S16Code`, and `S15Code` only — no `S17Code` fork, and no local clone. | `REQ-DEL-001`, Phase 0 |
| OD-D | Can `glc_v5` carry an image part to the model? Nothing in the course material exercises that path, and the intent's central claim depends on it. | `REQ-OPT-001`, Phase 0 |
| OD-B | Release thresholds: prediction accuracy, mutation detection rate, control false-positive ceiling. | `REQ-DEL-004`, `REQ-DEL-005` |
| OD-C | Numeric tolerances: mass comparison, load-direction angle, spatial region match, and D-22 validation agreement. | `REQ-VER-001`, `REQ-VER-006`, `REQ-OPT-005`, `REQ-DEL-009` |

OD-A and OD-D block work and are resolved in [Phase 0](plan.md) before week 1. OD-B and OD-C do not block building; they block declaring the result acceptable, and should be set from week-3 data rather than guessed now.

## 8. Execution order

Sequencing, the Phase 0 gates that resolve `OD-A` and `OD-D`, the demo and validation parts, and the risk register live in **[plan.md](plan.md)**. Two ordering constraints are normative here because requirements depend on them: `REQ-OPT-001` cannot be built before `OD-D` is answered, and no agent result is meaningful before `REQ-DEL-009`'s validation cases pass.

## 9. References

- [Project intent](intent.md) — product scope and the five deliverables.
- [EARS — Mavin](https://alistairmavin.com/ears/), syntax reference, accessed 2026-09-09.
- [ISO/IEC/IEEE 29148:2018](https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso-iec-ieee%3A29148%3Aed-2%3Av1%3Aen), structural reference, accessed 2026-09-09.

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-09 | Initial specification from intent |
| 0.2 | 2026-09-09 | Scoped to four weeks: 10 open decisions resolved to 3, 38 requirements reduced to 30, lifecycle process and source register removed, schedule added |
| 0.3 | 2026-09-09 | Stack corrected to what this machine can actually run — CadQuery replaces FreeCAD, uv replaces conda, CalculiX sourced and fetched rather than vendored. Added D-19 to D-22 and REQ-DEL-009 to 011/013 from the harness constraints and the missing solver-validation gate. `OD-A` restated, `OD-D` added. Execution order moved to `plan.md` |

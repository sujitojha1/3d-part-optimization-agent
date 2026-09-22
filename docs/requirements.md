# Requirements — 3D Part Optimization Agent

| Attribute | Value |
| --- | --- |
| Version | 0.7 |
| Date | 2026-09-21 |
| Status | Draft for owner approval |
| Owner | Sujit Ojha |
| Budget | Three weeks, one engineer — 12 Sep to **3 Oct 2026, fixed end date** |
| Scope source | [Project intent](intent.md). Departures are listed in section 2.1 |
| Execution order | [Plan](plan.md) — milestones M1 to M6 |
| Design | [Solution architecture](solution-architecture.md) — how it is built |
| Conventions | EARS statements ([Mavin](https://alistairmavin.com/ears/)); structure informed by ISO/IEC/IEEE 29148:2018, tailored — not audited compliance |

## Progress audit — 21 September

See [the complete requirement-by-requirement audit](progress-review-2026-09-21.md) and [current recovery plan](plan.md). No Must requirement is waived by this review. Manual four-case studies remain separate from the parametric LC1 agent task. Current scripts and documents disagree on geometry identity, raw-versus-excluded stress acceptance, support idealisation, material tempers and experimental CAM scope; those discrepancies remain open implementation/decision work, not implicit requirement amendments. `OD-B`/`OD-C` must be frozen before the corresponding scored validation runs. D-23 below corrects the symmetry assumption using the already-recorded geometry evidence.

## 1. How to read this

Only `REQ-*` lines are normative. `Must` = required to ship by 3 Oct. `Should` = build only if the plan's schedule holds. Everything else is definition, rationale, or a decision record.

Section 2 fixes the choices the v0.1 draft left open. A three-week build cannot run a decision-review process, so the defaults below are **decided** with rationale; the owner overrides any of them by editing section 2, and the requirements follow. Only section 7 stays genuinely open.

**What v0.5 changed, in one paragraph.** Four owner decisions on 2026-09-17: the project is built and run on **macOS arm64 only**; **3 Oct is fixed**; a **parametric GE-style jet engine bracket is the demo part**, replacing `L_bracket`; and **the intent's stack is kept, centred on FreeCAD — its FEM Workbench for Gmsh and CalculiX, and its CAM Workbench for manufacturability — with no other CAD or slicer software**, reversing v0.3's switch to CadQuery. D-02 to D-04, D-06, D-08, D-09, D-11, D-12, D-14 to D-17 and D-22 follow from those, and D-23 and D-24 are new. The machinability check follows [freecad-cam-workbench.md](freecad-cam-workbench.md); the mesh-quality and singularity content comes from [fem-geometry-preparation.md](fem-geometry-preparation.md) via [freecad-tutorials.md §7](freecad-tutorials.md) and [fem-workbench.md §9.8](fem-workbench.md).

## 2. Fixed decisions

These were open decisions `OD-01`–`OD-10` in v0.1. Each is now resolved toward the cheapest option that still satisfies the intent.

| # | Decision | Rationale |
| --- | --- | --- |
| D-01 | **Analysis:** linear static, small strain, isotropic elastic. Failure mode: von Mises against yield only. Buckling, fatigue, contact, thermal, and plasticity are out of scope. | The intent's loop is stress-contour reasoning. Anything nonlinear multiplies solve time and debugging with no gain to the thesis. The GE challenge's own criterion is static loads against yield ([brief §7](ge-jet-engine-bracket.md)). |
| D-02 | **Solver:** CalculiX `ccx` **2.23**, conda-forge build `osx-arm64/calculix-2.23-pl5321h33a25c5_4.conda` (SHA-256 `2d92ce83c8949361fbc2c6043dea56e9bb0a631cae59a512337b047fa28a28c4`), installed into the D-17 FEM environment and driven through **FreeCAD's `femtools.ccxtools`** — `write_inp_file`, `ccx_run`, `load_results`. **Not committed.** FEniCS not used. | The intent names CalculiX or FEniCS; CalculiX is what FreeCAD's FEM Workbench drives natively, so the `.inp` writer, material cards and constraint cards come from FreeCAD rather than being written by hand. Text `.inp` in, `.frd` out, both diffable. No Homebrew formula exists and the build links arpack, BLAS and OpenMP dylibs, so it comes from the same explicit lock as FreeCAD. GPL, public repo: fetched, not vendored. |
| D-03 | **Mesh:** Gmsh 4.15.2 through FreeCAD's `FemMeshGmsh` object, second-order tetrahedra (`C3D10`). Sizing per D-24. | First-order tets are over-stiff and report bad stress — they would poison the prediction-accuracy metric. FreeCAD's own geometry-preparation guide says the same ([§10.3](fem-geometry-preparation.md)). |
| D-04 | **Geometry: FreeCAD 1.1.3**, run headless from Python. One parametric FreeCAD document per benchmark part, **driven by a Spreadsheet of named parameters**; the agent sets spreadsheet cells only and the document recomputes. It never performs free-form CAD and never writes CAD code. **No other CAD software.** Every face a constraint or mesh group references is **re-selected by a geometric predicate after each recompute** (e.g. the cylindrical face of radius 9.525 mm at the pin axis), never by a stored face index. | The intent names FreeCAD, and FreeCAD's FEM Workbench is the only place where CAD, Gmsh and CalculiX already meet ([fem-workbench.md](fem-workbench.md)). v0.3 dropped it for Windows packaging; on macOS arm64 conda-forge ships FreeCAD, Gmsh and CalculiX as one lockable set, so that reason is gone. The predicate rule exists because of the topological naming problem: a parameter change can renumber faces, and a constraint silently moving to the wrong face produces a plausible, wrong answer. |
| D-05 | **Permitted edit vocabulary** — a closed set of four parameter *kinds*: `fillet_radius`, `wall_thickness`, `hole_diameter`, `pocket_depth`. The part's frozen parameter record names each concrete parameter (at most six), its kind, and min/max/step. Each task declares which apply. **Every thickness floor is ≥ 1.27 mm**. The frozen record also notes, for each `fillet_radius`, the smallest ToolBit radius that can cut it, so an unmachinable edit is a visible trade, not a surprise. | Makes `REQ-OPT-003` checkable, and makes the refusal case a finite, enumerable claim. The bracket needs more than one thickness (base, arms), so the closed set is of kinds, not of names. 1.27 mm is the challenge's minimum feature size. |
| D-06 | **Named regions:** each part defines FEM **Mesh Group** objects that become labeled element sets in the `.inp` — verified by reading the deck in M2.4, with element-centroid membership in named sub-shapes as the fallback. `ge_bracket` candidates: `pin_bore`, `clevis_arm`, `arm_root_fillet`, `base_plate`, `bolt_boss`, `bulk` — frozen in M2.1. Spatial claims resolve to one label. | Turns "where is the stress" from an open representation problem into a set-membership check. |
| D-07 | **Prediction schema:** `{region, metric, direction, band}` where `metric ∈ {max_vm, max_disp, mass}`, `direction ∈ {up, down, flat}`, `band ∈ {0–5%, 5–15%, 15–30%, >30%}`. Scored as three independent booleans — region hit, direction hit, band hit — reported separately and as a conjunction. | The intent's headline metric had no scoring rule, and free-text reasons collide with `REQ-DEL-004`. This makes the reasoning score a predicate over structured data. |
| D-08 | **Load cases:** exactly one per task. `ge_bracket` tasks use **LC1 vertical**, `FORCE (0, 0, +35,585.77) N` on the pin, in the SimJEB frame (+z up, N, mm, MPa). LC2–LC4 as tasks are Should or deferred. | Multi-case support multiplies solve time and plumbing for no thesis value. LC1 governs peak stress in 318 of 381 SimJEB designs ([simjeb-dataset §4](simjeb-dataset.md)). |
| D-09 | **Material library:** closed JSON file, **5 machinable alloys** — Ti-6Al-4V (annealed), Al 7075-T6, Al 6061-T6, 17-4PH (H1025), AISI 4140 (quenched and tempered). Fields per D-10. Provenance is a cited handbook or public datasheet per record (not MatWeb); `machinability` is a cited index against a named reference alloy. Ti-6Al-4V uses E = 113.8 GPa and ν = 0.342, matching SimJEB, and one cited density. | Finite and enumerable, so "no material in the library works" is provable by exhaustion. Every alloy is routinely milled, so a material-led task cannot win with a part D-11 cannot make; machinability is now a real trade against strength and density, as the intent asks. |
| D-10 | **Material fields:** `yield_mpa`, `density_kg_m3`, `youngs_gpa`, `poisson`, `cost_per_kg`, `machinability`, `corrosion_resistance`, `availability`, `source`. Unknowns are explicit `null`, never omitted. | Intent calls out all six selection attributes; explicit `null` keeps `REQ-OPT-007` decidable. `machinability` stays: AM brackets are post-machined at interfaces. |
| D-11 | **Manufacturing check: FreeCAD CAM Workbench, one `cnc_3axis` profile.** The task declares its **setups** (e.g. top +z, bottom −z, side +y for the pin bore and arm profile) and references a committed **ToolBit library** (flat endmills and drills, pinned diameters). For each setup the pipeline, headless, creates a CAM Job on the candidate with Adaptive clearing, Profile and Drilling operations on predicate-selected faces (D-04), recomputes, runs **Sanity Check**, post-processes G-code with a pinned post processor, and replays it through **`PathSimulator`** on the job stock. Three rules: **`cam_ops`** — every operation yields a non-empty path with no errors; **`residual_stock`** — every part-surface sample is reached, within 0.2 mm, by some setup's simulated result, and no setup cuts into the part; **`min_wall`** — ≥ 1.27 mm by ray cast on the FreeCAD shape. Overhang and draft do not apply to milling and are dropped. No slicer. | The intent names "PrusaSlicer or a CAM check"; the owner chose the CAM check inside FreeCAD, which keeps every tool in one environment. The original GE bracket was designed for conventional machining ([brief §1](ge-jet-engine-bracket.md)), so a machined baseline is realistic. The rules read the CAM tool's own output — generated paths and simulated stock — rather than a proxy. `PathSimulator` is a heightmap simulator along the tool axis, which is exactly 3-axis reach: an undercut shows up as residual stock. It is exercised headless by FreeCAD's own CAM tests, but not yet on this machine (Gate 4). Fallback if the simulator cannot run headless: ray-cast tool access along setup directions plus concave radius ≥ smallest tool radius. |
| D-12 | **Singularity protocol:** re-solve the flagged candidate with the D-24 `MeshRegion` size halved in the flagged region. If peak von Mises rises more than 20%, the peak is treated as mesh-driven and the result is unverified. The 20% threshold is **calibrated in M5.3 on `ge_bracket` itself**: `arm_root_fillet` at nominal radius (convergent) against radius zero (divergent), at 3–4 refinement levels. | One extra solve per flagged candidate, no convergence-study machinery. The convergent-versus-divergent split is the discriminator ([fem-geometry-preparation §13](fem-geometry-preparation.md)); calibrating on the demo part's own fillet replaces v0.4's V2 stepped bar, which moves to Should. |
| D-13 | **Budget:** 8 candidate evaluations or 20 minutes wall clock per run, whichever comes first. Per-tool timeout 180 s. In-flight work finishes; no new evaluation launches. | Bounds the run. An evaluation includes the D-11 CAM jobs and simulation, not only the solve; both are timed in M3.8. If M2.5 measures a nominal solve over 60 s, the levers apply in order: D-23 half model, D-24 minimum size, then coarser base size. Coarsening is last because it degrades the field the vision step reads. **M2 measurement:** at MeshRegion 1.5 the simulation half of one evaluation was 111.23 s (8 evaluations = 14.8 of the 20 min). The D-23 lever is unavailable, so the D-24 lever was taken on 2026-09-22 (region 2.0): 66.45 s per evaluation, mesh + solve 47.06 s, 8 evaluations = 8.9 min, leaving about 11 min for the untimed CAM jobs. Timings are provisional (Windows, not D-17) — see the [M2 walkthrough](m2-walkthrough.md#d-13-the-budget--first-measurement-and-it-is-tight). |
| D-14 | **Benchmark part:** `ge_bracket` — a parametric FreeCAD bracket (base plate, four bolt bosses, two clevis arms, arm-root fillets, base pockets or lightening holes) built around SimJEB's interface coordinates: pin Ø 19.05 mm, four bolt holes Ø 9.525 mm. Ti-6Al-4V baseline, **yield overridden to 903 MPa** (challenge), **SF 1.5** (allowable 602 MPa), **displacement limit 1.1 × baseline**. The baseline passes all checks. `L_bracket`, `cantilever_plate_with_hole` and `ribbed_beam` are deferred; **`L_bracket` is the named fallback** if M2.5 cannot solve `ge_bracket` inside D-13. | A real, well-known benchmark gives the demo and the refusal an external reference: SimJEB's 381 designs show what human designers reached. SF and displacement limit are project choices, because the challenge prescribes neither ([brief §6](ge-jet-engine-bracket.md)). One part is what three weeks allows. |
| D-15 | **Task set:** 3 tasks — `ge_bracket` × {geometry-led, material-led, unachievable-target}, all LC1. The material-led task is labelled as leaving the challenge brief, which fixes Ti-6Al-4V. **Should:** the same three under LC2 horizontal. | Gives every validation scenario one fixture. The unachievable target is calibrated in M5.5 against the explored parametric space and SimJEB's LC1 frontier, and stated as "no design in SimJEB", not as proof. |
| D-16 | **Mutation corpus:** 3 categories × 1 instance = **3 mutants**, each paired with a valid control. Sharp corner: `arm_root_fillet = 0` — it also fails D-11's `residual_stock`, which is correct but is not what it scores; it is detected only if `REQ-VER-005` flags the singularity. Wrong load direction: LC1 sign-flipped. Unit mismatch: the Ti-6Al-4V card in Pa where MPa is declared. **Should:** a second instance per category — LC3 at the challenge's own published error (30° from horizontal instead of 42° from vertical), a sharp pocket corner, and density in g/cm³ declared as kg/m³. | The three categories the intent names, runnable every commit. Paired controls make the false-positive rate reportable. Halved from v0.4: first item on the plan's cut list, taken now. |
| D-17 | **Environment: macOS arm64** (Apple Silicon). **(1) FEM environment** — conda-forge `freecad` 1.1.3 (Python 3.11; includes the FEM and CAM workbenches and `PathSimulator`), `gmsh` 4.15.2, `calculix` 2.23, `pyvista` and `ccx2paraview`, installed into gitignored `vendor/fem-env` by a pinned `micromamba` binary from an **explicit lock** (every package URL and SHA-256). `opencamlib` is not needed: the experimental 3D Surface and Waterline operations are not used. **(2) Harness environment** — the S17Code harness under its own `uv` lockfile. The harness calls the pipeline as a subprocess in the FEM environment. One documented entry command installs both. Windows is deferred. | Owner decisions 2026-09-17: this Mac only, and the intent's stack centred on FreeCAD. FreeCAD brings its own Python and binary dependencies, so it cannot share a `uv` environment with the harness; a process boundary at the L1 seam is also where errors-as-values already sits. All FEM packages exist for `osx-arm64` on conda-forge (checked 2026-09-17). Dropping the slicer removes the only separately installed app. |
| D-18 | **Model access:** the vision step sends rendered contour images and numeric summaries to a hosted model **through the `glc_v5` gateway on 8111**; the agent process holds no credential. SimJEB-derived interface coordinates are public data; SimJEB CAD is never shipped. Records stay local. | Matches the course harness split. Whether the gateway can carry an image part is `OD-D`. |
| D-19 | **Rerunnable capabilities:** `run_sim`, `read_result`, and the manufacturing check are declared rerunnable in the capability registry. | The harness deduplicates identical capability calls. Re-solving the same parameter set after an edit is not a duplicate, and without this the loop silently stops iterating. |
| D-20 | **Protected paths:** `verifiers/**`, `tasks/**`, `materials/**`, `mutations/**`, and `tooling/**` (the D-11 ToolBit library and post-processor config) join the harness defaults (`tests/**`, `conftest.py`, `.github/**`). The solver is exposed as a capability, not added to the command allowlist. Code-editing capabilities are disabled. | The judge must be unreachable by the thing being judged: an agent asked to reduce mass that can edit `tasks/` will lower the safety factor instead of removing material, and one that can edit `tooling/` will add a smaller endmill instead of opening a corner radius. |
| D-21 | **Mesh density is not an agent-controllable parameter.** Every D-24 size and field setting is task data, and a proposal that changes one is refused. | The cheapest way to make a stress concentration disappear is to coarsen the mesh until it vanishes. |
| D-22 | **Solver validation gate** — must pass before any agent result is meaningful. **V1:** FreeCAD's bundled *CalculiX Cantilever 3D* example rebuilt through our pipeline must reproduce its published −86.93 mm, and a slender variant (*L*/*h* ≥ 20) must agree with `δ = PL³/3EI` and `σ = Mc/I` within a signed band. **V3:** SimJEB design 148 (`148.stp`) under LC1, bolt holes as FreeCAD **Rigid Body Constraints** (`*RIGID BODY`), the pin load applied as settled in M2.2, reactions balanced via a **Section Print** feature (`*SECTION PRINT`), nodal displacement compared against `148.csv`. **Should:** V2, a shoulder-fillet stepped bar against a published `Kt`. | V1 checks units, material card, element formulation and extraction against both a formula and someone else's CalculiX run; slender, because a clamped stubby bar is stiffer than beam theory ([freecad-tutorials §6.4](freecad-tutorials.md)). The demo part is supported through couplings that neither closed-form case exercises, so V3 is a gate. It compares displacement only: SimJEB's first-order stresses are not ground truth. FreeCAD has no `*DISTRIBUTING COUPLING` tool ([fem-workbench §9.1](fem-workbench.md)), so how the pin load enters is a hand-walk decision, not an assumption. |
| D-23 | **Full model for the current `ge_bracket`.** The measured bolt pattern is asymmetric about the clevis midplane ([frozen part](ge-bracket-part.md), [LC1 record](ge-bracket-lc1.md)); apply the full load and report full-part mass. A future half model requires independent geometry, support and load symmetry evidence plus verified label mapping. | The original symmetry assumption was disproved during the hand walk. Do not halve force or double mass on the current full model. LC4 requires separate symmetry reasoning. |
| D-24 | **Mesh sizing** on `FemMeshGmsh`: each task declares `CharacteristicLengthMax`, `CharacteristicLengthMin`, and one **`MeshRegion`** size on the `arm_root_fillet` and `pin_bore` faces. `HighOrderOptimize` is on. If Gmsh reports inverted elements (negative Jacobians), the pipeline retries once with `SecondOrderLinear = true` and records it; a second failure makes the candidate `unverified` with a mesh diagnostic. | FreeCAD's guide: automatic meshers are too coarse by default, a minimum size stops tiny elements forming around small features, and refinement belongs at the concentrations ([§10.1](fem-geometry-preparation.md)). Distance-based refinement would grade more smoothly but only arrives in FreeCAD 26.3; `MeshRegion` is what 1.1.3 has. **`ge_bracket`:** max 4.0 / min 1.0 / `MeshRegion` 2.0 / curvature 8 mm (owner, 2026-09-22; was 1.5) — it moves LC1's governing peak 2.2 % at the same location and clears D-13's 60 s trigger. Do not coarsen past 2.0: `pin_bore` under-reads 23 % at 3.0 ([M2 walkthrough §5](m2-walkthrough.md#d-24-the-mesh-sizing--applied-at-20)). Second-order meshing inverts elements at small radii, which the agent's own `fillet_radius` edits reach ([§12](fem-geometry-preparation.md)). |

Two rendering constraints follow from D-07 and are normative, not stylistic: contour images use a **fixed camera set and a legend range locked across all iterations of a run** (`REQ-OPT-001`). An auto-rescaling color bar makes cross-iteration visual comparison meaningless. **Frozen in M2 (owner, 2026-09-22):** `turbo` colormap, 800 × 600, a linear legend locked at 0 → allowable/2 (the task's allowable, so the rule transfers across D-09 alloys; 301 MPa for Ti-6Al-4V at SF 1.5), cameras `iso`, `front` and `arm_root`, parallel projection ([record](ge-bracket-contour.md)).

### 2.1 Departures from the intent

The intent is the scope source and is not edited. These are the points where the requirements knowingly differ from it.

| Intent says | Requirements say | Decision |
| --- | --- | --- |
| Four-week build | Three weeks, fixed end 3 Oct | Budget |
| CalculiX or FEniCS | CalculiX, driven by FreeCAD | D-02 |
| PrusaSlicer or a CAM check; "machinable or printable" | CAM check only, in FreeCAD's CAM Workbench; machinable, not printable | D-11 |
| Manufacturability is minimum wall, draft, overhang | Minimum wall, CAM operations generate, tool reaches every surface; draft and overhang dropped — not applicable to 3-axis milling | D-11 |
| "Any material in the library" | A closed library of 5 machinable alloys | D-09 |
| — (GE challenge targets additive manufacturing) | The GE-style bracket is checked for CNC machining, as the original part was made | D-11, D-14 |

FreeCAD, Gmsh and CalculiX are used as the intent names them, and FreeCAD's CAM Workbench is the intent's "CAM check". v0.3's substitution of CadQuery for FreeCAD is withdrawn.

## 3. Acceptance semantics

| Term | Meaning |
| --- | --- |
| Task | Part ID and its FreeCAD document, units, single load case, supports, material library reference, permitted edits with bounds, safety factor `SF ≥ 1`, displacement limit, manufacturing profile, mesh sizing (D-24), optional mass target, budget |
| Baseline | The task's initial parameter set, evaluated under identical conditions to every candidate |
| Candidate | One parameter set plus one material assignment |
| Structural pass | Valid `max_vm ≤ yield_mpa / SF` **and** `max_disp ≤ limit` |
| Manufacturing pass | Every enabled rule in the task's profile passes |
| Successful reduction | Mass at least 1% below baseline (task-overridable), with structural and manufacturing pass |
| Target achieved | Successful reduction that also meets the task's mass target |
| Explored frontier | Recorded nondominated candidates on (mass, violation). Evidence of search, not proof of optimality |
| Prediction score | D-07's three booleans, compared against the next valid evaluation |
| Invalid | Missing, failed, non-finite, timed-out, mesh-failed, or setup-inconsistent evidence. Never a pass |

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
| REQ-OPT-002 | When the agent interprets a contour, the system shall record the identified concentration as one region label from D-06. | Must | The `ge_bracket` LC1 baseline, whose peak region is established in M2.5, yields a label the predicate can score. |
| REQ-OPT-003 | When the agent proposes a candidate, the system shall accept exactly one D-05 parameter change or one material substitution, within declared bounds, and shall refuse any proposal that changes mesh settings. | Must | Compound, out-of-bounds, and mesh-altering proposals rejected; each permitted single edit accepted. Enforced in the runtime, not in a skill. |
| REQ-OPT-008 | When a parameter change is applied, the system shall re-select every constraint and mesh-group face by its D-04 geometric predicate and shall mark the candidate `unverified` if any predicate matches zero faces or more than one. | Must | At each parameter's min and max, every predicate matches exactly one face; a deliberately ambiguous predicate yields `unverified`. |
| REQ-OPT-004 | Before a change is executed, the system shall persist the agent's rationale and its D-07 structured prediction. | Must | Record ordering shows both persisted before the tool invocation. |
| REQ-OPT-005 | When the next valid evaluation completes, the system shall score the preceding prediction per D-07 and store all three booleans. | Must | Known-correct and known-wrong predictions receive the expected sub-scores. |
| REQ-OPT-006 | When the agent considers a material, the system shall supply all D-10 fields, including explicit `null`. | Must | Trace shows every field for each considered material. |
| REQ-OPT-007 | If a material lacks a property an enabled check requires, then the system shall exclude it from accepted candidates. | Must | A record with `null` yield strength cannot produce an accepted candidate. |

### 4.3 Verification

| ID | Requirement | Pri | Verification |
| --- | --- | --- | --- |
| REQ-VER-001 | When a candidate is evaluated, the system shall report mass in grams for the full part. | Must | Known volume × known density, within declared tolerance; a D-23 half model reports twice its solved volume. |
| REQ-VER-002 | When valid structural results exist, the system shall decide structural pass per section 3. | Must | Boundary fixtures at, below, and above both limits. |
| REQ-VER-003 | When a candidate is evaluated, the system shall decide manufacturing pass using the task's `cnc_3axis` profile and its declared setups and ToolBit library. | Must | Fixtures failing each rule fail the matching rule: an operation with an empty path (`cam_ops`), an undercut unreachable from every setup (`residual_stock`), and a wall under 1.27 mm (`min_wall`); a CAM recompute error or missing simulator result is `invalid`, never a pass. |
| REQ-VER-004 | If any required check is invalid, then the system shall classify the candidate `unverified`, and an unverified candidate shall never count as a pass. | Must | Timeout, missing-output, non-finite, and D-24 mesh-failure fixtures never pass. |
| REQ-VER-005 | If a peak meets the D-12 singularity criteria, then the system shall run the D-12 refinement re-solve and classify the result `unverified` unless it survives. | Must | The sharp-corner mutant is flagged; its nominal-fillet control is not. |
| REQ-VER-006 | If the solver's applied load direction differs from the task's declared direction, then the system shall reject the setup before scoring. | Must | Each wrong-direction mutant detected by comparing task intent with the generated `.inp`. |

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
| REQ-DEL-002 | The system shall expose the FreeCAD–Gmsh–CalculiX pipeline through callable `run_sim` and `read_result` tools per section 5. | Must | Integration fixture exercises both contracts across the process boundary into the FEM environment. |
| REQ-DEL-003 | The distribution shall pin every tool dependency — the D-17 FEM explicit lock and the harness `uv` lockfile — and provide one documented command that runs a bundled task end to end on a clean macOS arm64 machine. | Must | Fresh macOS user account with no Python, conda, FreeCAD, Gmsh or CalculiX present: install and run with no undeclared preinstalled dependency. |
| REQ-DEL-004 | The system shall provide an executable acceptance predicate per task in D-15, deriving its decision exclusively from structured tool outputs. | Must | Editing agent prose alone leaves every score unchanged. |
| REQ-DEL-005 | The distribution shall include the D-16 corpus and shall report detections ÷ executions, plus the control false-positive rate. | Must | Controlled outcomes yield the expected numerator, denominator, and rates; zero executions report `not evaluated`. |
| REQ-DEL-006 | Before scoring, the system shall persist the raw run record — inputs, tool calls, outputs, artifact references, predictions, tool versions, and terminal status — to disk, and a write failure shall prevent scoring. | Must | Scoring blocked until the record is readable; every evaluation resolves to its exact inputs and versions. |
| REQ-DEL-007 | When a saved run is rescored, the system shall compute the new score with no model or solver access. | Must | Rescore a saved fixture with both disabled. |
| REQ-DEL-008 | If a tool execution fails, then the system shall persist its diagnostics against the candidate ID. | Must | Injected solver, mesher and checker failures retrievable by candidate. |
| REQ-DEL-009 | The distribution shall include the D-22 Must validation cases (V1, V3) as tests, and their failure shall block release. | Must | V1 agrees with closed form within its signed band; V3's reactions balance and displacement agrees within the declared tolerance; an injected unit error in the material card fails V1. |
| REQ-DEL-010 | The system shall declare `run_sim`, `read_result`, and the manufacturing check rerunnable, and shall not deduplicate them. | Must | Two identical `run_sim` calls separated by an edit both execute and both appear in the run record. |
| REQ-DEL-011 | The system shall refuse edits to every D-20 protected path and shall record each refusal. | Must | An attempted edit to a task, verifier, material record, mutation, and ToolBit library is refused, and each refusal is retrievable. |
| REQ-DEL-012 | The system should publish a run report summarizing mass delta, constraint margins, prediction accuracy, and mutation detection. | Should | Report generated from stored records alone. |
| REQ-DEL-013 | The system should record an A/B of one benchmark task run with and without the FEA-reasoning skill loaded. | Should | Both runs stored, differing only by the skill being available. |

## 5. Interface contracts

Logical content; encodings are JSON on disk unless noted.

| Interface | Content |
| --- | --- |
| Task | `task_id`; part ID and units; single load case and supports; material library ref; permitted edits with bounds; `SF`; displacement limit; manufacturing profile; mesh sizing (D-24) and symmetry flag (D-23); optional mass target; tolerances; budget |
| `run_sim` request | `run_id`, `candidate_id`; parameter set; material ID; mesh settings; load case; solver settings |
| `run_sim` response | Status; FreeCAD, Gmsh and solver versions; generated `.inp` reference; result artifact refs; mesh diagnostics; solver diagnostics |
| `read_result` response | Validity; `mass_g`; `max_vm` and `max_disp` with units; peak region label; contour image ref |
| Manufacturing result | `candidate_id`; FreeCAD version; profile; setups; ToolBit library hash; per-rule pass/fail/invalid with measured value; G-code and simulated-stock refs per setup |
| Prediction record | `candidate_id`, `parent_id`; D-07 schema; rationale ref; scored booleans |
| Run record | Task, config, versions, ordered tool I/O, artifact refs, predictions, diagnostics, terminal status |

## 6. Explicitly deferred

Named so that absence is a decision, not an oversight: multiple load cases per task, and the worst case over LC1–LC4; LC4 torsion as a task; buckling, fatigue, and nonlinear material; free-form CAD editing; additive-manufacturing and slicer-based checks; 4-axis and 5-axis machining; experimental 3D Surface and Waterline operations; machining time and cost estimates; the `L_bracket`, `cantilever_plate_with_hole` and `ribbed_beam` parts (`L_bracket` remains D-14's fallback); mesh convergence studies beyond D-12; multi-objective optimization over cost; **Windows and Linux packaging**; and any performance, retention, or privacy threshold beyond D-18.

Dropped from v0.1 as redundant or merged, IDs retired and not reused: v0.1 `OPT-004`/`OPT-006` (merged into the new `OPT-004`), `VER-006` (merged into `VER-005`), `VER-008` (a restatement of section 3), `OUT-004` (merged into `OUT-003`), and `DEL-010`/`DEL-011` (merged into `DEL-006`). Note that `OPT-005`–`OPT-009`, `VER-007`, and `OUT-005` were renumbered by the merges; compare against v0.1 in git before citing an old ID.

## 7. Still open

| ID | Question | Blocks |
| --- | --- | --- |
| OD-B | Release thresholds: prediction accuracy, mutation detection rate, control false-positive ceiling. | `REQ-DEL-004`, `REQ-DEL-005` |
| OD-C | Numeric tolerances: mass comparison, load-direction angle, V1 signed band, V3 displacement agreement. | `REQ-VER-001`, `REQ-VER-006`, `REQ-OPT-005`, `REQ-DEL-009` |

`OD-A` is **resolved**: the harness base is the owner's `S17Code` fork (plan M1.1, closed 2026-09-12). `OD-D` is **resolved**: `glc_v5` carries an image part unmodified, through both `/v1/vision` and an OpenAI-shape `image_url` block on `/v1/chat`, and routes it past the non-vision Ollama slot to Gemini (plan M1.5 Gate 2b, `scripts/gate2b_vision.py`, 2026-09-19). No fallback is needed. OD-B and OD-C do not block building; they block declaring the result acceptable, and are set from M5 data rather than guessed now.

## 8. Execution order

Sequencing, the M1 gates, the risk register and the cut list live in **[plan.md](plan.md)**. Three ordering constraints are normative here because requirements depend on them: `REQ-OPT-001` cannot be built before `OD-D` is answered; its camera set, image size, colormap and legend scheme are fixed by **M2**, where readability is judged by eye on `ge_bracket` before any renderer is written; and no agent result is meaningful before `REQ-DEL-009`'s V1 and V3 pass.

## 9. References

- [Project intent](intent.md) — product scope and the five deliverables.
- [GE jet engine bracket brief](ge-jet-engine-bracket.md) — interfaces, four load cases, Ti-6Al-4V limits, and §7's conflicts, now settled by D-08, D-11 and D-14.
- [SimJEB dataset brief](simjeb-dataset.md) — exact load vectors, interface coordinates, V3's reference field, and refusal-target calibration.
- [FEM geometry preparation](fem-geometry-preparation.md), [FreeCAD tutorials](freecad-tutorials.md), [FEM Workbench](fem-workbench.md), [CAM Workbench](freecad-cam-workbench.md) — the stack's own documentation; sources for D-04, D-11, D-12, D-22, D-23 and D-24.
- [EARS — Mavin](https://alistairmavin.com/ears/), syntax reference, accessed 2026-09-09.
- [ISO/IEC/IEEE 29148:2018](https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso-iec-ieee%3A29148%3Aed-2%3Av1%3Aen), structural reference, accessed 2026-09-09.

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-09 | Initial specification from intent |
| 0.2 | 2026-09-09 | Scoped to four weeks: 10 open decisions resolved to 3, 38 requirements reduced to 30, lifecycle process and source register removed, schedule added |
| 0.3 | 2026-09-09 | Stack corrected to what the machine could run — CadQuery replaces FreeCAD, uv replaces conda, CalculiX fetched rather than vendored. Added D-19 to D-22 and REQ-DEL-009 to 011/013. `OD-A` restated, `OD-D` added. Execution order moved to `plan.md` |
| 0.4 | 2026-09-12 | M0.5 added to the execution order; section 8 records that M0.5 fixes `REQ-OPT-001`'s render settings |
| 0.5 | 2026-09-17 | Owner decisions: macOS arm64 only, 3 Oct fixed, GE-style bracket as the demo part, and the intent's stack centred on FreeCAD. D-04 returns to FreeCAD 1.1.3 with spreadsheet parameters and predicate face selection; D-02/D-03 drive Gmsh and CalculiX through the FEM Workbench; D-11 is a `cnc_3axis` check in the CAM Workbench (CAM operations, `PathSimulator` residual stock, minimum wall) — no slicer; D-09 five machinable alloys; D-17 one conda-forge explicit lock plus the harness `uv` lock. D-08 LC1; D-12 calibrated on the demo part; D-14/D-15 one part, 3 tasks; D-16 3 mutants; D-22 V1 on FreeCAD's cantilever, V3 promoted, V2 Should; D-23 and D-24 added; REQ-OPT-008 added. `OD-A` resolved. Section 2.1 records departures from intent. Milestones renamed M1–M6 |
| 0.6 | 2026-09-19 | `OD-D` resolved by Gate 2b: `glc_v5` carries images to a vision model |

| 0.7 | 2026-09-21 | Added complete progress audit; corrected D-23 to the evidenced full model; identified unresolved implementation deviations without weakening Must acceptance |
| 0.8 | 2026-09-22 | D-24: `ge_bracket` `MeshRegion` 1.5 → 2.0 (owner). D-13 records the M2 measurement at both sizes. `REQ-OPT-001` render settings frozen (owner accepts M2.6) |

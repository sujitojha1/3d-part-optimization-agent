# Requirements — 3D Part Optimization Agent

| Document attribute | Value |
| --- | --- |
| Version | 0.1 |
| Date | 2026-09-09 |
| Status | Draft for stakeholder review; not an approved baseline |
| Project owner | Sujit Ojha |
| Standard | ISO/IEC/IEEE 29148:2018, Systems and software engineering — Life cycle processes — Requirements engineering |
| Requirement syntax | EARS (Easy Approach to Requirements Syntax, Mavin et al.) |
| Product scope source | [Project intent](intent.md) |

## 1. Purpose and document conventions

This specification defines the expected behavior, interfaces, quality constraints, and acceptance evidence for a runnable agent that reduces a loaded part's mass while checking structural and manufacturing constraints. It uses a tailored requirements-engineering process informed by IEEE 29148:2018 and EARS; it does not assert audited compliance with the complete standard.

Only statements identified by `REQ-*` are normative product requirements. Supporting text supplies definitions, rationale, verification guidance, and unresolved decisions. All requirements are proposed, unimplemented, and unverified unless their status is changed through the process in section 9.

Each requirement has a stable identifier, one normative statement, a source, a priority, and a verification criterion. `Must` means required for initial acceptance; `Should` means desirable with a documented waiver. Source codes beginning with `D` identify derived requirements that need owner review, rather than commitments explicitly present in the intent.

EARS conventions used here are: an unconditional statement for persistent behavior, `When` for an event, `While` for a state, `If ... then` for an unwanted condition, and `Where` for an included optional feature. Clauses may be combined when both a state and a trigger determine behavior. Every normative statement uses `shall` and identifies the responsible system.

## 2. Context, stakeholders, and scope

### 2.1 Intended outcome

Given a part, material, loads, supports, and acceptance constraints, the agent interprets finite element analysis (FEA) results visually, proposes one geometry or material change, predicts its effect, and checks that prediction through another simulation. Success requires reduced mass and passing all specified constraints. A lower mass alone is insufficient.

### 2.2 Stakeholders and system boundary

| Stakeholder or external component | Responsibility or interaction |
| --- | --- |
| Project owner | Approves scope, open decisions, and acceptance baseline |
| Engineering user | Supplies part, intended use, load cases, constraints, and material options; reviews recommendations |
| Evaluator | Executes task predicates, mutation tests, and offline scoring |
| Agent harness | Coordinates tool calls, reasoning, iteration, and recording |
| Geometry and meshing tools | Apply permitted edits and create meshes |
| FEA solver | Produces displacement and stress results for the specified setup |
| Manufacturing checker | Evaluates process-specific geometric constraints |
| Material library | Supplies material properties, units, and selection attributes |

The delivered system includes the custom harness, tool wrappers, task set, independent verifiers, mutation corpus, raw records, and runnable package. FreeCAD, Gmsh, CalculiX or FEniCS, and PrusaSlicer or a CAM check are the candidate tool stack specified by the intent. Final solver, manufacturing path, formats, and deployment environment remain open decisions.

Physical qualification, production approval, exhaustive global optimization, and proof of infeasibility over an unbounded design space are outside this draft's scope. Reported feasibility is limited to the modeled loads, material library, geometry changes, and evaluated manufacturing rules.

### 2.3 Operational sequence

1. Validate a task and establish a simulated baseline.
2. Inspect the stress contour alongside numerical results and setup data.
3. Record one proposed change and a structured prediction before execution.
4. Apply the change, remesh as needed, and rerun the checks.
5. Evaluate constraint satisfaction and prediction accuracy; retain the evidence.
6. Repeat within the declared search budget, then return a verified candidate or an evidence-backed termination outcome.

## 3. Definitions and acceptance semantics

| Term | Meaning |
| --- | --- |
| Task | Part geometry, units, loads, supports, material library, permitted changes, process rules, targets, and execution budget |
| Baseline | Initial valid part evaluated under the same acceptance conditions as candidates |
| Candidate | One geometry and material assignment evaluated under the task's load cases |
| Safety factor, `SF` | Positive task-specified factor, at least 1, applied to material yield strength |
| Structural pass | For every required load case, valid maximum von Mises stress is at most `yield_strength / SF`, and maximum displacement is at most the specified limit |
| Manufacturing pass | Every applicable rule in the task's declared manufacturing profile passes |
| Successful reduction | Candidate mass is below baseline mass by more than the configured comparison tolerance, with structural and manufacturing passes |
| Target achieved | Successful reduction that also meets the task's explicit mass target, when supplied |
| Explored frontier | Recorded nondominated evaluated candidates, compared on mass and constraint violations; not proof of a global optimum |
| Prediction accuracy | Agreement between a pre-execution structured prediction and the next valid simulation, under the task's scoring rule |
| Invalid result | Missing, failed, non-finite, or setup-inconsistent solver/checker evidence; never a constraint pass |

The initial stress criterion assumes the selected analysis and material support a yield-based von Mises check. Applicability to other failure modes is unresolved in `OD-01`. Units and tolerances are explicit task data; the draft supplies no invented load magnitudes, wall thicknesses, solver error tolerances, or response-time targets.

## 4. Source register and stakeholder needs

| Source | Intent section or derivation | Stakeholder need |
| --- | --- | --- |
| S1 | One-line brief; Why this is not a numerical optimiser | Reduce mass through geometry and material reasoning |
| S2 | The loop; Vision matters here | Interpret spatial stress evidence and test a stated reason |
| S3 | Verifier | Check mass, stress, displacement, manufacturability, and prediction accuracy |
| S4 | Mutation corpus | Detect misleading simulation inputs and results |
| S5 | The refusal case | Explain failure to achieve a target using explored evidence |
| S6 | Stack; The five deliverables | Ship a custom, reproducible, independently evaluable package |
| D1 | Derived from S3–S4 | Validate task data and prevent invalid evidence from passing |
| D2 | Derived from S5–S6 | Bound execution and distinguish search exhaustion from demonstrated infeasibility |
| D3 | Derived from S6 | Preserve provenance and enable offline rescoring |

## 5. Functional requirements

### 5.1 Task intake and baseline

| ID | EARS requirement | Source | Priority | Verification / acceptance criterion |
| --- | --- | --- | --- | --- |
| REQ-IN-001 | When a task is submitted, the system shall validate its required fields against the versioned task schema. | D1 | Must | Test complete input and one missing-field fixture per required field; incomplete tasks fail validation. |
| REQ-IN-002 | If a task contains inconsistent or unsupported physical units, then the system shall reject the task with the affected field identified. | S4, D1 | Must | Inject a declared Pa/MPa mismatch and an unsupported unit; both are rejected with field-specific diagnostics. |
| REQ-IN-003 | When a valid task starts, the system shall evaluate the initial part as its baseline. | S1, S3 | Must | Baseline record contains mass, stress, displacement, and manufacturing results linked to the original part. |
| REQ-IN-004 | If a required baseline check is invalid, then the system shall terminate optimization with an invalid-baseline outcome. | D1 | Must | Failed and non-finite baseline fixtures produce no successful optimization outcome. |

### 5.2 Reasoning and optimization loop

| ID | EARS requirement | Source | Priority | Verification / acceptance criterion |
| --- | --- | --- | --- | --- |
| REQ-OPT-001 | When valid FEA results become available, the system shall supply the stress contour image to the agent's visual interpretation step. | S2 | Must | Inspect a run trace for an actual image input linked to the matching solver result. |
| REQ-OPT-002 | When the agent interprets a stress contour, the system shall record its identified stress-concentration region. | S2 | Must | A benchmark with a known fillet concentration yields a recorded region that the fixture's spatial predicate can evaluate. |
| REQ-OPT-003 | When the agent proposes a candidate, the system shall restrict the proposal to one permitted geometry edit or one material substitution. | S2 | Must | A compound geometry-and-material proposal is rejected; each permitted single edit is accepted. |
| REQ-OPT-004 | Before a proposed change is executed, the system shall persist the agent's rationale for that change. | S2 | Must | Record ordering establishes that rationale persistence precedes the tool invocation. |
| REQ-OPT-005 | Before a proposed change is executed, the system shall persist a structured prediction of its expected effect. | S2, S3 | Must | Prediction includes the affected metric or region, expected change, and scoring-rule reference before execution. |
| REQ-OPT-006 | When a candidate change has been applied, the system shall evaluate the candidate under every required task load case. | S2, S3 | Must | A multi-load-case fixture produces results for every required case linked to the candidate version. |
| REQ-OPT-007 | When the next valid candidate evaluation completes, the system shall score the preceding prediction against that evaluation using the task's prediction rule. | S3 | Must | Known correct and incorrect predictions receive the expected scores from structured results. |
| REQ-OPT-008 | When the agent considers a material substitution, the system shall provide its yield strength, density, cost, machinability, corrosion resistance, and availability attributes to the selection step. | S1 | Must | Trace inspection shows all six attributes, including explicit unknown values, for considered materials. |
| REQ-OPT-009 | If a material lacks a property required for a task's acceptance checks, then the system shall exclude that material from accepted candidates. | D1 | Must | A material missing yield strength or density cannot produce an accepted candidate. |

### 5.3 Verification and abnormal conditions

| ID | EARS requirement | Source | Priority | Verification / acceptance criterion |
| --- | --- | --- | --- | --- |
| REQ-VER-001 | When a candidate is evaluated, the system shall report its mass in grams. | S3 | Must | Known-volume, known-density fixtures produce the expected gram values within the declared tolerance. |
| REQ-VER-002 | When valid structural results are available, the system shall determine structural pass using the criteria in section 3. | S3 | Must | Boundary fixtures at, below, and above both limits produce the expected result for every load case. |
| REQ-VER-003 | When a candidate is evaluated, the system shall determine manufacturing pass using the task's applicable process rules. | S3 | Must | Fixtures violating each enabled minimum-wall, draft, or overhang rule fail the corresponding check. |
| REQ-VER-004 | If any required candidate check is invalid, then the system shall classify the candidate as unverified. | D1 | Must | Timeout, missing-output, and non-finite fixtures never receive a pass. |
| REQ-VER-005 | If a stress concentration meets the configured singularity-suspicion criteria, then the system shall flag the result for mesh-sensitivity investigation. | S2, S4 | Must | The sharp-corner mutation is flagged according to the selected diagnostic protocol in OD-04. |
| REQ-VER-006 | While a singularity flag remains unresolved, the system shall classify the affected structural result as unverified. | D1 | Must | A flagged result cannot contribute to a structural pass before recorded resolution. |
| REQ-VER-007 | If the solver-applied load direction differs from the task's declared direction beyond the configured tolerance, then the system shall reject the simulation setup. | S4 | Must | Wrong-direction mutation is detected by comparing task intent with applied solver data. |
| REQ-VER-008 | When a candidate is classified as a successful reduction, the system shall require the successful-reduction conditions in section 3 to hold. | S1, S3 | Must | Lower-mass candidates failing stress, displacement, or manufacturing checks are not successful. |

### 5.4 Termination and explanation

| ID | EARS requirement | Source | Priority | Verification / acceptance criterion |
| --- | --- | --- | --- | --- |
| REQ-OUT-001 | When the declared iteration or elapsed-time budget is exhausted, the system shall stop launching new optimization evaluations. | D2 | Must | A small-budget fixture launches no further evaluation after exhaustion; in-flight timeout behavior follows OD-06. |
| REQ-OUT-002 | When a run terminates, the system shall report its outcome as target-achieved, improved-without-target, target-not-achieved, invalid-input, invalid-baseline, or execution-failed. | S5, D2 | Must | Fixtures cover each outcome with matching machine-readable status and explanation. |
| REQ-OUT-003 | When a valid search terminates without achieving the mass target, the system shall report the explored frontier with each candidate's material, mass, and constraint results. | S5 | Must | An unattainable-target fixture returns a frontier linked to stored evaluations. |
| REQ-OUT-004 | If the search does not establish infeasibility over the declared finite search space, then the system shall describe target failure as not achieved within the explored scope. | S5, D2 | Must | Budget-exhaustion fixture does not assert universal infeasibility. |
| REQ-OUT-005 | When a run returns a recommended candidate, the system shall provide an explanation linked to its baseline comparison, change history, and verification evidence. | S1, S2 | Must | Every reported metric and accepted change resolves to a persisted artifact. |

## 6. Interfaces, data, and delivery requirements

### 6.1 Required interface contracts

These contracts define logical content; file encodings and concrete API signatures are pending OD-02.

| Interface | Required content |
| --- | --- |
| Task input | Task ID; geometry reference and units; material records with property units and provenance; loads and supports; permitted edits; safety factor; displacement limit; manufacturing profile; optional mass target; comparison tolerances; execution budget |
| `run_sim` request | Run/candidate IDs; immutable geometry and material references; mesh settings; complete load cases and supports; solver settings |
| `run_sim` response | Execution status; solver version; applied-setup reference; result artifact references; diagnostic information |
| `read_result` response | Validity status; mass in grams; per-case stress and displacement with units; stress contour and spatial-region references |
| Manufacturing result | Candidate ID; checker version; profile; per-rule pass/fail/invalid status and measurements |
| Prediction record | Candidate ID; preceding candidate ID; expected metric or spatial change; rationale reference; scoring rule and tolerance |
| Run record | Task and configuration; versions; ordered model/tool inputs and outputs; artifact references; predictions; diagnostics; terminal status |

### 6.2 Product and evaluation constraints

| ID | EARS requirement | Source | Priority | Verification / acceptance criterion |
| --- | --- | --- | --- | --- |
| REQ-DEL-001 | The system shall implement its orchestration in a project-owned harness without an agent framework. | S6 | Must | Dependency and source inspection finds no LangChain, CrewAI, or equivalent framework driving the loop. |
| REQ-DEL-002 | The system shall expose the chosen solver through callable `run_sim` and `read_result` tool interfaces. | S6 | Must | Integration fixture invokes both interfaces and checks their versioned contracts. |
| REQ-DEL-003 | The distribution shall include vendored, version-pinned solver/checker dependencies for the declared supported environment. | S6 | Must | Package inspection and clean-environment installation match the dependency manifest. |
| REQ-DEL-004 | The distribution shall provide a documented command that executes a bundled end-to-end task on a clean supported machine. | S6 | Must | Execute the command in the OD-05 environment without undeclared preinstalled project dependencies. |
| REQ-DEL-005 | The system shall provide a task set with an executable acceptance predicate for each task. | S6 | Must | Enumerate task IDs and run every associated predicate on known pass/fail tool-output fixtures. |
| REQ-DEL-006 | When an acceptance predicate scores a task, the system shall derive the decision exclusively from structured tool outputs. | S6 | Must | Changing agent prose alone leaves acceptance scores unchanged. |
| REQ-DEL-007 | The distribution shall include mutations for sharp-corner singularities, wrong load direction, and incorrect material units. | S4, S6 | Must | Inventory contains all three runnable mutation categories paired with valid controls. |
| REQ-DEL-008 | When the mutation corpus is scored, the system shall report the number detected divided by the number executed. | S4, S6 | Must | Controlled outcomes yield the expected numerator, denominator, and fraction; zero executions are reported as not evaluated. |
| REQ-DEL-009 | Before scoring a run, the system shall persist its raw run record to disk. | S6 | Must | Scoring starts only after the record is readable; a write failure prevents scoring. |
| REQ-DEL-010 | When a saved run is rescored, the system shall compute the new score without rerunning the model or engineering tools. | S6 | Must | Disable model and solver access and successfully rescore a saved fixture. |
| REQ-DEL-011 | The system shall attach input and configuration provenance to each persisted evaluation. | D3 | Must | Every evaluation resolves to exact geometry, material, setup, tool versions, and model configuration. |
| REQ-DEL-012 | If a tool execution fails, then the system shall persist its failure diagnostics with the affected candidate identifier. | D3 | Must | Inject solver/checker failures and retrieve their candidate-linked diagnostics. |

## 7. Assumptions, dependencies, and open decisions

Loads, supports, intended use, and material data are supplied by the task author. A direction check can detect disagreement with that declared intent; it cannot determine the true physical load without an independent reference. Declared unit checks cannot reliably detect every plausibly valued but mislabeled material property without provenance or reference bounds.

| ID | Decision required before baseline approval | Owner | Affected requirements |
| --- | --- | --- | --- |
| OD-01 | Supported part family, analysis regime, material behavior, and excluded failure modes such as buckling or fatigue | Project owner | IN-001, VER-002, OPT-009 |
| OD-02 | Geometry formats, task/result schemas, unit normalization, and region-identification representation | Project owner | IN-001–002, OPT-002, DEL-002 |
| OD-03 | Material library source, property provenance, unknown-attribute policy, and permitted edits | Project owner | OPT-003, OPT-008–009 |
| OD-04 | Mesh-convergence/singularity protocol and numerical, spatial, load-direction, and prediction tolerances | Project owner | OPT-007, VER-001–002, VER-005–007 |
| OD-05 | Selected solver and manufacturing checker, supported OS/runtime, package licensing, and deployment target | Project owner | VER-003, DEL-002–004 |
| OD-06 | Iteration/time budgets, per-tool timeouts, in-flight cancellation, and representative runtime/memory limits | Project owner | OUT-001, DEL-012 |
| OD-07 | Benchmark task count and coverage, target prediction accuracy, mutation detection threshold, and false-positive limit | Project owner | OPT-007, DEL-005–008 |
| OD-08 | Manufacturing profiles and applicability of minimum wall, draft, and overhang checks | Project owner | VER-003 |
| OD-09 | Availability and reuse scope of the EAG V3 code required by the intent | Project owner | DEL-001 |
| OD-10 | Model/provider choice, handling of part data sent externally, record retention, and credential management | Project owner | OPT-001, DEL-009–011 |

Requirement references in this table omit the `REQ-` prefix for readability. Quantitative performance, privacy, and retention requirements need approved operating constraints before they can be baselined. The absence of those values is a draft limitation, not evidence that the properties have been satisfied.

## 8. Verification, validation, and traceability

The acceptance criteria beside each requirement define planned verification, not completed test results. Numerical checks use the approved task tolerances. Independent task-success predicates consume engineering tool outputs; prediction scoring compares structured predictions with those outputs and is reported separately from task success.

| Validation scenario | Requirement coverage | Expected evidence |
| --- | --- | --- |
| Geometry-based mass reduction | IN-003, OPT-001–007, VER-001–003, VER-008, OUT-005 | Baseline/candidate artifacts, visible stress interpretation, single edit, prediction score, all constraint passes |
| Material tradeoff | OPT-008–009, VER-001–003 | Attribute comparison, material provenance, rerun results |
| Broken setup and misleading stress | IN-002, VER-004–007, DEL-007–008 | Three mutation categories, valid controls, detection fraction and false-positive results |
| Unachievable target | OUT-001–004 | Finite known-infeasible fixture, explored frontier, scoped refusal; separate budget-exhaustion fixture |
| Reproducible delivery | DEL-001–006, DEL-009–012 | Clean-machine run, dependency manifest, raw records, independent predicates, offline rescore |

Release acceptance requires verification evidence for every Must requirement, owner validation of the scenarios above, and resolution of applicable open decisions. Any waived requirement is explicitly recorded with owner, rationale, risk, and target resolution; an unresolved Must is not silently counted as passing.

## 9. Requirements lifecycle and change control

1. **Elicit:** review the intent with the owner and engineering user; record assumptions and decisions with sources.
2. **Analyze:** resolve feasibility, conflict, interface, and quantitative-threshold questions; separate required outcomes from tool choices.
3. **Specify:** write atomic EARS statements with stable IDs, source/rationale, priority, and observable verification criteria.
4. **Review and validate:** check necessity, clarity, consistency, feasibility, verifiability, and stakeholder agreement; resolve the open decisions that block acceptance.
5. **Baseline:** obtain owner approval and record the approved version and date in this document.
6. **Implement and verify:** link each requirement to implementation artifacts, test identifiers, and stored evidence; track status as proposed, approved, implemented, verified, or retired.
7. **Manage changes:** record the requested change, reason, impacted requirements/interfaces/tests, owner decision, and new baseline version. Preserve retired IDs and never reuse them.

For each approved requirement, the maintained traceability record contains: requirement ID, owner, status, source, rationale, dependencies, implementation reference, verification ID, evidence location, and last change. This draft's tables establish source-to-requirement-to-verification links; implementation and execution evidence remain pending.

| Version | Date | Change | Approval |
| --- | --- | --- | --- |
| 0.1 | 2026-09-09 | Initial specification derived from project intent using the requested standard and EARS | Pending |

## 10. References

- [Project intent](intent.md), local product scope and deliverables.
- [ISO/IEC/IEEE 29148:2018 — official ISO overview](https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso-iec-ieee%3A29148%3Aed-2%3Av1%3Aen), requirements-engineering reference, accessed 2026-09-09. The 2018 edition is the edition requested for this project.
- [Alistair Mavin — EARS official guide](https://alistairmavin.com/ears/), syntax reference, accessed 2026-09-09. EARS originated with Mavin et al.; the requirement statements here are project-specific.

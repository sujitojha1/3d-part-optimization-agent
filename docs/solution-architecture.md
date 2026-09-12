# Solution Architecture — 3D Part Optimization Agent

| Attribute | Value |
| --- | --- |
| Version | 0.2 |
| Date | 2026-09-12 |
| Owner | Sujit Ojha |
| Status | Design sketch. Nothing here is built yet |
| Companions | [Intent](intent.md) — why · [Requirements](requirements.md) — what · [Plan](plan.md) — when · this — how |

This is the design document. It records structure and technical choices with their reasoning, so that a decision made in week 1 can be re-examined in week 3 without re-deriving it. It deliberately does **not** restate requirements; where a choice is already fixed, it cites the decision ID (`D-nn`) rather than repeating the rationale.

Section 9 lists what is still undecided. That list is the agenda for the next pass.

---

## 1. Brief

The system takes a loaded part and makes it lighter without making it fail, by reading the FEA stress contour the way an engineer does rather than searching a parameter space.

Everything follows from one structural idea: **a deterministic evaluation pipeline wrapped in a non-deterministic reasoning loop, with a judge that neither can reach.**

- The **pipeline** is a pure function. Given a parameter set and a material, it always produces the same mass, stress, displacement, region label and contour image. It contains no model calls and no judgement.
- The **loop** is the agent. It looks at a picture, forms a belief about *where* and *why*, commits that belief to disk, changes exactly one thing, and is scored on whether the belief held.
- The **judge** is ordinary code the agent cannot edit or influence. It reads the pipeline's structured output and decides. It never reads the agent's prose.

The project's novelty sits in the second bullet, and its credibility sits entirely in the first and third. A reasoning loop over an unvalidated pipeline produces confident nonsense; a judge the agent can reach produces a green score and no information.

---

## 2. Layers

```
 ┌──────────────────────────────────────────────────────────────┐
 │  L0  Harness — S17Code (:8113)                               │
 │      planner · capability registry · journal · checkpoints   │
 │      protected-path guard · skills loader                    │
 └───────────────┬──────────────────────────────────────────────┘
                 │ capability calls (typed)
 ┌───────────────▼──────────────────────────────────────────────┐
 │  L1  Capability seam                                         │
 │      run_sim · read_result · check_manufacturing             │
 │      render_contour · apply_candidate                        │
 └───────────────┬──────────────────────────────────────────────┘
                 │ plain Python, no agent, no I/O to models
 ┌───────────────▼──────────────────────────────────────────────┐
 │  L2  Engineering core — the deterministic pipeline           │
 │      parts/ → meshing/ → solver/ → parse → render/           │
 └───────────────┬──────────────────────────────────────────────┘
                 │ structured results only
 ┌───────────────▼──────────────────────────────────────────────┐
 │  L3  The judge — PROTECTED, unreachable from L0/L1           │
 │      verify/ · tasks/ · materials/ · mutations/ · predicates │
 └──────────────────────────────────────────────────────────────┘

 ┌──────────────────────────────────────────────────────────────┐
 │  Gateway — glc_v5 (:8111)   provider keys · routing · vision │
 └──────────────────────────────────────────────────────────────┘
```

**Why the seam at L1 matters.** The solver is reached as a *capability with a typed contract*, never as an allowlisted shell command (D-20). Two things fall out for free: the command allowlist stays narrow enough to be auditable, and `run_sim` has a declared request/response shape, which is what `REQ-DEL-002` asks for anyway. Adding `ccx` to `S17_ALLOWED_COMMANDS` would have given the agent a string-shaped door into the filesystem and bought nothing.

**Why L2 holds no model calls.** It is what makes the pipeline replayable, cacheable and testable without a network or an API key. The two closed-form validation cases (`REQ-DEL-009`) are ordinary unit tests against L2.

**Why L3 is a separate layer rather than a directory convention.** The agent in this project can, in principle, write code — S17Code's whole point. An agent asked to reduce mass that can edit `tasks/` will lower the safety factor rather than remove material, and that is not dishonesty, it is a loop finding the cheapest route to a green result. The guard is enforced in code and every refusal is recorded.

---

## 3. The deterministic pipeline

```
CandidateSpec ──▶ CadQuery ──▶ STEP ──▶ Gmsh ──▶ .inp ──▶ ccx ──▶ .frd ──▶ EvaluationResult
   params            solid      B-rep    C3D10    solver   results      + contour.png
   material_id                          + tags            + labels
```

**The pipeline is a pure function of `CandidateSpec`.** This is the single most useful property in the design and several requirements collapse into it:

- **Offline rescoring** (`REQ-DEL-007`) — the scorer reads stored results; nothing needs re-running.
- **Provenance** (`REQ-DEL-006`) — the spec *is* the provenance.
- **Caching** — an identical spec can return a stored result without re-solving.

```python
CandidateSpec = {
    part_id, parameters{...}, material_id,
    mesh_settings,          # task data, never agent-set (D-21)
    load_case, supports,
    tool_versions{cadquery, gmsh, ccx},
}
candidate_id = sha256(canonical_json(CandidateSpec))
```

`tool_versions` is inside the hash deliberately. A CalculiX upgrade must invalidate every cached result rather than silently mixing solver generations inside one frontier.

### Region labels are carried, not inferred

The chain that makes spatial claims checkable (D-06):

```
CadQuery tags faces  ──▶  Gmsh physical groups  ──▶  .inp element sets
                                                          │
peak element  ──▶  which set contains it?  ──▶  one label │
```

The agent names a region; the verifier does a set-membership test. No geometry reasoning at scoring time, no fuzzy spatial matching, no tolerance to argue about.

### One internal unit system

L2 works in SI throughout — metres, pascals, kilograms — and **converts only at the boundary**. No conversion happens inside the pipeline. Task intake validates declared units and rejects mismatches by field (`REQ-IN-002`); the cantilever validation case then catches anything that slipped through, because a Pa/MPa error shows up there as a factor of 10⁶ rather than a plausible-looking drift.

### Errors are values

Every stage returns a result carrying validity, never an exception crossing the capability seam. Missing, failed, non-finite, timed-out or setup-inconsistent evidence produces `unverified`, and `unverified` is never a pass (`REQ-VER-004`). A crashed solve must be distinguishable from a solve that ran and reported low stress.

---

## 4. The agent loop

```
baseline ─▶ render ─▶ READ CONTOUR ─▶ region claim
                                          │
                                          ▼
                                     PREDICT  ── persisted before any tool call
                                          │
                                          ▼
                                   one edit (D-05)
                                          │
                                          ▼
                                      evaluate
                                          │
                                          ▼
                                    SCORE prediction ─▶ next iteration
```

**Prediction before execution is the whole novelty**, and it is worthless if written afterwards. The ordering is enforced by record sequence, not by convention (`REQ-OPT-004`).

**Every attempt is a new node.** The graph is a straight line — nothing points backwards — so a failed iteration stays in the journal as evidence rather than being overwritten. This is inherited from the harness and it is also what makes the explored frontier real rather than reconstructed.

### Rerunnable at the graph, cached at the implementation

These sound contradictory and are not, and the distinction is worth stating because getting it wrong costs a day:

- **At the graph level**, `run_sim` is declared **rerunnable** (D-19). The harness deduplicates identical capability calls; without the declaration the loop silently stops iterating and presents as a hang. Every attempt must earn its own node.
- **At the implementation level**, `run_sim` is **content-addressed**. Identical `CandidateSpec` returns the stored result rather than re-solving.

The graph keeps the history; the cache keeps the cost down. The D-12 singularity re-solve is not a cache hit, because a different mesh refinement is a different spec.

### Contour rendering is a run-scoped context

```python
RenderContext = {cameras: [...fixed...], vmin, vmax}   # fixed at baseline, carried for the run
```

The legend range is locked across the run (`REQ-OPT-001`). An auto-rescaling colour bar makes two iterations incomparable, which degrades the vision loop into noise without failing anything. When a candidate exceeds the baseline range, the render **clips and flags** rather than rescaling — rescaling would break comparability silently, and hiding the exceedance would be worse.

---

## 5. Data at rest

```
runs/<run_id>/            journal, checkpoints, predictions, scores, terminal status
artifacts/<candidate_id>/ spec.json  geometry.step  mesh.inp  result.frd
                          result.json  contour.png  manufacturing.json
tasks/       PROTECTED    task definitions with predicates
materials/   PROTECTED    the closed 8-alloy library, sourced per record
mutations/   PROTECTED    6 mutants + paired controls
skills/                   SKILL.md — how to approach the work, never what is permitted
vendor/                   ccx, fetched by pinned URL + SHA, gitignored
```

Run records reference artifacts by `candidate_id` rather than embedding them, which keeps the journal small enough to read and makes the artifact store deduplicating by construction.

---

## 6. Trust boundaries

Four rules, each inherited from something that has already gone wrong in the course material:

1. **The model proposes; deterministic code decides.** Every accept/reject is code the agent did not write.
2. **The judge is unreachable.** `verify/`, `tasks/`, `materials/`, `mutations/` are protected paths, refusals recorded (D-20).
3. **A skill is instruction, never authority.** The single-edit rule and the mesh-change refusal live in the runtime. Writing them in `SKILL.md` would make them advice, and advice is not binding.
4. **Credentials live on the gateway.** The agent process holds none; `glc_v5` on 8111 owns provider keys and routing (D-18).

A fifth follows from the domain rather than the harness: **mesh density is not agent-controllable** (D-21). The cheapest way to make a stress concentration disappear is to coarsen the mesh until it does. That is the same instinct as deleting a failing test, and it must be refused rather than discouraged.

---

## 7. Technical choices

Fixed, with the reasoning compressed. Full rationale sits in `requirements.md` section 2.

| Area | Choice | One-line reason |
| --- | --- | --- |
| CAD | CadQuery 2.8 + `cadquery-ocp` 7.9.3.1.1 | Verified cp313 `win_amd64` wheels; FreeCAD has no reliable pip path on Windows (D-04) |
| Mesh | Gmsh 4.15.2, second-order tets | First-order tets are over-stiff and report bad stress, which would poison prediction accuracy (D-03) |
| Solver | CalculiX 2.10, GE Windows build | Text in, text out, scriptable and diffable; fetched by pinned URL + SHA, never committed — GPL, public repo (D-02) |
| Packaging | `uv` lockfile, Python 3.13 | Whole stack verified to resolve with no conda, which is what the target machine has (D-17) |
| Manufacturing | FDM only — ray-cast min wall, facet-normal overhang | Hours of geometry work versus days of driving a slicer as an external process (D-11) |
| Render | PyVista + VTK, off-screen | Resolves clean; off-screen on Windows is unproven and is M0 Gate 2 |
| Edits | 4 named parameters on a parametric script | Free-form CAD editing is its own multi-week project (D-04, D-05) |
| Model access | Through `glc_v5` | Matches the harness split; the agent holds no credential (D-18) |

---

## 8. What the architecture buys, per requirement

A short sanity check that the structure actually earns its keep:

| Requirement | Satisfied by |
| --- | --- |
| `REQ-DEL-007` offline rescoring | L2 purity + content-addressed artifacts |
| `REQ-DEL-006` provenance | `CandidateSpec` is the provenance, hashed |
| `REQ-VER-004` invalid never passes | Errors as values across the L1 seam |
| `REQ-OPT-002` region claim scoreable | Label chain carried from CAD tags to element sets |
| `REQ-OPT-005` prediction scoring | Structured D-07 schema, compared to structured results |
| `REQ-DEL-004` predicates ignore prose | L3 reads only L2 output, by construction |
| `REQ-OPT-001` comparable contours | Run-scoped `RenderContext`, clip-and-flag |

---

## 9. Open architecture questions

The agenda for the next pass. None block M0. Questions 1, 2 and 6 are answered by **M0.5**'s hand pass — by experiment and measurement, not by argument — and 4, 5 and 7 stay open into M1.

1. **Does the agent see the numbers before or after it reads the picture?** If `max_vm` is in context first, the model may anchor on it and the contour becomes decorative — which would quietly hollow out the project's central claim while every metric still looks fine. A two-step exchange (read image → commit the region claim → then reveal numerics) would preserve the thesis and make the region claim independently scoreable. This is the most consequential open question here. → **M0.5 task 8** settles it by running the same contour both ways and comparing the region claim.
2. **Where does the proposal step live** — a planner node, or a capability with a typed request? A capability makes the single-edit rule trivially enforceable at the seam; a planner node keeps the graph honest about who decided what. → Decided in **M0.5 task 9**'s integration spec, against a real transcript rather than in the abstract.
3. **Is prediction scoring part of the judge?** It reads structured output and produces a number that is reported, which argues for protected. It is also not a task predicate. Probably `verify/`, to decide.
4. **Frontier representation** — recomputed from stored candidates on demand, or maintained incrementally? Recompute is simpler and cheap at 8 candidates, and it cannot drift.
5. **Retry policy at the L1 seam.** A timed-out solve is `unverified`, but is it retried once? The harness's answer elsewhere is that an operation with an unknown outcome is a question, not a retry.
6. **Does the agent get code-editing capability at all?** If not — and this project mostly calls tools — the cleanest move is to disable those capabilities explicitly rather than register them and lean on the guard. → **M0.5 task 9** names the answer, since the integration spec enumerates every capability the exchange actually needs.
7. **Multi-part generalisation.** `L_bracket` first and completely; whether `parts/` needs a shared base or just three independent scripts is not yet clear, and guessing early would over-abstract.

---

## 10. Revision log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-09 | First pass: layers, pipeline purity, the rerunnable/cached distinction, trust boundaries, open questions |
| 0.2 | 2026-09-12 | Open questions 1, 2 and 6 assigned to M0.5's hand pass, which supplies the evidence they need |

# Intent — Project 4: 3D Part Optimization

**Owner:** Sujit Ojha
**Track:** Route B — four-week build, deployed, with its own harness.

## One-line brief

Given a loaded part, make it lighter without making it fail. The agent reads
the FEA results, reasons about geometry and material together, and explains
itself.

## Why this is not a numerical optimiser

A topology optimiser searches a parameter space. This agent reads the stress
plot the way an engineer does — decides the failure is at a fillet rather than
the web, and reasons about whether the right answer is more material, a
different radius, or a different alloy.

Material selection is the part no optimiser handles: yield strength, density,
cost, machinability, corrosion resistance and availability trade against each
other, and the right answer depends on what the part is for.

## The loop

```
mesh -> FEA -> READ THE STRESS CONTOUR VISUALLY
     -> "failing at the fillet, not the web"
     -> propose one change, in geometry or material, and state why
     -> re-run and check whether the reason held
```

Vision matters here. The colour plot carries information the raw max-stress
number does not: where the concentration is, whether it is a mesh singularity
from a sharp corner, whether the load path has shifted.

## Verifier

| Metric | What it checks |
| --- | --- |
| mass | down, in grams |
| max von Mises | below yield, with the stated safety factor |
| displacement | within limit |
| manufacturability | machinable or printable — minimum wall, draft, overhang |
| prediction accuracy | did the agent's stated reason match what the next FEA showed |

That last row is the interesting one: it scores the reasoning rather than the
outcome.

## Mutation corpus

- Meshes with singularities at sharp corners producing fake infinite stress
- A load case applied in the wrong direction
- A material card with the wrong units (MPa against Pa)

An agent that trusts the number without sanity-checking the setup fails these.

## The refusal case

A mass target that cannot be met at the required safety factor with any
material in the library. The agent must say so and show the frontier it
explored.

## Stack

FreeCAD · Gmsh (meshing) · CalculiX or FEniCS (FEA) · PrusaSlicer or a CAM
check (manufacturability).

## The five deliverables every Route B project ships

1. **Your harness** — your own loop. No LangChain, no CrewAI, no agent
   framework. Reuse your EAG V3 code.
2. **The open-source tool, wrapped** — the solver/checker becomes tool calls
   the agent can make (`run_sim`, `read_result`). Vendored and pinned, so the
   package runs on a clean machine.
3. **A task set with verifiers** — each task has a predicate that reads the
   tool's output and decides. It never reads the agent's prose.
4. **A mutation corpus** — deliberately broken inputs. The checker either
   catches them or it does not, and the fraction caught is a number you report.
5. **Raw run records** — every run written to disk before scoring, so the
   scorer can change without re-running the model.

> "I used FreeCAD" is not a project. A downloadable, runnable package that
> happens to use FreeCAD inside it is one.

**Source:** Axiom — Route B project definitions (School of AI).
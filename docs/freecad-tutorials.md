# Reference — FreeCAD Tutorials

| Attribute | Value |
| --- | --- |
| Source | [FreeCAD wiki — Tutorials](https://wiki.freecad.org/Tutorials) |
| Publisher | The FreeCAD project wiki, CC-BY 3.0 unless a page says otherwise |
| Accessed | 2026-09-17 |
| Status | Reference input. **FreeCAD is not in this project's stack** and this page does not reopen that — see [D-04](requirements.md) and section 6 |
| Read in depth | [FEM Geometry Preparation and Meshing](#41-fem-geometry-preparation-and-meshing), [FEM Tutorial Python](#42-fem-tutorial-python), [FEM CalculiX Cantilever 3D](#43-fem-calculix-cantilever-3d) |
| Related | [Requirements](requirements.md) · [Plan](plan.md) · [Solution architecture](solution-architecture.md) · [GE bracket brief](ge-jet-engine-bracket.md) · [SimJEB dataset](simjeb-dataset.md) |

Sections 1–5 record what the FreeCAD tutorial index and three of its pages say.
Section 6 is this project's reading of what that is worth to us, and section 7 lists
the changes it argues for. Sections 6 and 7 are our interpretation, not FreeCAD's.

**Why a doc about a tool we dropped.** D-04 removed FreeCAD from the stack for
packaging reasons — no reliable pip path on Windows, its own interpreter — and put
CadQuery in its place. That decision was about *installing* FreeCAD. It said nothing
about FreeCAD's documentation, which is the best free written account of the exact
chain this project is building by hand: CAD solid → Gmsh → CalculiX `.inp` → `.frd` →
contour. The FEM pages are a domain source and a reference implementation. They are
worth having in `docs/` for that reason and no other.

---

## 1. What the index is

[wiki.freecad.org/Tutorials](https://wiki.freecad.org/Tutorials) is a curated shortlist
of tutorials the project considers high quality, followed by a comprehensive sortable
table of every tutorial on the wiki regardless of quality. The curated part is grouped
into nine topics:

| Topic | Tutorials | Relevance here |
| --- | --- | --- |
| Architecture and BIM | 7 | None |
| Modeling parts | 13 + 3 Raspberry Pi | Background on CSG vs. parametric feature modelling |
| Drafting and Sketching | 5 | None — we never draw by hand |
| Technical Drawings | 3 | None |
| **FEM** | **7** | **Direct. The core of this project** |
| CNC & 3D Printing | 2 | Marginal — see section 6.5 |
| Rendering | 4 | None — our contour is PyVista, not POV-Ray |
| Robot workbench | 1 | None. Development abandoned |
| Scripting | 3 | Indirect — Python API, macros, workbenches |

The page carries one standing caution, which applies to everything below:

> Please notice the version of FreeCAD used in the tutorial as some tutorials may use
> an old version of the program.

Versions in the comprehensive table range from 0.11 to 1.0, and some page bodies
describe features introduced in 1.1. Several curated tutorials predate the
0.17 PartDesign rework and the index says so.

---

## 2. The FEM cluster

Seven tutorials, and the only cluster that maps onto our pipeline one-for-one.

| Tutorial | Version | What it covers |
| --- | --- | --- |
| [FEM Geometry Preparation and Meshing](https://wiki.freecad.org/FEM_Geometry_Preparation_and_Meshing) | 1.0+ | Element type and order, defeaturing, symmetry, partitioning, element size, negative Jacobians, convergence, singularities |
| [CalculiX cantilever FEM analysis](https://wiki.freecad.org/FEM_CalculiX_Cantilever_3D) | 0.20 | The bundled example: run the solver, read displacement, change load direction |
| [Simple FEM introduction](https://wiki.freecad.org/FEM_tutorial) | 0.20 | Model → mesh → constraints → material → solve → visualise |
| [FEM shear analysis of a composite block](https://wiki.freecad.org/FEM_Shear_of_a_Composite_Block) | 0.17 | Mesh regions, two materials, sliding constraints, clip plane |
| [Analysis of reinforced concrete with FEM](https://wiki.freecad.org/Analysis_of_reinforced_concrete_with_FEM) | 0.19 | Reinforcement level against brittle failure |
| [Electrostatic — capacitance of two balls](https://wiki.freecad.org/FEM_Example_Capacitance_Two_Balls) | 0.19 | Elmer solver, clip filter |
| [Post-processing FEM results with Paraview](https://wiki.freecad.org/Post-Processing_of_FEM_Results_with_Paraview) | 0.19 | Getting data out of FEM into Paraview |

Two more sit only in the comprehensive table and matter to us:
[FEM Tutorial Python](https://wiki.freecad.org/FEM_Tutorial_Python) (0.18+, intermediate)
and [Transient FEM analysis](https://wiki.freecad.org/Transient_FEM_analysis).

---

## 3. The other clusters, briefly

**Modeling parts.** The index splits modelling into two workflows: constructive solid
geometry with the Part workbench, and parametric feature editing with PartDesign. The
PartDesign workflow changed substantially at 0.17 and some tutorials still show 0.16.
[Basic Part Design Tutorial 019](https://wiki.freecad.org/Basic_Part_Design_Tutorial_019)
is called out as the rewrite that "avoids the topological naming problem" — the same
problem that makes free-form CAD editing unsuitable for an agent and that D-04 sidesteps
by allowing only named-parameter edits.

**Scripting.** Three entries — [Python scripting tutorial](https://wiki.freecad.org/Python_scripting_tutorial),
[How to install macros](https://wiki.freecad.org/How_to_install_macros),
[How to install additional workbenches](https://wiki.freecad.org/How_to_install_additional_workbenches)
— plus [Topological data scripting](https://wiki.freecad.org/Topological_data_scripting)
in the comprehensive table. Aimed at users already familiar with the program.

**CNC & 3D Printing.** [CAM Workbench for the impatient](https://wiki.freecad.org/CAM_Walkthrough_for_the_Impatient)
(job, tool, path operations, G-code) and
[Manual:Preparing models for 3D printing](https://wiki.freecad.org/Manual:Preparing_models_for_3D_printing)
(solid → mesh → STL → Slic3r/Cura/CAM for G-code). Both describe the slicer-driven route
that D-11 explicitly rejected in favour of a geometric rule check.

---

## 4. Read in depth

### 4.1 FEM Geometry Preparation and Meshing

Beginner-level, by NewJoker. Its own infobox says FreeCAD 1.0 or above; the index table
in section 5 says 0.21 — the source page disagrees with itself, and nothing here depends
on which is right. Despite the level tag it is the densest page in the
set and it opens on the point the whole project rests on: *garbage in, garbage out*. FEM
is an advanced method and needs properly prepared geometry and mesh to give reasonable
answers.

**Geometry type.** Wires for beams, surfaces for shells and 2D, solids for solid
elements. If a part is slender (cross-section < 1/10 of length) it should be a beam
model; if thin-walled (thickness < 1/10 of a typical dimension) it should be a shell.
CalculiX expands its beam and shell elements to solids internally, and the page still
recommends using them. Getting three to five elements through the thickness of a
thin-walled solid is what makes the solid route expensive.

**Element order and type.** Hexahedra and quadrilaterals are preferable to tets and
triangles, but complex geometry cannot be hex-meshed and FreeCAD's hex capability is
very limited. Second-order elements are preferred "in most cases", and for tets
specifically first-order versions are "normally not recommended for regular usage" —
filler elements in low-importance regions only.

**Negative Jacobians.** The page's most useful passage for us. Second-order meshing can
fail on geometry with small edges and faces, because the mesher must put mid-side nodes
*on the geometry*; on tight curvature that stretches elements until they invert. Named
remedies, in the page's order: set `Second Order Linear` so mid-side nodes sit at the
midpoint of straight edges instead of snapping to the surface; switch mesher; reduce
element size; use a standalone mesher's high-order tools; and only as a last resort drop
to first order. It closes by noting that negative Jacobians are usually a symptom of
unprepared geometry rather than a meshing bug.

**Element size.** Automatic meshers "typically generate very coarse, unsuitable meshes
when the element size is not manually specified". The recommended practice is to know the
smallest relevant feature, set a maximum element size from it, set a minimum size to stop
tiny elements forming around small features, and refine locally at stress concentrations
rather than globally.

**Defeaturing and symmetry.** CAD models are typically too detailed for FEM. Small
fillets, small holes, welds, threads, bolts and engravings are normally removed. Planar
symmetry (1/2, 1/4, 1/8) is recommended whenever geometry, loads, boundary conditions
*and* response are all symmetric; it cuts cost and removes rigid-body modes.

**Convergence and singularities.** Refine, re-run, note max von Mises and max
displacement, repeat until the change between runs is small — "usually below 5%". The
page then gives three curve shapes, which is the part that matters:

- displacement converges quickly;
- max stress at a notch such as a hole converges, but needs more refinement;
- **max stress at a sharp corner with a fixed boundary condition does not converge at
  all** — it grows indefinitely.

Four causes are named: concentrated forces on solids or shells, boundary conditions
applied to points, sharp corners, and contact at a corner. Four remedies: apply loads and
boundary conditions to small *areas* rather than points, add a small fillet to the sharp
corner (an explicit exception to the defeaturing rule), include plasticity so stress can
redistribute, or read stress away from the singularity under St. Venant.

### 4.2 FEM Tutorial Python

Intermediate, 0.18+, by Bernd, 30 minutes. Builds the cantilever of §4.3 entirely from
Python. Worth recording because it is a working reference implementation of the chain
M3.3 and M3.4 build by hand.

The shape of it:

```python
import ObjectsFem
analysis_object = ObjectsFem.makeAnalysis(doc, "Analysis")
solver_object   = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiX")
material_object = ObjectsFem.makeMaterialSolid(doc, "SolidMaterial")
fixed_constraint = ObjectsFem.makeConstraintFixed(doc, "FemConstraintFixed")
force_constraint = ObjectsFem.makeConstraintForce(doc, "FemConstraintForce")

from femmesh.gmshtools import GmshTools as gt
gmsh_mesh = gt(ObjectsFem.makeMeshGmsh(doc, "Box_Mesh"))
error = gmsh_mesh.create_mesh()

from femtools import ccxtools
fea = ccxtools.FemToolsCcx()
fea.update_objects(); fea.setup_working_dir(); fea.setup_ccx()
message = fea.check_prerequisites()
if not message:
    fea.purge_results(); fea.write_inp_file(); fea.ccx_run(); fea.load_results()
```

Three details carry over regardless of which CAD library we use:

- The material card is set as strings with units attached (`"210000 MPa"`,
  `"7900 kg/m^3"`), i.e. FreeCAD validates units at the boundary rather than inside.
  That is the same discipline as our SI-internal, convert-at-the-edge rule.
- The step-by-step path separates `write_inp_file` from `ccx_run` from `load_results`,
  with a `check_prerequisites` gate in front. Our L1 seam splits the same way.
- The page warns that on an `.inp` write error the returned path is empty *even when the
  file was written*, so the filename has to be set manually. A reminder that "the file
  exists" is not the same as "the write succeeded" — exactly what our errors-as-values
  rule exists for.

It also notes that Netgen scripting "has some limitations" while the Gmsh mesh object
"fully supports Python scripting", and that writing the input file headlessly is only
reachable through test mode — a live reminder that the GUI-free path is the awkward one
in FreeCAD, which is part of why D-04 went the other way.

### 4.3 FEM CalculiX Cantilever 3D

Beginner, 0.16+, by Bernd, 10 minutes. The example bundled with every FreeCAD
installation, used as the FEM workbench's own smoke test.

**The case, as published.** A box 8000 mm long, 1000 × 1000 mm in section.
Steel-Generic, E = 210 000 MPa, ν = 0.30, ρ = 7900 kg/m³. One face fixed. Force
9 × 10⁶ N applied to the opposite face in −z.

| Load | Published result |
| --- | --- |
| 9 MN transverse (−z) | z-displacement **−86.93 mm** |
| 500 MN axial (x, reversed into tension) | x-displacement **18.95 mm** |

**Checked against closed form.** Both cases have an elementary answer:

| Case | Closed form | Value | FreeCAD/CalculiX | Deviation |
| --- | --- | --- | --- | --- |
| Bending | δ = *FL*³/3*EI*, *I* = 8.333 × 10¹⁰ mm⁴ | 87.77 mm | 86.93 mm | −0.96 % |
| Axial | δ = *FL*/*AE* | 19.05 mm | 18.95 mm | −0.51 % |

The sign of the bending deviation is the interesting part. Timoshenko shear deformation
would *add* about 1.07 mm and push the FE answer **above** 87.77 mm, not below it. The FE
model comes out stiffer instead, which is what a fully clamped end face does: it restrains
Poisson contraction across the whole root section, which no beam formula models. At
*L*/*h* = 8 this box is also stubby enough that Euler–Bernoulli is itself the
approximation. Section 7 turns this into a change to M3.5.

---

## 5. The comprehensive table

Every tutorial on the wiki, as the index lists it. Kept whole so this page is a usable
index without a network round-trip. Blank cells are blank on the source page.

| Tutorial | Topic | Level | Time | Authors | Version |
| --- | --- | --- | --- | --- | --- |
| Add Button to FEM Toolbar | Finite Element Analysis | | | JohnWang | |
| Add FEM Constraint Tutorial | Finite Element Analysis | | | M42kus | |
| Add FEM Equation Tutorial | Finite Element Analysis | | | JohnWang | |
| Advanced Attachment OYX | Attachment | Intermediate/Advanced | | drmacro | 0.19 |
| Advanced TechDraw Tutorial (unfinished) | TechDraw | Advanced | | domad | 0.19 |
| Aeroplane | Part Workbench | Beginner | 0:10 | Hughthecat | |
| Analysis of reinforced concrete with FEM | Finite Element Analysis | Intermediate | 1:00 | HarryvL | 0.19+ |
| Arch panel tutorial | BIM Workbench | Beginner | 1:00 | Yorik | |
| Arch tutorial | BIM Workbench | Intermediate | | Yorik | 0.14 |
| Basic Attachment Tutorial | Attachment | Beginner/Intermediate | 1:00 | Bance | 0.17+ |
| Basic modeling tutorial | Modelling | Beginner | 0:15 | NormandC | Any |
| Basic Part Design Tutorial | Modeling | Beginner | | Quick61, HarryGeier | 0.17+ |
| Basic Part Design Tutorial 019 | Modeling | Beginner | 1:00 | Carlo Dormeletti, Ed Williams | 0.19+ |
| Basic Sketcher Tutorial | Sketcher | Beginner | 1:00 | Drei, Vocx | 0.19 |
| Basic TechDraw Tutorial | TechDraw | Beginner | | WandererFan | 0.17+ |
| BIM ingame tutorial | BIM Workbench | Beginner | | Yorik | |
| CAM Walkthrough for the Impatient | CAM Workbench | | | Chrisb | |
| Code snippets | Python | Beginner | | | |
| Configuration Tables | Product design | Beginner | 0:30 | Gbroques | 0.20+ |
| Creating a simple part with Draft and Part WB | Modeling | Beginner | 1:30 | Heda | |
| Creating a simple part with Part WB | Modeling | Beginner | 2:00 | Heda | |
| Creating a simple part with PartDesign | Modeling | Beginner | 1:00 | GlouGlou | 0.17+ |
| Customize Toolbars | Customization | Beginner | 0:05 | Mario52 | Any |
| Draft ShapeString tutorial | Product Design | Beginner | 0:30 | r-frank, vocx | 0.17+ |
| Draft tutorial | Draft Workbench | Beginner | 0:30 | Drei, vocx | 0.19 |
| Engine Block Tutorial | Part Workbench | Beginner | 1:00 | Andrewbuck40 | 0.14.3700 |
| Example Combined Footing | Reinforcement Workbench | Intermediate | | Shiv Charan | 0.20 |
| Example Slab Having LShape Rebars | Reinforcement Mesh | Intermediate | | Shiv Charan | 0.20 |
| Example Slab Having Mesh Of Straight Rebars | Reinforcement Workbench | Intermediate | | Shiv Charan | 0.20 |
| Example Slab Having UShape Rebars | Reinforcement Mesh | Intermediate | | Shiv Charan | 0.20 |
| Example Slab Spanning in One Direction | Reinforcement Workbench | Intermediate | | Shiv Charan | 0.20 |
| Example Slab Spanning in Two Directions | Reinforcement Workbench | Intermediate | | Shiv Charan | 0.20 |
| Export to STL or OBJ | Export | Beginner | 0:20 | r-frank | 0.16.6703 |
| Extend FEM Module | Finite Element Analysis | | | M42kus | |
| **FEM CalculiX Cantilever 3D** | Finite Element Analysis | Beginner | 0:10 | Bernd | 0.16.6377+ |
| FEM Example Capacitance Two Balls | Finite Element Analysis | Beginner | | Sudhanshu Dubey | 0.19 |
| **FEM Geometry Preparation and Meshing** | Finite Element Analysis | Beginner | | NewJoker | 0.21 |
| FEM Shear of a Composite Block | Finite Element Analysis | Beginner/Intermediate | 0:30 | HarryvL | 0.17.12960+ |
| FEM tutorial | Finite Element Analysis | Beginner | 0:10 | Drei | 0.17+ |
| **FEM Tutorial Python** | Finite Element Analysis | Intermediate | 0:30 | Bernd | 0.18.15985+ |
| FreeCAD-Ship s60 tutorial | Ship Workbench | Beginner | | | |
| FreeCAD-Ship s60 tutorial (II) | Ship Workbench | Beginner | | | |
| How to install additional workbenches | Programming | Medium | 0:15 | r-frank | Any |
| How to install macros | Programming | Medium | 0:15 | Mario52 | Any |
| Import from STL or OBJ | Import | Beginner | 0:30 | r-frank | 0.16.6703 |
| Import OpenSCAD code | Import | Beginner | 0:30 | r-frank | 0.16.6704 |
| Import text and geometry from Inkscape | Import | Beginner | 0:30 | r-frank | 0.16.6704 |
| Import/Export IFC — compiling IfcOpenShell | BIM Workbench | Advanced | 2:00 | Pablo Gil | |
| Measurement Of Angles On Holes | TechDraw | Beginner | 0:01 | AnHi | 0.19 |
| NativeIFC Tutorial | BIM Workbench | Intermediate/Advanced | 1:00 | Yorik | 1.0 |
| PartDesign Bearingholder Tutorial I | Product design | Beginner | 1:00 | NormandC | |
| PartDesign Bearingholder Tutorial II | Product design | Beginner | 1:00 | NormandC | |
| PartDesign tutorial | Sketcher | Beginner | 0:15 | Drei | 0.16+ |
| Plot Basic tutorial | Plot Workbench | Beginner | | | |
| Plot MultiAxes tutorial | Plot Workbench | Intermediate | | | |
| Post-Processing of FEM Results with Paraview | Finite Element Analysis | Intermediate | 2:00 | HarryvL | 0.19 |
| Private Preference Packs | Customization | Intermediate/Advanced | | drmacro | 1.0+ |
| Python scripting tutorial | Programming | Intermediate | | | |
| Raytracing tutorial | Raytracing Workbench | Beginner | 0:10 | Drei | 0.16+ |
| Robot 6-Axis | Robot Workbench | Intermediate | | | |
| Robot tutorial | Robot Workbench | Beginner | | r-frank | |
| Scripted Parts: Ball Bearing — Part 1 | Python | Beginner | 0:30 | r-frank | 0.16.6706 |
| Scripted Parts: Ball Bearing — Part 2 | Python | Beginner | 0:30 | r-frank | 0.16.6706 |
| Scripts | Python | Beginner | | onekk Carlo | 0.19 |
| Sketcher Lecture | Sketcher | | | | |
| Sketcher Micro Tutorial — Constraint Practices | Sketcher | Beginner | 0:30 | Quick61, vocx | 0.19 |
| Sketcher requirement for a sketch | Sketcher | Beginner | | Maker | |
| Sketcher Tutorial | Sketcher | Beginner | | Ulrich | |
| TechDraw HowTo Page | TechDraw | | | | 0.19 |
| TechDraw Pitch Circle Tutorial | TechDraw | Beginner | 0:10 | Andergrin | 0.19 |
| TechDraw TemplateGenerator | TechDraw | Intermediate | | FBXL5 | 0.19 |
| TechDraw TemplateHowTo | TechDraw | Intermediate | 1:00 | wandererfan | 0.17 |
| Thread for Screw Tutorial | Product design | Advanced | 1:00 | DeepSOIC, Murdic, vocx | 0.19 |
| Toothbrush Head Stand | Modeling | Beginner | 1:00 | EmmanuelG | 0.16+ |
| Topological data scripting | Programming | Intermediate | | | |
| Transient FEM analysis | Finite Element Analysis | | | | |
| Tutorial custom placing of windows and doors | BIM Workbench | Intermediate | 1:00 | Vocx | 0.18+ |
| Tutorial for open windows | BIM Workbench | Beginner | 1:00 | Vocx | 0.18+ |
| Tutorial FreeCAD POV ray | Raytracing Workbench | Intermediate | 2:00 | Vocx | 0.18+ |
| Tutorial KinematicAssembly | Assembly3 | Beginner | 0:30 | FBXL5 | 0.20+ |
| Tutorial KinematicController | Programming | Intermediate | 1:00 | FBXL5 | 0.20+ |
| Tutorial KinematicSkeleton | Assembly3 | Intermediate | 0:40 | FBXL5 | 0.20 |
| Tutorial Render with Blender | Rendering | Intermediate | 1:00 | Vocx | 0.18+ |
| VRML Preparation for Robot Simulation | Robot Workbench | Intermediate | | | 0.11.4252ppa1 |
| Whiffle Ball tutorial | Product design | Beginner | 0:30 | r-frank, vocx | 0.17+ |
| Wikihouse porting tutorial | Import | Intermediate/Advanced | 1:00 | | |

Bold rows are the three read in depth in section 4.

---

## 6. This project's reading

### 6.1 D-04 stands

Nothing here argues for putting FreeCAD back in the stack. The D-04 reasoning was about
installation — no reliable pip path on Windows, its own interpreter — and the tutorials
do not touch it. §4.2 mildly strengthens the decision: FreeCAD's headless `.inp` write is
reachable only through test mode, and the result-display calls in the same tutorial go
through `ViewObject`, i.e. through the GUI. A pipeline that must run unattended on a
clean machine is the wrong fit for a program whose scripting path assumes a running GUI.

What changes is only the *status* of these pages: from "tool we dropped" to "the domain
source for the parts of this project that are engineering rather than software".

### 6.2 Second-order meshing has a named failure mode we have not written down

D-03 fixes second-order tets, and §4.1 says plainly that second-order meshing can fail —
negative Jacobians — where geometry has small edges and tight curvature, because mid-side
nodes are snapped onto the surface.

This lands directly on `L_bracket`. `fillet_radius` is one of the four D-05 levers, it has
a declared minimum, and the singularity mutant is that minimum driven to zero. So the
agent's own edit vocabulary walks the geometry straight into the regime the page warns
about, and the failure appears at *mesh* time, not solve time. The risk register has
"second-order tets blow up DOF count"; it does not have "second-order meshing fails at
small fillet radii". Those are different failures with different mitigations.

The mitigation translates cleanly out of FreeCAD: FreeCAD's `Second Order Linear` is
Gmsh's straight-sided high-order meshing, and the relevant Gmsh levers are
`Mesh.HighOrderOptimize` and `Mesh.SecondOrderLinear`. Deciding this now costs an hour;
discovering it in M4 when the agent proposes a small fillet costs a day.

### 6.3 D-12's 20 % rule is corroborated, and could be sharper

§4.1's three convergence curves are exactly the discriminator D-12 needs, arrived at
independently:

| Curve | Behaviour under refinement | D-12 reading |
| --- | --- | --- |
| Displacement | converges quickly | not the metric to test with |
| Stress at a notch/hole | converges, slowly | should sit under the threshold |
| Stress at a sharp corner with fixed BC | **does not converge at all** | the mutant; should blow past it |

Two consequences. First, D-12's "more than 20 % at 0.5× characteristic length" is
defensible as a discriminator, because the two populations it separates are *convergent*
and *divergent*, not two similar numbers. Second, the page names two singularity sources
the project creates for itself and the plan currently treats asymmetrically: loads applied
at points or edges, **and boundary conditions applied at points or corners**. M2.2 already
freezes one support face and one load face, which is the right call for the load. The
support deserves the same explicit note — a fully fixed face meeting a sharp corner is the
page's own example of the curve that never converges, and it would read as a real
singularity, not a mutant.

One calibration note: M3.6 uses the V2 stepped bar's refinement behaviour to set the 20 %
threshold. The page's advice — plot the result against mesh density and look for the knee
— argues for recording three or four refinement levels there, not the two points the 0.5×
protocol itself uses. Same solve budget, a curve instead of a slope.

### 6.4 V1 now has a published cross-check, and an argument for a slenderer bar

§4.3 gives a third-party FE answer for a tip-loaded cantilever with every input published,
and it agrees with closed form to about 1 %. That is a free extra data point for M3.5: if
our pipeline reproduces −86.93 mm on that geometry it has validated the material card,
units, constraints, element formulation and extraction chain against someone else's
CalculiX run as well as against a formula.

The more useful finding is the direction of the error. Shear deformation would push the FE
deflection *above* the Euler–Bernoulli value by about 1.07 mm; the published result is
0.84 mm *below* it. The clamped end face is stiffer than a beam-theory built-in end,
because it restrains Poisson contraction across the whole root section. So the comparison
has a known systematic offset, and at *L*/*h* = 8 it is not small.

M3.5's exit criterion is "agrees with closed form within tolerance". A symmetric tolerance
around the formula hides this. Either state the acceptance as a signed band, or — better,
and cheaper — make V1's bar slender enough (*L*/*h* ≥ 20) that Euler–Bernoulli is the
accurate model and the end-effect offset drops below the noise. This is a task-level
change to M3.5, not a milestone change, and it must land before 21 Sep.

### 6.5 Two levers on the D-13 budget that the risk register does not name

The risk register's mitigation for "iteration too slow" is "shrink the part or coarsen the
base mesh before cutting iterations". §4.1 supplies two better first moves:

- **Planar symmetry.** `L_bracket` — a plate bent through 90° with a fillet — is
  symmetric about its mid-width plane, the one whose normal runs along the bend axis,
  provided the lightening hole stays centred on it. If the frozen load case is symmetric
  about that plane too, a half model is valid: a factor of two on every solve in the run,
  for the cost of one boundary condition, and it does not touch mesh density, which D-21
  puts out of reach anyway. It constrains M2.1 and M2.2's frozen records, so it has to be
  decided while they are still open.
- **Minimum element size.** The page's specific advice is to set a minimum element size
  as well as a maximum, to stop the mesher generating unnecessarily dense meshes around
  small features. With `fillet_radius` as an agent-controllable parameter, small features
  are guaranteed to appear. Without a floor, a small-fillet candidate can silently cost
  far more than the budget assumed.

Coarsening the base mesh should stay the *last* lever, not the first: it degrades exactly
the stress field the vision step has to read.

### 6.6 M5.10's SKILL.md has a source now

M5.10 writes the FEA-reasoning `SKILL.md` — instruction for how to approach the work,
never what is permitted. §4.1 is close to a ready-made checklist for it: what element
order means, why a coarse mesh lies, the four causes of a singularity, how to tell a
singularity from a real concentration, and why displacement converges when stress does
not. Writing that skill from a cited source beats writing it from memory, and it is the
distinction the agent has to make on every contour it reads.

### 6.7 An `.inp` writer reference for M3.3

M3.3 (the CalculiX `.inp` writer) is tied for the longest estimate in M3 at 4–6 h, and it
is the task where an undetected mistake is most expensive, because everything downstream
inherits it. FreeCAD's `femtools`/`ccxtools` module writes CalculiX decks from a Gmsh mesh
and is readable on GitHub without installing anything. Reading it as a reference for card
ordering, set definitions and material-card syntax is free and does not create a
dependency. §4.2's warning — that a failed `.inp` write can return an empty path even
though the file exists — is the kind of detail that costs an afternoon to rediscover.

---

## 7. What this changes

Nothing at milestone level. The six milestones, their exit criteria, the three hard
orderings and the 12 Sep – 3 Oct window are unaffected; this is a documentation source,
not a new capability or a new dependency. The changes are inside existing tasks.

| # | Change | Where | Urgency |
| --- | --- | --- | --- |
| 1 | Add a risk: *second-order meshing fails at small fillet radii (negative Jacobians)*. Mitigation: straight-sided high-order meshing (`Mesh.SecondOrderLinear` / `HighOrderOptimize`), decided before M4 | Risk register | Before M4 (22 Sep) |
| 2 | Hand-mesh `L_bracket` at `fillet_radius` **minimum**, not only nominal, and keep the mesh | M2.3 / M2.4 (#45, #47) | In flight now |
| 3 | Record in the frozen load record that the **support** face is a singularity source too, and how the fixed face meets the fillet | M2.2 (#46) | In flight now |
| 4 | Make V1's bar slender (*L*/*h* ≥ 20), or state the acceptance as a signed band; note the clamped-face stiffening | M3.5 (#15) | Before 21 Sep |
| 5 | Add the FreeCAD bundled cantilever (−86.93 mm, inputs in §4.3) as a second published reference for V1 | M3.5 (#15) | Before 21 Sep |
| 6 | Record 3–4 refinement levels for the V2 Kt case, not 2, so the D-12 threshold sits on a curve | M3.6 (#16) | Before 22 Sep |
| 7 | Add planar symmetry and a minimum element size to the "iteration too slow" mitigations, ahead of coarsening the base mesh | Risk register / M3.8 (#18) | Before 22 Sep |
| 8 | Cite §4.1 as the source for the singularity and mesh-quality content of the skill | M5.10 (#36) | Before 30 Sep |
| 9 | Read FreeCAD's `femtools`/`ccxtools` `.inp` writer as a reference before writing ours | M3.3 (#13) | Before 20 Sep |

None of these adds a task to the board. Items 2, 3, 4, 6 and 9 are acceptance-criteria
edits on existing issues; items 1 and 7 are risk-register rows in this repo; items 5 and 8
are references added to existing task descriptions.

**What it does not change.** D-03 (second-order tets) — the page endorses them. D-04
(CadQuery over FreeCAD) — reinforced, if anything. D-11 (geometric FDM check over a
slicer) — the CNC cluster describes the slicer route we priced and rejected. D-13's budget
numbers — unchanged until M3.8 measures them. The open question about a GE-bracket-derived
parametric part is untouched; nothing here bears on it.

---

## 8. Revision log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-17 | First pass. Index captured, three FEM pages read in depth, nine task-level changes proposed |

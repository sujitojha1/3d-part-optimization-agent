# Reference — FEM Workbench

| Attribute | Value |
| --- | --- |
| Source | [FreeCAD wiki — FEM Workbench](https://wiki.freecad.org/FEM_Workbench) |
| Publisher | The FreeCAD project wiki, CC-BY 3.0 |
| Kind | Workbench hub page — the tool catalogue for FreeCAD's FEA workbench, plus its onward links |
| Version markers | The page tags tools *introduced in 1.0*, *1.1* and *26.3*; those tags are carried through below as written |
| Accessed | 2026-09-17 |
| Status | Reference input. Since requirements v0.5, FreeCAD **is** the project's CAD and FEM front end ([D-04](requirements.md)); §9.6 ("D-04, again") is historical |
| Related | [FEM geometry preparation](fem-geometry-preparation.md) · [FreeCAD tutorials index](freecad-tutorials.md) · [Requirements](requirements.md) · [Plan](plan.md) · [Solution architecture](solution-architecture.md) |

Sections 1–8 record what the source page says, following its own menu structure. Section 9
is this project's reading and is our interpretation, not FreeCAD's.

Three small departures from the source's own headings, for readability: §5.1's *Filters*
heading is ours (on the page that list sits directly under *Menu: Results*); §6 merges the
page's *Menu: Utilities*, *Context Menu* and *Preferences*; and §8 merges its *Information*,
*Tutorials* and the two *Extending* sections. Nothing is dropped.

**Why this page is worth capturing.** It is a catalogue rather than a tutorial, and most of
it is GUI inventory we will never touch. Its value is narrower and specific: several
entries name **the CalculiX capability underneath them**, and two of those are cards this
project's M3.9 needs and currently has no reference for. Reading the catalogue is the
cheapest way to find out which parts of CalculiX someone has already wrapped, and — just as
useful — which parts nobody has.

---

## 1. What it is, and the workflow it assumes

The FEM Workbench is described as providing a modern FEA workflow for FreeCAD, which
mainly means gathering every tool needed for an analysis into one GUI.

The steps it lists — three phases, seven steps, five of them preprocessing:

**Preprocessing**

1. Model the geometry in FreeCAD, or import it from another application.
2. Create an analysis.
3. Add analysis features — boundary conditions, loads, constraints — to the geometric model.
4. Add materials to the parts of the model.
5. Create a finite element mesh for the model, or import one.

**Solving**

6. Run an external solver from within FreeCAD.

**Postprocessing**

7. Visualise results within FreeCAD, or export them for postprocessing elsewhere.

The workbench runs on Linux, Windows and macOS, but — the page's own caveat — because it
uses external solvers, **the amount of manual setup depends on the operating system**.
[FEM Install](https://wiki.freecad.org/FEM_Install) covers that setup.

The page's own diagram summary: the workbench calls two external programs, one to mesh a
shape and one to solve the finite element problem.

---

## 2. Menu: Model

**New Analysis** creates a container for a mechanical analysis.

### 2.1 Materials

| Tool | Purpose |
| --- | --- |
| Solid Material | Select a solid material from the database |
| Fluid Material | Select a fluid material from the database |
| Non-Linear Mechanical Material | Add a nonlinear mechanical material model |
| Reinforced Material (Concrete) | Select a matrix-plus-reinforcement material from the database |
| Material Editor | Edit materials |

### 2.2 Element geometry

| Tool | Purpose |
| --- | --- |
| Beam Cross Section | Define cross sections for beam elements |
| Beam Rotation | Rotate beam cross sections |
| Shell Plate Thickness | Define shell element thickness |
| Fluid Section for 1D Flow | Fluid section element for pneumatic and hydraulic networks |

### 2.3 Electromagnetic boundary conditions

Electromagnetic Boundary Condition (electrostatic potential, or *26.3:* magnetic flux
density); Current Density Boundary Condition; Magnetization Boundary Condition; *1.1:*
Electric Charge Density.

### 2.4 Fluid boundary conditions

Initial Flow Velocity Condition and Initial Pressure Condition, both for a body (volume);
Flow Velocity Boundary Condition, at an edge in 2D or a face in 3D.

### 2.5 Geometrical analysis features

| Tool | Purpose |
| --- | --- |
| Plane Multi-Point Constraint | Keep the nodes on a planar surface in the same plane |
| Section Print Feature | Print predefined facial output variables — **forces and moments** — to the data file |
| Local Coordinate System | Define a local coordinate system for a face |

### 2.6 Mechanical boundary conditions and loads

| Tool | Purpose |
| --- | --- |
| Fixed Boundary Condition | Fix point(s), edge(s) or face(s) |
| Rigid Body Constraint *(1.0)* | Apply **CalculiX's rigid body constraint** — the nodes of a selected geometric entity are constrained to the motion of a user-positioned reference point |
| Displacement Boundary Condition | Prescribe displacement on point/edge/face(s) |
| Contact Constraint | Contact between two faces |
| Tie Constraint | Tie ("bonded contact") between two faces, or *(1.0)* cyclic symmetry |
| Spring Boundary Condition | A spring boundary condition |
| Force Load | A force in newtons applied uniformly to the selected entity in a given direction |
| Pressure Load | A pressure load |
| Centrifugal Load | A centrifugal body load |
| Gravity Load | Gravity acceleration acting on the model |

### 2.7 Thermal boundary conditions and loads

Initial Temperature (for a body); Heat Flux Load (on face(s)); Temperature Boundary
Condition (on point/edge/face(s)); Body Heat Source (internally generated body heat).

### 2.8 Overwrite constants

Constant Vacuum Permittivity — overwrite the permittivity of vacuum with a custom value.

---

## 3. Menu: Mesh

| Tool | Purpose |
| --- | --- |
| Mesh From Shape by Netgen | Generate an FE mesh with Netgen |
| Mesh From Shape by Gmsh | Generate an FE mesh with Gmsh |
| Mesh Refinement | Create localised area(s) to mesh, which "highly optimizes analysis time" |
| Mesh Group | Group and label mesh elements (vertex, edge, surface) together — **"useful for exporting the mesh to external solvers"** |
| Erase Elements *(1.0)* | Hide elements selected by a polygon |
| FEM Mesh to Mesh | Convert surfaces of 3D elements, or whole 2D elements, to a surface mesh |

### 3.1 Gmsh refinements

Almost all new in 26.3:

| Tool | Purpose |
| --- | --- |
| Distance-Based Refinement *(26.3)* | Set mesh size from the distance to vertices, edges and faces |
| 2D Boundary Layer | Anisotropic meshes for accurate calculation near boundaries |
| Shape-Based Refinement *(26.3)* | Set mesh size inside and outside a box, sphere or cylinder |
| Manipulate Refinement *(26.3)* | Manipulate a refinement's output in various ways |
| Advanced Refinement Types *(26.3)* | Define mesh size by various advanced means |
| Structured Transfinite Curve *(26.3)* | A fixed number of nodes on an edge, structured |
| Structured Transfinite Surface *(26.3)* | A structured mesh on a face |
| Structured Transfinite Volume *(26.3)* | A structured mesh in a 4- or 5-sided volume bounded by transfinite surfaces |

---

## 4. Menu: Solve

### 4.1 Solvers

Four: **CalculiX**, **Elmer**, **Mystran**, **Z88**. Each entry creates a solver
controller for the analysis.

### 4.2 Equations

All of these are Elmer equations — the page says so on every line.

*Mechanical:* Elasticity Equation (linear mechanical), Deformation Equation (nonlinear,
deformations).

*Electromagnetic and other:* Electrostatic; Electricforce (electric force on surfaces);
Magnetodynamic; Magnetodynamic 2D; *1.1:* Static Current; Flow; Flux; Heat.

### 4.3 Running

**Solver Job Control** opens the menu to adjust and start the selected solver; **Run
Solver** runs the selected solver of the active analysis.

---

## 5. Menu: Results

**Purge Results** deletes the active analysis's results. **Show Result** displays a
result — and the page notes it is *not* available for Elmer, which visualises only through
the post pipeline. **Apply Changes to Pipeline** toggles whether pipeline and filter
changes apply immediately. **Post Pipeline From Result** adds a graphical representation
of the results, with a colour scale and further display options. *1.1:* **Pipeline
Branch** branches the results pipeline.

### 5.1 Filters

| Filter | Purpose |
| --- | --- |
| Warp | Visualise the scaled deformed shape |
| Scalar Clip | Clip a field at a scalar value |
| Function Cut | Show results on a plane, sphere, cylinder or box cutting the model |
| Region Clip | Clip a field with a plane, sphere, cylinder or box |
| Contours | Iso-lines (2D) or iso-contours |
| Glyph *(1.1)* | Glyph (symbol) plots |
| Line Clip | Plot a field's values along a specified line |
| Stress Linearization Plot | Create a stress linearization plot |
| Data at Point Clip | Show a field's value at a given point |
| Calculator *(1.1)* | Custom fields from expressions over existing fields |

### 5.2 Filter functions

Plane, Sphere, Cylinder, Box — each cuts the result mesh with that shape.

### 5.3 Data visualisations

*All 1.1:* Create Lineplot, Create Histogram, Create Table — each for a selected pipeline
or filter.

---

## 6. Utilities and the context menu

**Utilities:** Clipping Plane on Face; Remove All Clipping Planes; FEM Examples (opens a
GUI for the bundled examples).

**Context menu:** Clear FEM Mesh (deletes the mesh from the FreeCAD file to make it
lighter); *26.3:* Clear Mesh Groups (deletes groups without the mesh, to shrink exports);
Display Mesh Info (basic statistics — node count and element count by type).

**Preferences** for FEM tools have their own page.

---

## 7. Obsolete tools

All removed in 1.0 and above. The stated reasons are worth keeping, because they are the
same two reasons features die anywhere:

| Tool | Why it went |
| --- | --- |
| Fluid boundary condition | **Did not have a solver** |
| Constraint bearing | Did not have a solver |
| Constraint gear | Did not have a solver |
| Constraint pulley | Did not have a solver |
| Solver CalculiX (new framework) | Same as the original with extra checks; **tool was unfinished** |
| Nodes set | Create a node set from an FEM mesh; unfinished and unusable |

Four constraints existed in the GUI with nothing behind them to consume what they
declared. That is the shape of a feature that was specified but never wired to the thing
that would have made it real.

---

## 8. Where the page points next

**Information pages.** [FEM Install](https://wiki.freecad.org/FEM_Install) (setting up the
external programs), [FEM Geometry Preparation and
Meshing](https://wiki.freecad.org/FEM_Geometry_Preparation_and_Meshing) — captured in
[fem-geometry-preparation.md](fem-geometry-preparation.md) —
[FEM Mesh](https://wiki.freecad.org/FEM_Mesh),
[FEM Solver](https://wiki.freecad.org/FEM_Solver) (the solvers available and those that
could be used in future), [FEM CalculiX](https://wiki.freecad.org/FEM_CalculiX) (the
default structural solver), and [FEM Concrete](https://wiki.freecad.org/FEM_Concrete).

**Tutorials,** numbered 1–7 on the page: FEM CalculiX Cantilever 3D; FEM Tutorial; FEM
Tutorial Python; FEM Shear of a Composite Block; Transient FEM analysis; Post-Processing of
FEM Results with Paraview; FEM Example Capacitance Two Balls. Plus coupled
thermal-mechanical tutorials by openSIM and several video series. All of these are indexed
in [freecad-tutorials.md](freecad-tutorials.md).

**Extending the workbench.** Aimed at power users and developers, expecting C++ and Python
and some knowledge of FreeCAD's document object system: Extend FEM Module, Onboarding FEM
Devs, Add FEM Constraint Tutorial, Add FEM Equation Tutorial, and the community-maintained
FreeCAD Mod Dev Guide. The page states the workbench's own objective — to find ways to
interact easily with various FEM solvers, so a user can create, mesh, simulate and optimise
a design entirely within FreeCAD — and warns that some articles may be obsolete because
FreeCAD is under active development.

---

## 9. This project's reading

### 9.1 Two CalculiX cards M3.9 needs, one of which has a wrapper here

[M3.9](plan.md) — the SimJEB design 148 cross-check — specifies modelling each bolt hole as
a `*RIGID BODY` fixed at the hole centre and the pin bore as a `*DISTRIBUTING COUPLING`,
then checking that reaction forces sum to the applied load before comparing displacement.
Three of those four things appear in this catalogue, and the gap is informative:

| M3.9 needs | In this catalogue |
| --- | --- |
| `*RIGID BODY` | **Yes** — §2.6 Rigid Body Constraint (1.0), described as CalculiX's own rigid body constraint with a user-positioned reference point |
| Reaction forces summed against the applied load | **Yes** — §2.5 Section Print Feature, which prints facial forces and moments to the data file. That is CalculiX's `*SECTION PRINT`, and it is exactly the check M3.9 describes |
| `*DISTRIBUTING COUPLING` | **No tool listed.** Nothing in §2.5 or §2.6 corresponds to it |
| Nodal displacement comparison | **Yes** — §5.1 Data at Point Clip, and Line Clip for a path |

Two consequences. First, **`*SECTION PRINT` is the named mechanism for M3.9's reaction
check**, rather than summing reactions by hand from the `.frd` — worth knowing before that
task is written. Second, the pin-bore half of M3.9's coupling model has **no reference
implementation anywhere in FreeCAD's FEM workbench**, so the one part of V3 that cannot be
cribbed is the one the plan treats as symmetric with the other. M3.9 is estimated at 4–6 h
and is already on the cut list at position 3; this is the argument for why that estimate is
the soft one.

### 9.2 Mesh Group is the FreeCAD analogue of our label chain

§3's Mesh Group groups and labels mesh elements, and the page gives its purpose as
**exporting the mesh to external solvers** — which is to say, groups become solver element
sets. That is precisely the mechanism [D-06](requirements.md) depends on and that
[M2.4](plan.md) verifies by reading the generated `.inp`. It is mild corroboration that the
chain CadQuery tags → Gmsh physical groups → `.inp` element sets is the ordinary way to do
this and not an invention of ours.

§6's Display Mesh Info — node count and element count by type — is the trivial sanity check
worth having in our own parse step. An element count that changes when only a material
changed means something is wrong upstream.

### 9.3 The 26.3 Gmsh refinement tools are Gmsh fields, and we can use them directly

[D-03](requirements.md) specifies one task-declared characteristic length with a local
refinement factor at named regions. §3.1's Distance-Based Refinement (mesh size from
distance to vertices, edges and faces) and Shape-Based Refinement (size inside and outside a
box, sphere or cylinder) are wrappers over Gmsh's own `Field` mechanism, which we reach
directly through the Gmsh Python API without any of this GUI.

Distance-based sizing is a better fit for D-03 than a flat factor on a named region: the
element size grades away from the fillet instead of stepping at a region boundary, which is
what the [geometry page](fem-geometry-preparation.md) §10.1 recommends anyway. It also
interacts with [D-12](requirements.md)'s 0.5× local re-solve, since "0.5× characteristic
length in the affected region" has to mean something precise in whichever mechanism we
choose. Worth settling in M3.2 rather than discovering in M5.3.

### 9.4 The results filters are VTK filters we already have

Our renderer is PyVista on VTK ([plan.md](plan.md), verified stack), and §5.1's list —
warp, clip, cut, contour, glyph, calculator — is the VTK filter set. Nothing to adopt, but
two entries are worth remembering:

- **Line Clip** and **Stress Linearization Plot** plot a field along a line. That is the
  mechanical form of the [geometry page](fem-geometry-preparation.md) §13 remedy of reading
  stress *away* from a singularity under St. Venant, and it is the obvious fallback if
  D-12's re-solve test is ever inconclusive.
- **Data at Point** is the V3 comparison primitive.

### 9.5 A contradiction between two wiki pages, recorded not resolved

[fem-geometry-preparation.md §6.2](fem-geometry-preparation.md) records the geometry page's
statement that flexible supports such as springs are **not** available in FreeCAD's FEM
workbench when using CalculiX, and that Elmer has a spring constraint. This page lists a
**Spring Boundary Condition** in §2.6 under mechanical boundary conditions and loads, with
no solver qualifier.

The two pages disagree, or one of them is out of date, and nothing here settles which.
Recorded because it matters as a caution rather than as a fact: neither wiki page is
authoritative about what a solver can do, and anything load-bearing we take from them
should be checked against CalculiX's own documentation. It has no bearing on our work —
[D-08](requirements.md) gives one load case per task and our support is a fixed face.

### 9.6 D-04, again

The page states that because the workbench uses external solvers, manual setup depends on
the operating system, and it points at a whole page for that setup. Four solvers, a
separate mesher, and an install guide per OS is the same packaging problem
[D-04](requirements.md) and [D-17](requirements.md) solved by dropping FreeCAD and pinning
CalculiX by URL and SHA. Nothing to change.

### 9.7 What does not apply

Everything Elmer (§4.2 in full), everything thermal, electromagnetic and fluid (§2.3, §2.4,
§2.7, §2.8), Mystran and Z88, the concrete and reinforcement materials, beam and shell
element geometry (§2.2 — see [fem-geometry-preparation.md §2](fem-geometry-preparation.md)
for why we cannot use those element types), contact and tie constraints (one solid,
[D-08](requirements.md)), the clipping-plane utilities, and §8's developer material.

§7's obsolete tools apply to nobody, but they are a good reminder of what a declared
capability with nothing behind it looks like — the project's own equivalent would be a
verifier that reads a field the pipeline never populates.

### 9.8 Two additions to the change list

[freecad-tutorials.md §7](freecad-tutorials.md) holds this project's running list of
task-level changes argued for by the FreeCAD documentation. This page adds two, both
recorded here rather than folded into that table, because that table belongs to the page it
sits on:

| # | Change | Where |
| --- | --- | --- |
| 10 | Use CalculiX `*SECTION PRINT` for M3.9's reaction-force check rather than summing from the `.frd`; note that `*DISTRIBUTING COUPLING` has no reference implementation, so that half of the coupling model is the unestimated part | M3.9 ([#57](https://github.com/sujitojha1/3d-part-optimization-agent/issues/57)) |
| 11 | Decide whether local refinement is a distance field or a flat factor on a region, and make D-12's "0.5× characteristic length in the affected region" mean something precise in whichever is chosen | M3.2 ([#12](https://github.com/sujitojha1/3d-part-optimization-agent/issues/12)), consumed by M5.3 ([#29](https://github.com/sujitojha1/3d-part-optimization-agent/issues/29)) |

Neither adds a board item. Both are acceptance-criteria edits on existing issues.

---

## 10. Revision log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-17 | First pass. Catalogue captured by menu; §9 maps it onto the project and adds changes 10 and 11 |

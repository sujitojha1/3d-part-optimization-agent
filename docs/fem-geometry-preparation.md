# Reference — FEM Geometry Preparation and Meshing

| Attribute | Value |
| --- | --- |
| Source | [FreeCAD wiki — FEM Geometry Preparation and Meshing](https://wiki.freecad.org/FEM_Geometry_Preparation_and_Meshing) |
| Author | NewJoker, on the FreeCAD project wiki. CC-BY 3.0 |
| Stated level | Beginner. Topic: Finite Element Analysis. Time to complete: N/A |
| FreeCAD version | Its infobox says 1.0 or above; the [tutorial index](https://wiki.freecad.org/Tutorials) says 0.21. Features marked *1.1* below are flagged as such on the source page |
| Accessed | 2026-09-17 |
| Status | Reference input. FreeCAD is not in this project's stack ([D-04](requirements.md)); this page is a domain source, not a dependency |
| Related | [FreeCAD tutorials index](freecad-tutorials.md) — §4.1 is the short version of this page · [Requirements](requirements.md) · [Plan](plan.md) · [Solution architecture](solution-architecture.md) |

Sections 1–13 record what the source page says, following its own outline — with one
departure, noted at §9. Section 14 is this project's reading and is our interpretation,
not FreeCAD's.

**How to read it.** The page is written for people driving FreeCAD's GUI, so a good part
of it is tool-specific: which button partitions a face, which boolean makes an assembly
meshable. That part is recorded because the *reason* behind each instruction usually
survives the change of tool — we reach the same ends through CadQuery and Gmsh's Python
API. Where an instruction is purely FreeCAD mechanics with no analogue for us, it is
marked **[FreeCAD-only]** and kept short.

The plan and milestone consequences are not repeated here. They are in
[freecad-tutorials.md §6–7](freecad-tutorials.md).

---

## 1. Background

The page opens on the point everything else rests on. Software that puts a simulation
environment next to a CAD environment makes it tempting to analyse a new design
immediately, but FEM is an advanced method and needs properly prepared geometry and mesh
to produce reasonable, accurate results. The page invokes *garbage in, garbage out* by
name and says it applies here particularly.

It also scopes itself: material properties and boundary conditions are equally decisive
for accuracy, but geometry preparation and meshing come first and are among the most
common sources of trouble, so those are what it covers.

---

## 2. Types of geometry, and choosing one

Three kinds of geometry feed FEM in FreeCAD:

| Geometry | Element family |
| --- | --- |
| Lines / wires | Beam elements |
| Surfaces | Shell and 2D elements (plane stress, plane strain, axisymmetric) |
| Solids | Solid elements |

Most designs are solids, but the page says it is often highly recommended to use wires or
surfaces instead where the structure allows it.

An important caveat on CalculiX specifically: its beam, shell and 2D elements are not true
elements of those kinds in the textbook sense — they are internally expanded to solids.
The page still recommends using them in the cases below.

### 2.1 Beam models

For a part that is slender and beam-like with a regular supported cross-section
(rectangular, box, elliptical, circular, pipe). The working rule offered is that
cross-section dimensions should be under about 1/10 of the part's length for the beam
assumption to hold — with the caveat that there is no single rule, and that particular
loading, response or unavoidable geometric detail can invalidate it.

The workflow is to draw a centreline and apply a beam section with an optional rotation.
Extracting a centreline from existing solid geometry is done with Draft Wire or Draft
BSpline using snaps, with lines as supports.

*1.1:* very slender beams may have negligible bending stiffness, in which case truss
elements apply. These carry axial force only, no moments. They are enabled by the
CalculiX solver's **Exclude Bending Stiffness** property, and the cross-section then comes
from the FEM ElementGeometry1D object's **Truss Area** property rather than a profile.

### 2.2 Shell models

For thin-walled parts such as sheet metal. The page calls this very important and often
overlooked. The reason is cost: to get proper accuracy with solid elements, especially
under bending, you need at least three to five elements through the thickness, and on a
thin-walled part that produces very large meshes — more so because FreeCAD cannot generate
hexahedra, so the thickness has to be filled with tetrahedra.

The geometry needed is a midsurface with a thickness applied. Extracting one from a solid
is done with PartDesign SubShapeBinder or Draft Facebinder, then Part Offset, then
SubShapeBinder and Extrude to extend the midsurface edges and close the gaps between them.
If an offset is used, the top or bottom surface can stand in for the midsurface, which may
also help avoid material overlap. **[FreeCAD-only]**

The usual applicability rule is thickness under about 1/10 of a typical global dimension.

*1.1:* very thin shells with negligible bending stiffness can use membrane elements, again
through **Exclude Bending Stiffness**.

### 2.3 Planar models

Set through the CalculiX solver's **Model Space** property. All three require the surface
to lie on the XY plane.

| Mode | For | Notes |
| --- | --- | --- |
| Plane stress | Thin parts reducible to the extrusion profile; loaded and deforming in-plane, zero out-of-plane stress | Two DOF (X, Y translation). "Quite common" — e.g. a thin plate in tension |
| Plane strain | Thick parts reducible to the extrusion profile; loaded and deforming in-plane, zero out-of-plane strain | Two DOF. "Not so common" — e.g. a long dam, wall or pipe under uniform pressure along its length |
| Axisymmetric | Parts reducible to a profile of revolution, loaded uniformly around the circumference | Two DOF (radial, axial). Profile must lie right of the Y axis, which is the revolution axis. "Very common" — pressure vessels, rubber mounts, bushings, gaskets, flanges, even bolted joints treating the thread as axisymmetric |

Thickness is defined as for shells in the two plane cases and is irrelevant for the
axisymmetric case.

---

## 3. Geometry validity

Geometry used for FEM has to be valid, and above all free of intersections. Intersections
are described as a common issue when assemblies are modelled without proper constraints
between parts.

- Part SectionCut helps find interferences between parts.
- Part Fuse resolves them where they are intentional.
- Part CheckGeometry catches other problems — non-manifold geometry, redundant edges or
  faces — but the page stresses that visual checks matter too.
- When it is unclear whether something is really a solid or just a closed shell, Part
  SectionCut and the **Shape Content** tab of Part CheckGeometry answer it.

All of this has to be fixed before meshing.

---

## 4. Surface normals

Relevant only for surface geometries used with shell and 2D elements. Normals distinguish
the positive from the negative side of a shell mesh, which affects pressure loads and
contact. For 2D analyses (plane stress/strain, axisymmetric), CalculiX **requires** normals
to point in the positive Z direction; inverted normals produce negative Jacobian errors.

Three ways to check them:

1. Enable Backlight in Preferences and set the surface object's **Lighting** property to
   *One side* — the negative side then appears darker.
2. Use the Normal Vector macro.
3. Mesh the surface in FEM — the mesh is coloured only on the positive side.

Inverting them is done with the Reverse shapes tool. **[FreeCAD-only]**

---

## 5. Surface meshes are not FEM geometry

Surface meshes imported from STL, OBJ and similar, or built in the Mesh Workbench, cannot
be used for FEM directly. A shape has to be created from the mesh first; that shape can
then be meshed into a shell or 2D FE mesh, and for a solid FE mesh the shape creation has
to be followed by conversion to a solid.

The page then explains why this route is a bad idea rather than merely a longer one: every
triangle of the surface mesh becomes a face of the generated shape, which makes assigning
loads and boundary conditions particularly problematic. Refinement after conversion to a
solid may remove redundant triangular faces on planar surfaces, but in practice most
remain. The recommendation is therefore to use CAD geometry — created in FreeCAD or
imported from STEP/IGES — instead, and that it sometimes makes sense to recreate the
geometry from the surface mesh rather than convert it.

---

## 6. Geometry simplification

### 6.1 Defeaturing

Designs prepared in CAD are typically too detailed for FEM. The page calls this step often
overlooked and very important: excessive detail makes a good mesh hard to obtain, and a
mesh that is eventually obtained may be so dense that solving times become unreasonable.
The rule offered is to leave only the features that significantly affect strength or
stiffness.

Typically omitted: small fillets and chamfers, small holes, other small details, welds,
bolts and threads, and decorative elements such as logos and engravings.

Part Defeaturing and the add-on Defeaturing Workbench help. The page illustrates this with
a bracket before and after defeaturing.

### 6.2 Replacing parts with boundary conditions

In assemblies, parts can often be dropped from the model and replaced by boundary
conditions on the parts they were attached to. This is valid when the excluded part is
significantly stiffer than the analysed part — stiffer structurally, so geometry as well
as material.

The caveat given is that fixed boundary conditions introduce rigidity, as if the part were
attached to something infinitely stiff, and that flexible supports such as springs are not
available in FreeCAD's FEM workbench with CalculiX. Elmer has a spring constraint.

### 6.3 Planar symmetry

Cutting the model at a symmetry plane is valid only when **all four** of these are
symmetric about it:

- geometry
- loads
- boundary conditions
- response

The response condition carries a warning of its own: frequency and buckling analyses using
symmetry will not find antisymmetric mode shapes.

Using 1/2, 1/4 or 1/8 of the model is recommended whenever possible, because it greatly
reduces computational cost and because it eliminates some rigid body motions, which makes
the part easier to constrain.

The symmetry boundary condition goes on the faces in the cut plane:

| Element type | Blocked |
| --- | --- |
| Solid | Translation normal to the symmetry plane |
| Shell and beam | Translation normal to the plane, plus rotations other than about the axis normal to the plane |

If the symmetry plane cuts through a region carrying an applied force, the force must be
reduced accordingly. This does not apply to pressure loads.

### 6.4 Cyclic symmetry

Less common, and defined through the tie constraint. It allows a single representative
sector of a structure built from a circular pattern to be analysed, assuming the loads and
boundary conditions share that symmetry. Tangential loads can be applied, so torsion can be
simulated, though centrifugal loading is the common use. Named applications: rotors,
shafts, turbines, fans, flywheels.

---

## 7. Geometry partitioning

### 7.1 What it is for

Partitioning divides geometry into smaller segments. The page notes that elsewhere it is
mainly a route to hex meshing, but that in FreeCAD it earns its place for four other
reasons:

1. creating subregions for analysis feature assignment
2. splitting a part into sections of different materials
3. creating regions for mesh refinement
4. controlling the mesher by forcing it to follow additional edges — called out as
   particularly useful for controlling Gmsh's mesh growth

### 7.2 Faces of solids, with sketches

The main application: applying a load or boundary condition to only part of a face. Draw a
sketch with the right contour on that face and split the face with it using Part Boolean
Fragments.

### 7.3 Volumes of solids, with datum planes

For applying several materials to one part without splitting it into several parts. Use a
datum plane with Part Boolean Fragments in **Compsolid** mode.

### 7.4 Surface geometries, with sketches

Boolean Fragments is the obvious route, but the page warns it may misbehave when mesh
group creation is enabled in the FEM preferences. The recommended alternative builds the
geometry from segments rather than splitting it afterwards: **[FreeCAD-only]**

1. Create a face for one side (e.g. a square plate with a circular hole) with Part MakeFace.
2. Create a face for the other side (e.g. a circular face filling that hole).
3. Combine them with Part Builder in *Shell from faces* mode, with **Refine shape**
   disabled.

### 7.5 Faces of solids, with datum planes

Partitioning selected faces with a datum plane without splitting the whole volume is
described as tricky, and two multi-step routes are given — one via downgrade / Slice apart
/ upgrade to shell / convert to solid, the other via subshapebinders and Boolean fragments
against a new Body to avoid a cyclic dependency. **[FreeCAD-only]**

The worked example is a cylindrical hole face partitioned by a plane so a 180° load from a
pin can be applied to it — which is the same problem as loading half a bore.

---

## 8. Assembly geometries

A current major limitation: **the FEM workbench does not support multiple meshes.** Parts
of an assembly cannot be meshed individually and then connected with constraints. Instead
a single object containing all the parts is created with a Part boolean tool and meshed.

The choice of boolean is governed by whether individual parts and their boundaries need to
stay selectable:

| Tool | Parts individually selectable |
| --- | --- |
| Part Fuse | No |
| Part JoinConnect | No (behaves like Fuse) |
| Part Compound | Yes |
| Part BooleanFragments | Yes (behaves like Compound) |

**Whether the mesh is continuous** then follows from the geometry, not from the tool: parts
that touch exactly produce a continuous mesh and need no constraints, unless a Part
Compound is used with non-coincident nodes, or Gmsh's *Coherence Mesh* / Netgen's *Glue* is
false. Any gap at all — or an intersection inside a Part Compound — breaks continuity, and
tie or contact constraints become necessary.

The page offers a good diagnostic for this: run a frequency analysis and view the first
mode shapes with the Warp filter. If the parts are not connected, they fly apart.

**The recommended workflow** — the page says it is often advised, particularly for
multi-material assemblies and for solids embedded in other solids without cutouts — is
Boolean Fragments in Compsolid mode followed by a **Compound filter**. The reason
matters: a compound is only a container of topologically unconnected shapes and can hold
anything, so the mesher may not treat it as intended; Boolean Fragments always produces a
Compound, and the Compound filter extracts the Compsolid — solids connected by their faces
— out of it. The Shape Content tab of Check geometry is the way to confirm what you
actually have. Even with this workflow, tiny gaps and misalignments still have to be
avoided.

For 2D geometries with multiple connected or embedded regions the same trap exists in a
worse form: Boolean Fragments yields a Compound without shells, the meshers renumber
elements on a Compound, and there is then no guarantee that references in analysis features
remain correct — edge numbering typically shifts. Since Boolean Fragments has no Shell mode
and CompSolid applies only to solids, the page recommends building such geometry from
segments as in §7.4.

**Two errors and their workarounds.** These:

```
ERROR: femelement_table != count_femelements
Error in get_femelement_sets -- > femelements_count_ok() failed!
```

```
*ERROR in calinput: no material was assigned
to element ...
```

are caused by missing or overlapping material definitions on some elements. Three
workarounds are given:

- leave the last material with no solid assigned, so it is applied automatically to every
  solid not referenced by another material definition
- use Netgen instead of Gmsh to mesh
- separate the parts slightly and connect them with tie constraints

---

## 9. Selecting interior entities

*On the source page this is a subsection of §8, not a section of its own. It is promoted
here because nothing else in §8 applies to us and this does.*

Selecting internal faces or volumes is described as tricky, and is needed for interior
material assignments, body loads and boundary conditions — especially in thermal and
electromagnetic analyses with cores, inclusions or external fluid domains. Four routes:
**[FreeCAD-only]**

1. *1.1:* the Clarify Selection tool — called the easiest method
2. enable a clipping plane during selection and pick the internal faces
3. enable transparency and use the Selection View with *Picked object list* checked
4. select another, external object and edit the **References** property by hand, typing the
   geometric object's name and number

One warning that generalises beyond FreeCAD: **select entities belonging to the meshed
object.** Hiding the boolean object and selecting its base objects instead is called a
common mistake — verify that the selection reads `CompoundFilter.Solid1` rather than
`Box1.Solid1`.

*1.1:* if a selected CompSolid face belongs to two solids, a pop-up asks which.

---

## 10. Meshing basics

### 10.1 Element size

A mesh that is too coarse is called one of the most common sources of inaccuracy and other
problems in FEM, and the page puts part of the blame on automatic meshers: left at default
values, they typically generate very coarse, unsuitable meshes.

The practice recommended:

- know the approximate dimensions of the part, especially the **smallest relevant feature**
  (Std Measure finds it), and set the maximum element size from that
- set a **minimum** element size as well, to stop tiny elements forming around small
  geometric features — which produces unnecessarily dense meshes, and can make FreeCAD
  crash or freeze while generating them
- start coarser, look at the result, and refine — "some experience is necessary"
- refine **locally**, at large stress gradients and notches, and stay relatively coarse
  away from them; this cuts element count substantially and with it solving time. Local
  refinement is defined with FEM MeshRegion

The page illustrates the three states: default and too coarse, globally refined, locally
refined.

### 10.2 Element type

The general rule is that hexahedra and quadrilaterals are preferable to tetrahedra and
triangles. But complex geometry cannot be hex-meshed, and FreeCAD's ability to generate
hexahedra is very limited (§11). Hex meshes produced by external meshers such as Gmsh can
be imported and used in the FEM workbench.

### 10.3 Element order

Depends on the analysis, but in most cases second-order elements are preferred. For
triangles and tetrahedra specifically, the first-order versions are "normally not
recommended for regular usage" and should be used only as filler elements in regions of low
importance. The exception the page allows: because FreeCAD cannot properly generate
hexahedra, linear tetrahedra can be used where the mesh is dense enough — especially in
contact analyses.

---

## 11. Quad and hex meshes

**Quads**, on surface geometry, from either mesher:

- Gmsh — set **Algorithm 2D** to *Quasi-structured Quad* (which currently does not work for
  second-order elements), or enable **Recombine All** and choose a **Recombination
  Algorithm**
- Netgen — enable **Quad Dominated**

**Hexes**, on volumes, with significant limitations in both:

- Gmsh — **Subdivision Algorithm** set to *All Hexahedra*, but the page states plainly that
  the resulting elements are not shaped as one would expect from hex meshes used in
  practice
- Netgen, *1.1:* for simple extruded shapes, hex or hex-dominated meshes by extrusion, with
  **Quad Dominated** enabled and **ZRefine** set to *Regular* (*Custom* requires specifying
  each element's height). **ZRefine Direction** changes the extrusion direction from the
  default Z; **ZRefine Size** sets element height as a fraction of the total. First-order
  meshes only, unless every generated element is a hexahedron

---

## 12. Negative Jacobians

The mechanism, in the page's own terms: meshers have to follow the CAD model and place the
mid-side nodes of second-order elements **on the geometry**. With more complex shapes this
can stretch elements so far that they invert. The Jacobian is one of the most common mesh
quality measures, representing an element's deviation from the ideal shape; it goes
negative when the element turns inside out — either from large deformation during the
analysis, or from this meshing problem.

So the failure appears when second-order meshing meets small edges and faces, which arise
either because the geometry cannot be simplified further or because an appropriate
modelling procedure produced them anyway.

In FreeCAD, negative Jacobians are reported by Gmsh or by CalculiX, and their locations are
highlighted when the analysis is submitted with **Run solver calculations**.

Remedies, in the page's order:

1. **Set Second Order Linear** on the FEMMeshGmsh or FEMMeshNetgen object. Mid-side nodes
   are then placed at the midpoint of the initially straight first-order edges instead of
   being snapped to the geometry. The page says this resolves the issue in most cases.
2. Use Netgen instead of Gmsh — less prone to the problem, but it does not report negative
   Jacobians, so the user may only find out on submitting the analysis.
3. Reduce the element size further.
4. Export the geometry and mesh it in the Gmsh or Netgen (NGSolve) GUI or another
   standalone mesher such as Salome_Meca, which have extra features for this — Gmsh's
   "high-order tools" are named.
5. **Last resort only:** drop to first-order elements, which for tetrahedra are known for
   their inaccuracy.

The page closes the section by insisting that negative Jacobians are usually the fault of
messy modelling and absent geometry preparation — "especially common with STEP models
downloaded from various websites" — and that even when such a mesh is eventually generated,
the results are likely to be poor. Geometry clean-up comes first.

---

## 13. Mesh convergence studies, and singularities

Recommended for all serious projects needing accurate results, because results can change a
lot and approach the correct values only as the mesh is refined.

The procedure:

1. Take the first results and note them — usually maximum von Mises stress, von Mises
   stress at a given location, and maximum displacement. Refine the mesh, globally or
   better locally with FEM MeshRegion, and re-run.
2. Note the new values. If they differ significantly, refine again and re-run.
3. Repeat while the results still change significantly. They usually grow.

Plotting a result against mesh density makes the onset of convergence easier to see. The
acceptable difference between two runs is given as a few percent, e.g. below 5 %.

**Three curve shapes**, from the page's own convergence plot:

| Curve | Behaviour |
| --- | --- |
| Displacement | Converges quickly |
| Maximum stress at a notch, such as a hole | Converges, but needs more refinement iterations |
| Maximum stress at a sharp corner with a fixed boundary condition | **Does not converge at all** |

That third case is a **stress singularity**: maximum stress grows indefinitely no matter
how far the mesh is refined. It is called a non-physical effect, and four causes are named:

- concentrated forces applied to solid and shell models
- boundary conditions applied to points (individual nodes)
- sharp corners
- contact occurring at a corner

Four ways of dealing with them:

- apply loads and boundary conditions to small **areas** rather than points — see §7 on
  partitioning
- add small fillets to sharp corners, explicitly an exception to §6.1's rule of omitting
  small fillets
- include plasticity in the material behaviour, so stress redistributes and is limited to
  what the plasticity definition allows, while watching the level of yielding (plastic
  strain)
- ignore the singularity and read stresses away from it where possible, under St. Venant's
  principle

The page's own caption for the red curve adds that a small fillet would have to be added
**and** the connection modelled in a more realistic, flexible way for it to converge.

---

## 14. This project's reading

The nine task-level changes this page argues for are listed in
[freecad-tutorials.md §7](freecad-tutorials.md) and are not repeated here. What follows is
only the mapping — which parts of the page apply to us, and which do not.

### 14.1 What transfers directly

| Section | Bears on |
| --- | --- |
| §10.3 element order | [D-03](requirements.md) — the page independently endorses second-order tets and calls first-order tets unsuitable for regular use |
| §12 negative Jacobians | The failure mode second-order meshing has at small `fillet_radius`. FreeCAD's **Second Order Linear** is Gmsh's `Mesh.SecondOrderLinear`; the high-order tools it names are `Mesh.HighOrderOptimize` |
| §13 convergence and singularities | [D-12](requirements.md)'s singularity protocol. The three curve shapes are the discriminator D-12 needs, and they say the sharp-corner mutant should be *divergent*, not merely over threshold |
| §13 singularity causes | Both of our own: the load face **and** the fixed support face. M2.2's frozen record covers the load; the support deserves the same note |
| §10.1 element size | Our task-declared characteristic length and local refinement factor, which [D-21](requirements.md) keeps out of the agent's reach. The advice to set a **minimum** size as well as a maximum is the part we have not written down |
| §6.3 planar symmetry | A factor of two on every solve in a run, if `L_bracket`'s frozen part and load records are chosen to allow it |
| §6.1 defeaturing | The `L_bracket` parameter bounds. A `fillet_radius` minimum near zero is the defeaturing exception this page names, not an ordinary small fillet |
| §3 geometry validity | Cheap to assert in the pipeline before meshing, and free to do at CAD time rather than discovering it at mesh time |

### 14.2 What does not

**Everything that assumes a GUI.** §4's normal checks, §7.4 and §7.5's partitioning
recipes, §9's interior selection — these solve the problem of *pointing at* a face with a
mouse. We never point: CadQuery tags faces in code and the tags carry through to Gmsh
physical groups and `.inp` element sets ([D-06](requirements.md)). The page's own warning in
§9 — select entities belonging to the meshed object, not its base objects — is the manual
version of what our label chain does structurally, and M2.4 verifies by reading the
generated `.inp`.

**§8 assembly geometries.** FreeCAD's single-mesh limitation is FreeCAD's. Our parts are
single solids from one parametric script, and [D-08](requirements.md) allows one load case
per task. Nothing in §8 applies, including the two CalculiX material-assignment errors.

**§2.1, §2.2 and §2.3 — beams, shells, planar.** Correct advice we cannot take. The
project's parts are solid-meshed by construction, and [D-03](requirements.md) fixes C3D10
tets. Worth recording anyway for one reason: §2.2's cost argument — three to five elements
through the thickness of a thin wall, with no hexahedra available — is exactly what will
bite if the agent drives `wall_thickness` toward its minimum. That is a D-13 budget
question, not an element-type question, but it comes from the same geometry.

**§11 quad and hex meshes.** Gmsh's *All Hexahedra* is described by the page itself as not
producing what practitioners would expect, and Netgen is not in our stack.

### 14.3 The one thing it changes about how we read this page

§14.1 is enough material for M5.10's `SKILL.md` to be written from a cited source rather
than from memory. The distinction the agent has to make on every contour — a real stress
concentration versus a mesh artefact — is §13, and the four causes and four remedies there
are the substance of it. The skill is instruction, never authority
([solution architecture §6](solution-architecture.md)), so what belongs in it is this page's
reasoning, while D-12's threshold and D-21's refusal stay in the runtime.

---

## 15. Revision log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-17 | First pass. Source page captured section by section; §14 maps it onto the project |

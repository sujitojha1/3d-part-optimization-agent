---
title: CAM Workbench
source: https://wiki.freecad.org/CAM_Workbench
tags: [FreeCAD, CAM, CNC, G-code]
captured: 2026-09-17
---

# CAM Workbench (FreeCAD)

## Introduction

The CAM Workbench produces machine instructions for CNC machines (mills, lathes, laser cutters, etc.) from a FreeCAD 3D model. Instructions are typically a G-code dialect.

Workflow:

1. A **3D model** is the base object — usually made with Part Design, Part, or Draft.
2. A **CAM Job** is created in the CAM Workbench. It holds everything needed to generate G-code: stock material, the mill's tool set, and commands controlling speed and movement.
3. **CAM Tools** are selected as required by the Job Operations.
4. **Milling paths** are created with operations such as Contour and Pocket. These use FreeCAD's internal G-code dialect, independent of the CNC machine.
5. **Export** the job as G-code matching your machine — the *post processing* step. Several post processors are available.

## General concepts

G-code is generated from directives and operations contained in a CAM Job. The Job Workflow lists them in execution order, populated by adding CAM Operations, Path Dressups, Supplemental Commands, and Path Modifications from the CAM menu or toolbar.

The workbench provides a Tool Manager (Library / Tool-Table), G-code inspection, and simulation tools. It links the postprocessor and supports importing/exporting job templates.

External dependencies and settings:

| Setting | Location |
| --- | --- |
| Model units | Edit → Preferences → General → Default unit system |
| Macro file path, geometric tolerances | Edit → Preferences → CAM → Job Preferences |
| Colors | Edit → Preferences → CAM → GUI |
| Holding tag parameters | Edit → Preferences → CAM → Dressups |

The base 3D model must also be of sufficient quality to pass Check Geometry.

## Limitations

- Most CAM tools are **2.5D only** — a fixed 2D shape cut down to a given depth. Exceptions producing true 3D paths: **3D Pocket** and **3D Surface**.
- Designed mainly for a standard 3-axis (XYZ) mill/router; lathe tools come via the Turning add-on.
- Most operations return paths assuming a **standard endmill**, regardless of the tool type in the tool controller. *(26.3: Engrave, 3D Surface, and others now support tool shape awareness.)*
- Operations are **not aware of clamping mechanisms**. Review and simulate paths before sending code to the machine; model clamps in FreeCAD if needed to check for collisions.

## Units

- FreeCAD base units are `mm` and `s`, so velocity is `mm/s` — this is what is stored internally regardless of anything else.
- With the default schema, a feed rate entered without a unit string becomes `mm/s`.
- Most CNC machines expect `mm/min` or `in/min`; most post processors convert automatically.

**Schemas**

- Changing the schema only changes the default unit string in input fields. Metric CAM users should prefer the **"Metric Small Parts & CNC"** schema; US users, Imperial Decimal or Building US.
- Schema choice has no effect on output — it just avoids input errors.

**Output**

- Correct output units are the post processor's responsibility, applied only at post-processing time.
- Machine output units are unrelated to the selected schema.
- Post processors emit metric (`G21`), imperial (`G20`), or are configurable; configurable ones default to metric.
- For imperial output from a configurable post processor, set the argument in the job output configuration (e.g. `--inches` for LinuxCNC). Store it in a job template and set that as default to make it automatic.

**Inspection** — the CAM Inspect tool shows G-code in `mm/s`, because it is not post-processed.

## Heights and depths

Many commands expose various height and depth properties; the wiki has a visual reference diagram for these depth settings.

## Commands

Some commands are experimental and not enabled by default (see *CAM experimental*).

### Project

- **New Job** — creates a new CNC job.
- **Sanity Check** — checks the selected job for missing values.
- **Post Process** — exports a project to G-code.
- **Post Process Selected** — TBD *(26.3)*.
- **Export Template** — exports the current job as a template.

### Tools

- **CAM Simulator** — the new, improved simulator *(1.0)*.
- **Legacy CAM Simulator** — shows the milling operation as done on the machine.
- **Inspect Toolpath** — shows the G-code for checking.
- **Finish Selecting Loop** — completes a loop from two selected edges.
- **Toggle Operation** — activates/deactivates a path operation.
- **ToolBit Library Manager** — editor for ToolBit libraries.
- **Add Toolbit…** — opens the ToolBit Selector.

### Basic operations

- **Profile** — profile of the whole model, or from selected faces/edges.
- **Pocket Shape** — pocketing from one or more selected pockets.
- **Mill Facing** — surfacing path.
- **Helix** — helical path.
- **Adaptive** — adaptive clearing and profiling.
- **Slot** — slotting from selected features or custom points.
- **Drilling** — drilling cycle.
- **Thread Milling** — thread milling from features of a base object.
- **Engrave** — engraving path.
- **Deburr** — deburr path.
- **Vcarve** — engraving path using a V tool shape.

### 3D operations

- **3D Pocket** — path for a 3D pocket.
- **3D Surface** — path for a 3D surface *(experimental)*.
- **Waterline** — waterline path for a 3D surface *(experimental)*.

### Path dressup

- **Array** — TBD *(1.1)*.
- **Axis Map** — remaps one axis to another.
- **Boundary** — boundary dressup on a selected path.
- **Dogbone** — dogbone dressup.
- **Drag Knife** — dragknife dressup.
- **Lead In/Out** — adds lead-in and/or lead-out points.
- **Mirror** — TBD *(26.3)*.
- **Ramp Entry** — ramp entry dressup.
- **Tag** — holding tag dressup.
- **Z Depth Correction** — corrects Z depth using a Probe Map.

### Supplemental commands

- **Comment** — inserts a comment in the path's G-code.
- **Stop** — inserts a full machine stop.
- **Custom** — inserts custom G-code.
- **Probe** — creates a probing grid from job stock.
- **Path From Shape TC** — path object from a selected Part object *(experimental)*.

### Path modification

- **Copy Operation** — parametric copy of a selected path object.
- **Array** — array by duplicating a selected path.
- **Simple Copy** — non-parametric copy of a selected path object.

### Miscellaneous

- **Area** — feature area from selected objects *(experimental)*.
- **Area Workplane** — feature area workplane *(experimental)*.

### Obsolete

- **Fixture** — changed fixture position; gone from 1.1 onward.
- **Face** — surfacing path; gone from 26.3 onward.
- **Tapping** — gone from 26.3 onward.

## ToolBit architecture

Tools, bits, and the Tool Library are managed through the ToolBit architecture: CAM Tools, CAM ToolShape, CAM ToolBit, CAM ToolBit Library, CAM ToolController.

## Other references

- **CAM FAQ** — shared concepts with other CAM packages plus FreeCAD's peculiarities; start here when something seems wrong.
- **CAM SetupSheet** — customize how operation property values are calculated.
- **CAM Postprocessor Customization** — for machines that no available post processor supports.
- **CAM fourth axis** — experimental four-axis milling.
- **Preferences** — CAM Workbench preferences.
- **CAM scripting** — scripting reference.

## Tutorials and videos

- *CAM Walkthrough for the Impatient* — quick tutorial to get familiar with CAM.
- *FreeCAD Path: Custom paths with Python, Parts 1–5* — playlist by sliptonic.
- *FreeCAD CAM Path Workbench* — 7-video playlist by CAD CAM Lessons.
- *FreeCAD CAM CNC* — 8-video playlist by CAD CAM Lessons.
- See also the CAM section of the FreeCAD Video tutorials wiki page.

## Roadmap

*CAM Development Roadmap* — for developers wanting to contribute to CAM.

---

Source: [CAM Workbench — FreeCAD Documentation](https://wiki.freecad.org/CAM_Workbench)

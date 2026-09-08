3D Part Optimization
Sujit Ojha

Given a loaded part, make it lighter without making it fail. The agent looks at the results, reasons about material and geometry together, and explains itself.

Why this is not a numerical optimiser
A topology optimiser searches a parameter space. This agent reads the stress plot the way an engineer does, decides that the failure is at a fillet rather than the web, and reasons about whether the right answer is more material, a different radius, or a different alloy.

Material selection is the part no optimiser handles: yield strength, density, cost, machinability, corrosion resistance and availability trade against each other, and the right answer depends on what the part is for.

The loop
mesh  ->  FEA  ->  READ THE STRESS CONTOUR VISUALLY
      ->  "failing at the fillet, not the web"
      ->  propose one change, in geometry or material, and state why
      ->  re-run and check whether the reason held
Vision matters here. The colour plot carries information that the raw max-stress number does not: where the concentration is, whether it is a singularity from a sharp corner in the mesh, whether the load path has shifted.

Verifier
mass                 down, in grams
max von Mises        below yield, with the stated safety factor
displacement         within limit
manufacturability    can it be machined or printed, minimum wall, draft, overhang
prediction accuracy  did the agent's stated reason match what the next FEA showed
That last row is the interesting one. It scores the reasoning rather than the outcome.

Mutation corpus
Meshes with singularities at sharp corners that produce fake infinite stress · a load case applied in the wrong direction · a material card with the wrong units, MPa against Pa. An agent that trusts the number without sanity-checking the setup fails these.

The refusal case
A mass target that cannot be met at the required safety factor with any material in the library. The agent must say so and show the frontier it explored.

Stack
FreeCAD, Gmsh for meshing, CalculiX or FEniCS for FEA, PrusaSlicer or a CAM check for manufacturability.
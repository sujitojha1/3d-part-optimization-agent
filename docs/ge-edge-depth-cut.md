# Variable-depth edge cut

The marked long outer side of `GE_Challenge_Bracket` now has a face-aligned rectangular cutting block and native FreeCAD Boolean Cut in `data/ge_manual/GE_Challenge_Bracket_EdgeCut.FCStd`.

Open the document, expand **Bracket — variable-depth edge cut**, select **Cutting block — edit Cut Depth**, and edit **Data → Cut settings → Cut Depth**. **Cut Span** controls its length along the edge. Recompute if needed. Select the block and press Space to display it; hide the result and show OriginalBracket to inspect the overlap. The frozen original is retained in the feature tree.

Depth runs inward normal to the long outer side face; the block is rotated to that face rather than aligned to the world axes. The default is 6 mm depth, 100 mm span, centered along that face, extending through the part's height. A 1 mm outside overlap prevents coincident Boolean boundaries. No Python proxy is required when reopening the document; native expressions drive the box and cut.

At Ti density 4430 kg/m³, the default removes 23,835.2 mm³ / 105.6 g (5.15%): 2052.2 g becomes 1946.6 g. Checked depths 0, 2, 4, 6 and 8 mm retain a valid single solid and monotonically reduce volume. Reopening and changing the depth to 4 mm reproduces the checked volume. Other depths/spans require fresh geometric checks. Strength, stress concentrations at the new corners, minimum-wall compliance and CAM readiness have not been validated.

Build: `vendor/fem-env/bin/python scripts/ge_edge_depth_cut.py`. Evidence: `out/ge_edge_depth_cut/cut-check.json`; preview: `out/ge_edge_depth_cut/preview.png`; STEP export: `out/ge_edge_depth_cut/GE_Challenge_Bracket_EdgeCut.step`. The derived CAD stays local under the project's existing data policy. This is a separate editable candidate, not a replacement of the frozen analysis baseline.

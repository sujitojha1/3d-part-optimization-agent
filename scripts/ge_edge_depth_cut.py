"""Create a native, editable Part Box/Cut on the marked long outer bracket face.

Run with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/ge_edge_depth_cut.py
The frozen analysis source is unchanged. Edit CuttingBlock.CutDepth in FreeCAD.
"""
import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'data/ge_manual/GE_Challenge_Bracket_deck_frame.step'
DEST = ROOT / 'data/ge_manual/GE_Challenge_Bracket_EdgeCut.FCStd'
OUT = ROOT / 'out/ge_edge_depth_cut'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shape = Part.Shape()
    shape.read(str(SOURCE))
    # Select by geometry, not stored Face18: long vertical outer side, opposite lugs.
    matches = [f for f in shape.Faces if isinstance(f.Surface, Part.Plane)
               and f.normalAt(0, 0).x > .98 and abs(f.normalAt(0, 0).z) < 1e-6
               and f.Area > 3000]
    if len(matches) != 1:
        raise ValueError(f'Expected one long outer side face, found {len(matches)}')
    face = matches[0]
    outward = face.normalAt(0, 0)
    inward = -outward
    up = App.Vector(0, 0, 1)
    along = up.cross(inward)
    along.normalize()
    center = face.CenterOfMass
    rotation = App.Rotation(inward, along, up, 'ZXY')
    doc = App.newDocument('GE_Bracket_EdgeCut')
    base = doc.addObject('Part::Feature', 'OriginalBracket')
    base.Label = 'Original bracket (unchanged)'
    base.Shape = shape
    block = doc.addObject('Part::Box', 'CuttingBlock')
    block.Label = 'Cutting block — edit Cut Depth'
    block.addProperty('App::PropertyLength', 'CutDepth', 'Cut settings', 'Inward distance from the aligned outer face, in mm')
    block.addProperty('App::PropertyLength', 'CutSpan', 'Cut settings', 'Length of the marked strip along the outer face, in mm')
    block.CutDepth = 6
    block.CutSpan = 100
    block.setExpression('Length', 'CutDepth + 1 mm')
    block.setExpression('Width', 'CutSpan')
    block.Height = shape.BoundBox.ZLength + 2
    block.Placement.Rotation = rotation
    # 1 mm extends outside the part to avoid coincident boolean faces.
    block.setExpression('Placement.Base.x', f'{center.x + outward.x:.12f} mm - {along.x:.12f} * CutSpan / 2')
    block.setExpression('Placement.Base.y', f'{center.y + outward.y:.12f} mm - {along.y:.12f} * CutSpan / 2')
    block.Placement.Base.z = shape.BoundBox.ZMin - 1
    result = doc.addObject('Part::Cut', 'WeightReductionCut')
    result.Label = 'Bracket — variable-depth edge cut'
    result.Base = base
    result.Tool = block
    result.Refine = True
    doc.recompute()
    samples = []
    for depth in [0, 2, 4, 6, 8]:
        block.CutDepth = depth
        doc.recompute()
        s = result.Shape
        if s.isNull() or not s.isValid() or len(s.Solids) != 1:
            raise ValueError(f'Invalid cut at {depth} mm')
        removed = shape.Volume - s.Volume
        samples.append({'depth_mm': depth, 'volume_mm3': s.Volume,
                        'removed_mm3': removed, 'ti_mass_saved_g': removed * .00443,
                        'valid_single_solid': True})
    assert abs(samples[0]['removed_mm3']) < .01
    assert all(a['removed_mm3'] < b['removed_mm3'] for a,b in zip(samples,samples[1:]))
    block.CutDepth = 6
    doc.recompute()
    base.Visibility = False
    block.Visibility = False
    result.Visibility = True
    doc.recompute()
    doc.saveAs(str(DEST))
    result.Shape.exportStep(str(OUT / 'GE_Challenge_Bracket_EdgeCut.step'))
    record = {'source': str(SOURCE.relative_to(ROOT)),
              'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'document': str(DEST.relative_to(ROOT)), 'default_depth_mm': 6,
              'span_mm': 100, 'outward_normal': list(outward),
              'cut_direction': list(inward), 'source_volume_mm3': shape.Volume,
              'samples': samples, 'validation': 'Geometric validity and volume reduction only; no new FEA or CAM acceptance.'}
    (OUT / 'cut-check.json').write_text(json.dumps(record, indent=2))
    # Headless CAD preview; no graphics context required.
    import os
    os.environ.setdefault('MPLCONFIGDIR', str(OUT / 'mpl-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
    fig = plt.figure(figsize=(14, 9), facecolor='#f3f5f7')
    def draw(ax, solid, color, alpha=1):
        vs, ts = solid.tessellate(.3)
        poly = Poly3DCollection([[list(vs[i]) for i in t] for t in ts],
                               facecolors=color, alpha=alpha, shade=True)
        ax.add_collection3d(poly)
        lines = [[list(v) for v in edge.discretize(Deflection=.2)] for edge in solid.Edges]
        ax.add_collection3d(Line3DCollection(lines, colors='#344655', linewidths=.45, alpha=alpha))
    for col in range(2):
        ax = fig.add_subplot(1, 2, col + 1, projection='3d')
        draw(ax, shape if col == 0 else result.Shape, '#9faebc')
        if col == 0:
            draw(ax, block.Shape, '#ef713a', .6)
        ax.set(xlim=(-55, 80), ylim=(-170, 25), zlim=(-2, 65))
        ax.set_box_aspect((135,195,67))
        ax.view_init(elev=65, azim=90)
        ax.set_axis_off()
        ax.set_title('Face-aligned cutting block' if col == 0 else 'Result: 6 mm inward cut', fontsize=15)
    fig.tight_layout()
    fig.savefig(OUT / 'preview.png', dpi=150)
    plt.close(fig)
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(DEST))
    reopened.CuttingBlock.CutDepth = 4
    reopened.recompute()
    assert abs(reopened.WeightReductionCut.Shape.Volume - samples[2]['volume_mm3']) < .01
    App.closeDocument(reopened.Name)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()

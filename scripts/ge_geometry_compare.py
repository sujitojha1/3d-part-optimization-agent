"""Render all local bracket candidates in interface-aligned views; no CAD edits.
Run with vendor/fem-env/bin/python scripts/ge_geometry_compare.py.
Outputs under gitignored out/ge_geometry_comparison/.
"""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
import FreeCAD,Part
import numpy as np
import pyvista as pv
from PIL import Image,ImageOps,ImageDraw
out=ROOT/'out/ge_geometry_comparison';out.mkdir(parents=True,exist_ok=True)
files=[ROOT/'parts/ge_bracket.FCStd']+sorted((ROOT/'data/simjeb').glob('*.stp'))+sorted((ROOT/'data/simjeb').glob('*.STEP'))
records=[]
for file in files:
 if file.suffix=='.FCStd':
  doc=FreeCAD.openDocument(str(file));shapes=[o.Shape for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull()];shape=max(shapes,key=lambda s:s.Volume)
 else:shape=Part.read(str(file))
 vertices,tri=shape.tessellate(0.12)
 mesh=pv.PolyData(np.array([[v.x,v.y,v.z] for v in vertices]),np.c_[np.full(len(tri),3),np.array(tri)].ravel())
 # Normalize display frame using measured bolt and pin cylinder axes only.
 def vec(v):return np.array([v.x,v.y,v.z])
 cylinders=[f for f in shape.Faces if isinstance(f.Surface,Part.Cylinder)]
 bolts=[f for f in cylinders if 5.0 < f.Surface.Radius < 5.5]
 pins=[f for f in cylinders if 9.4 < f.Surface.Radius < 9.7]
 if not bolts or not pins:raise ValueError('Cannot identify interface axes: '+file.name)
 bc=np.mean([vec(f.CenterOfMass) for f in bolts],axis=0);pc=np.mean([vec(f.CenterOfMass) for f in pins],axis=0)
 z=vec(bolts[0].Surface.Axis)
 if np.dot(pc-bc,z)<0:z=-z
 y=vec(pins[0].Surface.Axis);y=y-z*np.dot(y,z);y=y/np.linalg.norm(y)
 x=np.cross(y,z)
 if np.dot(bc-pc,x)<0:x=-x;y=-y
 rotation=np.stack([x,y,z]);mesh.points=(mesh.points-bc)@rotation.T
 record={'display_rotation_rows':rotation.tolist(),'display_origin':bc.tolist(),'file':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'valid':shape.isValid(),'solids':len(shape.Solids),'volume_native_units_cubed':shape.Volume,'bounds_native_units':[shape.BoundBox.XLength,shape.BoundBox.YLength,shape.BoundBox.ZLength]}
 for name,view in [('iso','iso'),('opposite','opposite'),('top','xy'),('front','xz')]:
  p=pv.Plotter(off_screen=True,window_size=(800,650));p.set_background('white');p.add_mesh(mesh,color='#e6a32f',smooth_shading=False,specular=0.2)
  if view=='iso':p.view_isometric()
  elif view=='opposite':
   c=np.array(mesh.center);r=mesh.length;p.camera_position=[c+np.array([-1,-1,1])*r,c,(0,0,1)]
  elif view=='xy':p.view_xy()
  else:p.view_xz()
  p.enable_parallel_projection();p.reset_camera();p.camera.zoom(1.12);p.add_text(file.name+' | '+name,font_size=11,color='black');p.show_axes();p.screenshot(str(out/f'{file.stem}_{name}.png'));p.close()
 records.append(record);print(json.dumps(record),flush=True)
canvas=Image.new('RGB',(1600,650*4),'#eeeeee')
ref=Image.open(ROOT/'docs/assets/ge-bracket/original-bracket.png').convert('RGB');ref.thumbnail((740,550));canvas.paste(ref,((800-ref.width)//2,55));ImageDraw.Draw(canvas).text((20,20),'GE challenge reference — original bracket',fill='black')
for i,file in enumerate(files,1):
 im=Image.open(out/f'{file.stem}_iso.png');canvas.paste(im,((i%2)*800,(i//2)*650))
canvas.save(out/'comparison.png');(out/'geometry-inventory.json').write_text(json.dumps(records,indent=2))

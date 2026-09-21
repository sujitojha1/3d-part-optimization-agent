"""M2A.3: assign the five material cards to the GE working mesh and verify each deck.

For each card in CARDS (sources and conditions in docs/ge-manual-materials.md),
opens the L1 mesh document from M2A.2, adds what a person adds by
hand in the FEM Workbench (a CalculiX solver and one MaterialSolid on the whole
solid), saves it, exports the CalculiX .inp and reads the material back:

- static deck: *MATERIAL / *ELASTIC must carry the card's E (MPa) and nu, and
  *SOLID SECTION must put every C3D10 element in that material. FreeCAD writes
  no *DENSITY in a static deck (only frequency, self-weight, centrifugal or
  transient thermal analyses need it);
- frequency deck of the same document: *DENSITY must equal the card's density
  converted to solver units (t/mm^3), so the conversion is checked in a deck too.

Mass in grams is volume (working-copy solid, mm^3) x density.

Writes data/ge_manual/materials/<card>/ (FCStd and decks; gitignored, derived
from licensed CAD) and out/ge_manual_materials/materials.json.

Run with the FEM environment's Python (scripts/fem_env.py finds it):
    $FEM_PYTHON scripts/ge_manual_materials.py
"""

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import FreeCAD  # noqa: E402
from ge_part import PART  # noqa: E402  the part M2A is locked to
import ObjectsFem  # noqa: E402
from femtools import ccxtools  # noqa: E402

MESH_DOC = ROOT / "data" / "ge_manual" / "mesh" / "L1" / f"{PART}_mesh_L1.FCStd"
MESH_QUALITY = ROOT / "out" / "ge_manual_mesh" / "mesh-quality.json"
DATA = ROOT / "data" / "ge_manual" / "materials"
OUT = ROOT / "out" / "ge_manual_materials"

LB_PER_IN3 = 27679.9047  # kg/m^3
KSI = 6.894757           # MPa
MSI = 6894.757           # MPa

# Values as used; derivations and citations are in docs/ge-manual-materials.md.
CARDS = {
    "ti6al4v": {
        "name": "Ti-6Al-4V (GE challenge baseline)",
        "role": "challenge baseline",
        "condition": "Ti-6Al-4V as specified by the GE challenge (yield set by the organisers); D-09 condition annealed",
        "youngs_mpa": 113800.0, "poisson": 0.342, "density_kg_m3": 4430.0,
        "yield_mpa": 903.2, "yield_basis": "GE challenge value, 131 ksi",
    },
    "al7075_t651": {
        "name": "Al 7075-T651 plate, 2.501-3.000 in",
        "role": "project comparison",
        "condition": "T651 (solution heat treated, stress relieved by stretching, artificially aged); plate 2.501-3.000 in thick",
        "youngs_mpa": round(10400 * KSI, 0), "poisson": 0.33, "density_kg_m3": 2810.0,
        "yield_mpa": round(61.1 * KSI, 1), "yield_basis": "specification minimum, 61.1 ksi, AMS-QQ-A-250/12 plate 2.501-3.000 in",
    },
    "al6061_t651": {
        "name": "Al 6061-T651 plate",
        "role": "project comparison",
        "condition": "T651 (solution heat treated, stretched, artificially aged); plate 0.250-4.000 in",
        "youngs_mpa": round(10000 * KSI, 0), "poisson": 0.33, "density_kg_m3": 2700.0,
        "yield_mpa": round(35.0 * KSI, 1), "yield_basis": "specification minimum, 35 ksi, ASTM B209 T6/T651",
    },
    "ss17_4ph_h1025": {
        "name": "17-4PH (UNS S17400) H1025",
        "role": "project comparison",
        "condition": "Condition A (1900 F solution treat) + aged 4 h at 1025 F, air cooled; bar AMS 5643",
        "youngs_mpa": round(29.0 * MSI, 0), "poisson": 0.272, "density_kg_m3": round(0.282 * LB_PER_IN3, 0),
        "yield_mpa": round(145.0 * KSI, 1), "yield_basis": "specification minimum, 145 ksi, H1025 (AMS 5643)",
    },
    "aisi4140_qt": {
        "name": "AISI 4140 quenched and tempered, ASTM A434 Class BD",
        "role": "project comparison",
        "condition": "oil quenched and tempered bar to ASTM A434 Class BD; stock about 5 in",
        "youngs_mpa": round(29.0 * MSI, 0), "poisson": 0.29, "density_kg_m3": round(0.282 * LB_PER_IN3, 0),
        "yield_mpa": round(100.0 * KSI, 1),
        "yield_basis": "specification minimum floor, 100 ksi, A434 Class BD over all sizes to 9.5 in",
    },
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material_block(inp):
    text = inp.read_text()
    m = re.search(r"\*MATERIAL, NAME=(\S+)\n\*ELASTIC\n([^\n]+)\n(?:\*DENSITY\n([^\n]+)\n)?", text)
    sec = re.findall(r"\*SOLID SECTION, ELSET=(\S+), MATERIAL=(\S+)", text)
    return m, sec, text


def elset_members(text, name):
    """Direct element count of an *ELSET, or the sets it names (FreeCAD nests Evolumes)."""
    m = re.search(rf"\*ELSET, ?ELSET={re.escape(name)}\n(.*?)(?=\n\s*\n|\n\*)", text, re.S)
    if not m:
        return None
    tokens = [t for t in re.split(r"[,\s]+", m.group(1)) if t]
    return {"ids": sum(t.isdigit() for t in tokens), "sets": [t for t in tokens if not t.isdigit()]}


def c3d10_in(text, elset):
    """Elements written under *Element, TYPE=C3D10, ELSET=<elset>."""
    m = re.search(rf"\*Element, TYPE=C3D10, ELSET={re.escape(elset)}\n(.*?)(?=\n\*|\Z)", text, re.S | re.I)
    return sum(1 for line in m.group(1).splitlines() if line.strip()) if m else 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mesh_q = json.loads(MESH_QUALITY.read_text())["levels"]["L1"]
    report = {"mesh_doc": str(MESH_DOC.relative_to(ROOT)), "mesh_connectivity_sha256": mesh_q["connectivity_sha256"],
              "freecad_version": ".".join(FreeCAD.Version()[:3]), "cards": {}}
    for key, c in CARDS.items():
        work = DATA / key
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        doc = FreeCAD.openDocument(str(MESH_DOC))
        part, analysis, mesh = doc.getObject("Bracket"), doc.getObject("Analysis"), doc.getObject("Mesh")
        solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiXCcxTools")
        analysis.addObject(solver)
        mat = ObjectsFem.makeMaterialSolid(doc, "Material")
        card = mat.Material
        card.update({"Name": c["name"], "YoungsModulus": f"{c['youngs_mpa']} MPa", "PoissonRatio": str(c["poisson"]),
                     "Density": f"{c['density_kg_m3']} kg/m^3", "YieldStrength": f"{c['yield_mpa']} MPa"})
        mat.Material = card
        mat.References = [(part, "Solid1")]
        analysis.addObject(mat)
        doc.recompute()
        volume = part.Shape.Volume
        doc.saveAs(str(work / f"{PART}_{key}_L1.FCStd"))

        rec = {**c, "density_t_per_mm3": c["density_kg_m3"] * 1e-12, "volume_mm3": round(volume, 3),
               "mass_g": round(volume * c["density_kg_m3"] * 1e-6, 1), "decks": {}}
        for kind in ("static", "frequency"):
            solver.AnalysisType = kind
            doc.recompute()
            fea = ccxtools.FemToolsCcx(analysis, solver)
            fea.update_objects()
            fea.setup_working_dir(str(work / kind), create=True)
            fea.write_inp_file()
            # write_inp_file ignores the working dir in 1.1.3 and writes to a temp dir.
            (work / kind).mkdir(exist_ok=True)
            inp = work / kind / f"{key}_{kind}.inp"
            shutil.copyfile(fea.inp_file_name, inp)
            m, sections, text = material_block(inp)
            e_nu = [float(v) for v in m.group(2).split(",")] if m else [None, None]
            dens = float(m.group(3)) if m and m.group(3) else None
            elsets = {s: elset_members(text, s) for s, _ in sections}
            d = {"inp": str(inp.relative_to(ROOT)), "sha256": sha256(inp), "material_name": m.group(1) if m else None,
                 "elastic_line": m.group(2) if m else None, "density_line": m.group(3) if m else None,
                 "solid_sections": sections, "elset_sizes": elsets,
                 "e_matches": e_nu[0] is not None and abs(e_nu[0] - c["youngs_mpa"]) < 1e-6 * c["youngs_mpa"],
                 "nu_matches": e_nu[1] is not None and abs(e_nu[1] - c["poisson"]) < 1e-9}
            # One section on the whole solid, whose elset is (or names) the set
            # FreeCAD writes every C3D10 into: its size must equal the mesh's.
            covered = 0
            if len(sections) == 1 and elsets[sections[0][0]]:
                e = elsets[sections[0][0]]
                covered = e["ids"] + sum(c3d10_in(text, n) for n in e["sets"])
            d["c3d10_in_section"] = covered
            d["all_elements_assigned"] = covered == mesh_q["femmesh"]["volumes"]
            if kind == "frequency":
                d["density_matches"] = dens is not None and abs(dens - rec["density_t_per_mm3"]) < 1e-6 * rec["density_t_per_mm3"]
            else:
                d["density_written"] = dens is not None
            rec["decks"][kind] = d
        FreeCAD.closeDocument(doc.Name)
        rec["verified"] = all(rec["decks"][k][f] for k in ("static", "frequency") for f in ("e_matches", "nu_matches", "all_elements_assigned")) \
            and rec["decks"]["frequency"]["density_matches"]
        report["cards"][key] = rec
        print(key, rec["mass_g"], "g", "verified" if rec["verified"] else "NOT VERIFIED",
              rec["decks"]["static"]["elastic_line"], rec["decks"]["frequency"]["density_line"],
              rec["decks"]["static"]["solid_sections"], flush=True)
    (OUT / "materials.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

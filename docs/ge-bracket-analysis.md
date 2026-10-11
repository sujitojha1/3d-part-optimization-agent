# ge_bracket analysis assembly — load-case record to checked CalculiX deck (M3.3)

| | |
| --- | --- |
| Task | M3.3 ([#13](https://github.com/sujitojha1/3d-part-optimization-agent/issues/13)) · [plan](plan.md) M3 step 3 |
| Date | 2026-10-11 |
| Part and load case | The parametric `ge_bracket` ([frozen record](ge-bracket-part.md)) under LC1 ([record](ge-bracket-lc1.md), `parts/ge_bracket_lc1.json`) |
| Tools | FreeCAD 1.1.3 FEM Workbench; `femtools.ccxtools` writes the deck. Run on the Windows machine, not the D-17 Mac |
| Script | `$FEM_PYTHON scripts/ge_bracket_analysis.py --bounds` (about 4 min). Writes `out/ge_bracket_analysis/analysis.json` |
| Status | **Done.** The assembly is `ok` at the baseline and all 12 parameter bounds, and `lc1_solve.py` on it reproduces the M2.5 record exactly. Three points of the issue text are not implemented as written, each for a recorded reason (section 2) |

## 1. What it does

`assemble(params, lc, work, sizes=None)` in `scripts/ge_bracket_analysis.py` takes one candidate's parameters
and one load-case record, and returns a record with `status` `ok` or `unverified` and a `diagnostic`. For `ok`
it also returns the open document, the analysis, the `ccxtools` object and the deck path, for the caller to solve.

1. **Mesh.** `gm.mesh_candidate` re-selects the faces (M3.1) and meshes to D-24 with the retry and quality gate
   (M3.2). An `unverified` mesh stops here and no deck is written.
2. **Analysis.** From the record: the CalculiX solver object, one material card, one `Fixed` constraint per
   support face, and one Rigid Body Constraint on the load faces. Every quantity carries its unit (`MPa`,
   `kg/m^3`, `N`). Faces come from `gb.select`, never from a stored index.
3. **Deck.** `ccxtools` writes it. Nothing in this project writes or edits the deck.
4. **Deck check.** The written deck is read back and compared with the record (section 3). Any disagreement is
   `unverified`.

The record is task data. `validate` refuses one this assembly does not implement — units other than
mm / N / MPa, a pin model other than `rigid`, a model extent other than `full`, or a face name that is not a
single-face predicate — with an error, because a bad record is a task fault and not a verdict on the candidate.

## 2. Where it departs from the issue text

| Issue text | What is implemented | Why |
| --- | --- | --- |
| Rigid Body Constraints at the four bolt holes | A `Fixed` constraint on each bolt-hole face | The LC1 record M2.2 froze: every node on the hole held in all DOF, as SimJEB's RBE2 spiders with SPC 123456. One constraint per hole, so `ccx` prints each bolt's reaction separately |
| The D-23 symmetry Displacement constraint | None; the full model | D-23 does not hold: the bolt pattern is not symmetric about the clevis midplane ([part record §7](ge-bracket-part.md)). A record asking for a half model is refused |
| A Section Print feature on the supports | None | `ccxtools` already writes `*NODE PRINT, NSET=Fixed_…, TOTALS=ONLY` with `RF` for every Fixed constraint. That is the reaction total M2.5 reads, and the deck check requires it for each support |

The pin-load model is the one M2.2 chose and is unchanged: `*RIGID BODY` on both bore faces, reference node at
the load point, the load vector as `*CLOAD` on that node.

## 3. What the deck check reads

| Card | Rule |
| --- | --- |
| `*Element` | C3D10 and nothing else |
| `*ELASTIC` | One card; E and ν equal to the record's |
| `*NSET` per support | Present and non-empty |
| `*BOUNDARY` | Exactly DOF 1, 2 and 3 on each support set, and nothing else |
| `*NODE PRINT … TOTALS=ONLY` / `RF` | Present for each support set |
| `*RIGID BODY` | One, on `Pin`, with a non-empty node set and its reference node at the record's load point |
| `*CLOAD` | Sums to the record's vector, on the reference node alone |
| `*STEP` | One static step |
| Other loads and ties | None of `*DLOAD`, `*DSLOAD`, `*TEMPERATURE`, `*EQUATION`, `*MPC`, `*TIE`, `*CONTACT PAIR` |

The deck has no `*DENSITY` card: the step is static with no body load. Mass comes from the CAD volume (M2.5).

## 4. Results (11 Oct, Windows)

| Check | Result |
| --- | --- |
| Baseline and all 12 parameter bounds | 13 of 13 `ok`. Each support set holds 166–318 nodes, the pin set 608–2,040. Deck write 4.5–8.1 s |
| Wrong-direction mutant (D-16) | Its deck agrees with its own record. Read against LC1 it fails on one rule: `*CLOAD sums to [0, 0, −35585.77]` |
| Wrong modulus | The same deck read against a record with E × 10⁻⁶ fails on `*ELASTIC` |
| Unverified mesh | A mesh that fails M3.2 returns `unverified`; no deck directory is created |
| Unimplemented records | Wrong units, the `half_bore` pin model and a half model are each refused |
| `lc1_solve.py` on the assembly | Same mesh (72,046 nodes, 43,430 C3D10), and the same results as the M2.5 record to every printed digit: maximum displacement 0.4515 mm, peak outside the support zone 435.8 MPa in `base_plate`, raw peak 618.1 MPa, reaction total (0, 0, −35,585.77) N and each bolt's reaction |

`lc1_solve.py` no longer builds its own analysis. It calls `assemble`, so the M2.5 solve now runs with the M3.2
retry and quality gate and stops on anything `unverified`.

## 5. What this does not establish

- **One load case, one material.** Only LC1 with the Ti-6Al-4V card was assembled. The material library is M4.8.
- **The deck check is not the solve.** Reaction balance and the all-zero-field guard stay in `lc1_solve.py`;
  moving them into a result parser is M3.4 ([#14](https://github.com/sujitojha1/3d-part-optimization-agent/issues/14)).
- **Bounds only.** The 12 bounds move one parameter at a time; the 64 corners were not assembled.
- **Not run on the D-17 machine.** Counts and timings are from Windows.
- **Other scripts keep their own copies.** `ge_bracket_labels.py` (M2.4) and `lc1_pin_models.py` (M2.2) still
  build their analyses themselves; they are hand-walk records and were left as run.

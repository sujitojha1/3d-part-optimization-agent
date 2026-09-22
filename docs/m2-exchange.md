# ge_bracket LC1 — one real exchange through glc_v5, both ways (M2.7)

| | |
| --- | --- |
| Task | M2.7 ([#50](https://github.com/sujitojha1/3d-part-optimization-agent/issues/50)), absorbing M2.8 ([#51](https://github.com/sujitojha1/3d-part-optimization-agent/issues/51)) · [plan](plan.md) step 7 |
| Date | 2026-09-22 |
| Images | The accepted `REQ-OPT-001` freeze ([record](ge-bracket-contour.md)): `turbo`, 800 × 600, linear 0 → 301 MPa locked, cameras `iso` / `front` / `arm_root`, parallel |
| Field | M2.5's LC1 solve at D-24 `MeshRegion` 2.0 (`out/lc1_solve`) |
| Model | `gemini-3.5-flash-lite` through `glc_v5` `/v1/chat` (router picked `gemini_1`/`gemini_2`), temperature 0, strict JSON schema |
| Script | `scripts/m2_exchange.py` — record in `out/m2_exchange/`, probes in `out/m2_exchange_below/` and `out/m2_exchange_neutral/` |
| Status | **Both questions answered yes; architecture question 1 answered; one disagreement with the pipeline's truth label goes to the owner** — section 4 |

**Measured outside D-17,** on the Windows-AMD64 machine; the gateway and model are the same ones Gate 2b used.

## 1. What was sent

Three conditions, each repeated three times, on the same three images:

| Condition | Prompt |
| --- | --- |
| **A** image only | Part, LC1, allowable, displacement limit, objective (reduce mass); the D-06 labels with one-line descriptions; the six permitted edits with bounds and steps; "stress on the fixed bolt-hole surfaces is a support artifact". Asks for the governing region, whether a support artifact is visible, one edit, and a D-07 prediction |
| **B** image + numbers | A, plus the scalar result: governing max von Mises 435.8 MPa (margin 1.38), raw peak 618.1 MPa flagged as a bolt-hole singularity, max displacement 0.4515 mm, mass 1,198.77 g. **Never** the per-region peaks or the peak's label |
| **C** two turns | Turn 1 asks only for the region claim. Turn 2 gives B's numbers, and asks the model to keep or revise the claim, then for the edit and the prediction |

Plus SimJEB design 148 under LC1, sent twice — at its own full range (Gate 2a's image) and under the
frozen 0 → 301 MPa legend — asking where the concentration is and whether it looks mesh-driven.

## 2. The answers

| | A | B | C turn 1 | C turn 2 |
| --- | --- | --- | --- | --- |
| Region claim | `arm_root_fillet` ×3 | `arm_root_fillet` ×3 | `arm_root_fillet` ×3 | `arm_root_fillet` ×3, `region_revised: false` ×3 |
| Label from the closed set | 3/3 | 3/3 | 3/3 | 3/3 |
| D-07 prediction complete and valid | 3/3 | 3/3 | — | 3/3 |
| Edit within bounds, on step, changed | 3/3 | 3/3 | — | 3/3 |
| Support artifact at the bolt holes seen | 3/3 | 3/3 | 3/3 | 3/3 |

Every call returned a schema-valid answer. The typical exchange is
`arm_root_fillet 5.0 → 5.5`, predicting `{arm_root_fillet, max_vm, down, 0–5% or 5–15%}`.
In the record run, two of the nine edits differ: `arm_thickness 8.0 → 7.5` predicting `max_vm up` (B), and
`arm_root_fillet → 4.5` predicting `max_vm up` (C). Both are coherent pairs of edit and prediction.

**SimJEB 148:** `bolt_holes`, `likely` mesh-driven, under both legends. Right on both counts against
`148field.csv`: the peak, 1,719.3 MPa, is on a bolt-hole surface, a fixed constraint. Worth
knowing: the free surface reaches 1,699.7 MPa, 33 of the top 50 nodes are free surface right beside
the holes, and the frozen legend saturates on 22 % of the part. The model still located the peak
correctly with 22 % of the part saturated.

## 3. Architecture question 1 — the numbers do not move the claim

**0 of 9** region claims moved between A and B, and **0 of 9** between C's two turns, across three
runs (the record, and the two probes in section 4). Issue #51's rule was that "if the numbers move
the claim, the exchange becomes two turns". They did not move it, so a single turn is admissible on this evidence.

**But the numbers are not inert.** In C's turn 2, the model writes the governing number into its own
region claim — *"The maximum governing von Mises stress of 435.8 MPa occurs at the arm_root_fillet
region"* — in **7 of 9** turn-2 answers across the three runs. Nothing in the prompt said where
435.8 MPa is; it is at a `base_plate` node. B's answers never cite a number. So the risk is not the
anchoring §9 feared (the number changing what the model sees). It is the reverse: **the image claim
takes over the number**, and the reason text then asserts something false with a figure attached.

What this means for M2.9's integration spec:

1. Keep the **two-turn** structure anyway. The claim is committed and scoreable before any number is
   shown, which §9 wanted for its own sake, and the cost is small (turn 1 is about 3.9k tokens
   in, 120 out).
2. **The agent's prose never carries a location for a number.** The pipeline's own peak label is the
   record of where the number is (D-06); the model's claim is scored against it, never merged into it.
   `REQ-DEL-004` already keeps prose out of scoring; this adds that prose is not evidence of location either.

## 4. The disagreement: the model says `arm_root_fillet`, the pipeline says `base_plate`

**Region hit is 0 of 36** against M2.5's label. It is not noise: every claim, every run, says the arm root.

**Where the pipeline's governing peak is.** 435.8 MPa sits at (−13.6, −136.6, 0.75) — the wall of
the **underside pocket** beside bolt 3, **17.7 mm from the bolt axis**. The runner-up, 436.9 MPa, is
the same spot beside bolt 2. The LC1 record's support zone is a 10 mm plan radius, so both count as
"outside the support zone". Growing that radius:

| Exclusion radius about each bolt axis | Governing peak | Region |
| --- | --- | --- |
| 10 mm (LC1 record) – 15 mm | 435.8 MPa, pocket wall by bolt 3 | `base_plate` |
| 20 mm | 303.4 MPa, underside by bolt 3 | `base_plate` |
| 25 mm and beyond | **259.3 MPa** | **`arm_root_fillet`** |

So the pipeline's `base_plate` peak is still inside the stress field of a fixed bolt hole, and once
that field is excluded the governing region is the one the model named.

**Two probes rule out the easy explanations:**

- **The frozen cameras cannot see it.** A flat-colour pass puts **0 pixels** of a 3 mm patch round
  either peak in `iso`, `front`, `arm_root` or `top` — every camera looks from above, and the pocket is
  on the underside. Adding an `iso_below` view (70 and 111 pixels on the two peaks) changed nothing:
  **12 of 12 claims still `arm_root_fillet`**, and the model files the red on the pocket wall with the
  bolt-hole artifact (`out/m2_exchange_below`).
- **It is not the camera's name.** The camera `arm_root` is named in the title strip and the prompt.
  With the titles blanked and the cameras called "view 1–3", **12 of 12 claims were still
  `arm_root_fillet`**, with the same reasoning (`out/m2_exchange_neutral`).

**This is a question about the truth label, not about the model.** The model treats everything round a fixed
hole as support artifact, which is what the prompt told it and what an engineer would do. The pipeline
calls anything beyond 10 mm real stress. **One of them has to move before region hit means anything**,
and which one is the owner's decision. It is the same question as the raw-versus-exclusion question already open for
`REQ-VER-002` and D-12 (the M2.5 record's `check.note`):

- **(a) widen the support zone** to about 25 mm for `ge_bracket`, so the pipeline's label agrees with the reading — or
- **(b) keep 10 mm**, and change the prompt to say only the hole surface itself is the artifact, then
  re-run this exchange to see whether the model can then find the pocket wall. That also needs an
  underside camera, which means amending the freeze accepted this morning.

Either way the base-plate hot spot is a real design lever: `base_pocket_depth` is a permitted edit and
it moves exactly that wall. An agent that files it under support artifacts will never pull that lever.

## 5. What else the exchange shows

- **The proposals chase stress, not mass.** 23 of 27 edits across the three runs *add* material
  (`arm_root_fillet` 5.0 → 5.5 or 6.0), although the objective is to reduce mass at a 1.38 margin. Four remove
  some: `arm_thickness 8 → 7.5` twice, `base_thickness 18 → 17.5` once, `arm_root_fillet → 4.5` once. That is a prompt and SKILL question for M2.9, not a transport one.
- **Latency is not small.** Mean 20–47 s per call across conditions, one outlier at 112 s. Two turns per iteration, 8 iterations, is
  on the order of **5–8 min** of wall clock inside D-13's 20, next to the 8.9 min of simulation.
  **D-13 has to count the LLM time as well as the CAM time.** Measured on free-tier keys at 15 rpm, so provisional.
- **Tokens and cost.** About 3.9k tokens in per call with three images (≈ 1.1k per image), 5.0k with
  four; 110–150 out. The record's 14 calls cost **$0.012** in total.
- **Temperature 0 is not deterministic** across repeats (bands and one edit vary), which is expected
  across routed keys, and is why each condition ran three times.

## 6. Exit criterion

Plan §2's M2 exit asks for *"a real exchange that returned a closed-set region label and a complete
D-07 prediction"*. **Met, 36 of 36.** Whether the label is *right* depends on section 4's decision.

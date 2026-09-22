# ge_bracket LC1 — the contour, and whether it is readable (M2.6)

| | |
| --- | --- |
| Task | M2.6 ([#49](https://github.com/sujitojha1/3d-part-optimization-agent/issues/49)) · [plan](plan.md) step 6 |
| Date | 2026-09-22 |
| Field | M2.5's solved LC1 result ([record](ge-bracket-lc1-solve.md)), read from `out/lc1_solve/lc1_solve.FCStd` |
| Labels | M2.4's D-06 surface groups ([record](ge-bracket-labels.md)), which partition the surface exactly |
| Script | `scripts/ge_bracket_contour.py` — `extract`, `study`, `render`, `simjeb` |
| Status | **Settings proposed, not accepted.** The freeze in section 3 is the recommendation; `REQ-OPT-001` is fixed by the owner's eye, not by this script. Two findings go with it: the physically obvious legend **fails**, and the frozen legend **does not transfer** to SimJEB 148 as a constant — sections 4 and 7 |

**Measured outside D-17,** on the same Windows-AMD64 / FreeCAD 1.1.3 machine as
[M2.5](ge-bracket-lc1-solve.md). Nothing here is timing-sensitive, so the D-17 divergence
touches these conclusions less than it touches M2.5's; the rendering stack is pyvista 0.49.0
on VTK, which the D-17 environment also carries.

## 1. The question, and why it is measured rather than eyeballed

The issue asks one narrow thing: at this image size, camera count and colormap, can an
engineer tell `arm_root_fillet` from `clevis_arm` from `bolt_boss`? "It looks fine to me" is
not a setting anyone can re-derive in three weeks, so the judgement rests on two numbers:

- **visibility** — each region's pixel count per camera, from a flat region-id pass with
  lighting off, so a pixel's colour *is* a region id. A region no camera shows cannot be
  judged at all, and that is a camera finding, not a colormap one.
- **separation** — the CIE Lab distance between two regions' median rendered colours, over
  the pixels each region actually occupies. Below ΔE 2.3 two colours are one colour; ΔE 10
  is the floor for "different at a glance". That is the bar.

Neither number replaces looking at the image, and section 5 is the case where looking at it
overturned the number.

## 2. What is being rendered

The surface comes from the D-06 groups, so a triangle's region label still originates at the
geometric predicate (D-04, `REQ-OPT-008`). Each Triangle6 is split into four linear triangles:
its three corners alone read a surface peak of **616.7 MPa** where the solve found **630.6**,
because the corner nodes miss the quadratic mid-side peak. The cache reproduces M2.5's
headline numbers exactly — 630.6 MPa and 0.4516 mm — and `extract` fails if it does not.

| | pin_bore | clevis_arm | arm_root_fillet | base_plate | bolt_boss |
| --- | --- | --- | --- | --- | --- |
| Triangle6 | 1,024 | 3,762 | 2,838 | 9,634 | 660 |
| Surface area, mm² | 957 | 7,122 | 2,093 | 36,384 | 3,223 |
| Median von Mises, MPa | 43.0 | 47.0 | **110.3** | 83.5 | 29.9 |
| 95th percentile, MPa | 136.3 | 146.4 | 242.7 | 155.0 | 281.5 |

**The three judged regions all live in the bottom fifth of the allowable.** That one line is
why this task exists: medians of 110, 47 and 30 MPa against a 602.1 MPa allowable.

## 3. The proposed freeze

| Setting | Value | Why |
| --- | --- | --- |
| Colormap | **`turbo`** | Beats `viridis` and `coolwarm` on separation at every scheme and camera; `coolwarm` fails outright (ΔE 0.7–5.7) |
| Image size | **800 × 600** | Separation is within 1 ΔE of 1600 × 1200 everywhere — resolution is not the binding constraint, the legend is. The cheaper image costs the vision step nothing |
| Legend | **0 → allowable/2, linear, locked** (301 MPa for Ti-6Al-4V) | Section 4. A constant of the material, not of the field, so it is re-derivable for every alloy in D-09's library without a pilot run |
| Camera set | **`iso`, `front`, `arm_root`** | Section 6. Three, not four |
| Projection | **parallel** | Not cosmetic: under perspective, apparent size tracks camera distance, so two iterations would not be comparable even from the same position |

## 4. The legend, which is the whole problem

*Measured at MeshRegion 1.5. Re-run on 22 Sep after D-24 went to 2.0: the ranking is unchanged and the
proposed freeze's worst ΔE (800 × 600, `iso`) moves 9.6 → 9.1 ([walkthrough §5](m2-walkthrough.md#d-24-the-mesh-sizing--applied-at-20)).*

Minimum ΔE over the three judged pairs, `turbo`, 1600 × 1200, worst camera:

| Scheme | Range, MPa | Worst ΔE | Reads |
| --- | --- | --- | --- |
| `allowable` | 0–602.1 | **4.2** | **Fails.** Above the 2.3 JND, far below the glance bar |
| `allowable_half` | 0–301.1 | **9.6** | Marginal at `iso`, clears at `front` (21.3) and `arm_root` (16.6) |
| `p99` | 0–258.9 | 13.2 | Clears everywhere, but the range is a property of the field |
| `log_allowable` | 1–602.1, log | 22.8 | Best number in the study — and rejected, section 5 |

**The obvious choice is the one that fails.** Locking to the allowable is the only scheme whose
colour means something on its own — red is at the limit — and it renders the part as one navy
mass with two bolt-hole spots. The binding pair is `clevis_arm | bolt_boss` at ΔE 4.2: two
regions at 47 and 30 MPa are the same colour when the bar runs to 602.

**The design-relevant discrimination is never the marginal one.** `arm_root_fillet` separates
from both others at ΔE 37.8–80.6 under every scheme. `arm_root_fillet` is a D-06 parameter the
optimiser moves; `clevis_arm` and `bolt_boss` are two quiet regions under LC1. The 9.6 that
makes `allowable_half` marginal is a pair whose confusion costs least.

`p99` is chosen against only because 258.9 MPa is a number this field produced. Locking a run
to it means the range depends on the first solve, and `REQ-OPT-001` exists precisely so the
range does not depend on what was solved.

## 5. Where the metric was wrong

`log_allowable` wins the study by a wide margin — ΔE 22.8 worst-camera against 9.6 — and it
should not be used. Looking at the image says why: on a log bar from 1 MPa, almost the whole
part reads orange to red, and the genuine 598 MPa hot spots are the same orange as an 80 MPa
base plate. A part at 1.35× margin looks like a part about to fail, and the one thing a stress
contour has to do — say where it is hot — is destroyed.

The separation metric measures whether regions are *distinguishable*. It does not measure
whether colour still means *hot*. It is necessary and not sufficient, and a setting chosen on
it alone would have shipped the worst image in the study. Recorded because the next person to
extend the metric needs to know what it does not cover.

## 6. The camera set

Percent of frame each region occupies, 1600 × 1200 (800 × 600 is within 0.06 pp throughout):

| Camera | pin_bore | clevis_arm | arm_root_fillet | base_plate | bolt_boss |
| --- | --- | --- | --- | --- | --- |
| `iso` | 0.49 | 4.18 | 1.38 | 16.46 | 0.75 |
| `front` | **0.00** | 2.89 | 0.57 | 3.64 | 0.69 |
| `top` | **0.00** | 1.82 | 2.96 | 26.30 | **0.00** |
| `arm_root` | 0.39 | 3.51 | 0.85 | 11.71 | 0.89 |

**`top` is dropped: it shows zero `bolt_boss` pixels and zero `pin_bore`.** It is the best view
of `base_plate`, where the governing peak sits, but `iso` and `arm_root` cover that at 16.5 %
and 11.7 %, and a blind camera in a fixed set costs an image per iteration for a view that
cannot answer two of the five region questions.

`top`'s blindness also broke the first version of this study. Scoring the minimum over whatever
pairs were present, `top` scored on one pair instead of three and topped the table at ΔE 96.9.
A row is now scored only when every judged region clears 0.05 % of the frame, and a camera that
cannot see a region is reported rather than rewarded.

## 7. SimJEB 148 — the harder test, and the finding

The issue says to apply the same settings to design 148 across all four load cases, and that a
setting which only reads well on the simple part is a finding. It is one. With the legend frozen
at 0–301 MPa:

| Load case | Median, MPa | 99th pct | Max | **Above the bar** |
| --- | --- | --- | --- | --- |
| `ver` LC1 vertical | 145.0 | 1,030.9 | 1,719.3 | **22.05 %** |
| `hor` LC2 horizontal | 121.6 | 693.7 | 1,225.2 | **17.13 %** |
| `dia` LC3 diagonal | 86.4 | 575.9 | 792.3 | **11.98 %** |
| `tor` LC4 torsion | 31.3 | 221.1 | 364.2 | 0.11 % |

Nearly a quarter of design 148's surface saturates under `ver`, and in the saturated area 302 MPa
and 1,719 MPa are the same dark red. Only the torsion case fits.

**What this does and does not say.** It does not say 301 MPa is the wrong lock for `ge_bracket`
under LC1 — 148 is a different design under SimJEB's own load magnitudes, and the two are not
comparable in absolute MPa. It says **the transferable thing is the rule, not the number**: a bar
anchored at 0 → allowable/2, re-evaluated once per run, where a run is one part, one material and
one load case. A single project-wide MPa constant would have been the natural next simplification
and it would have been wrong.

## 8. What is frozen here and what is not

Settled by measurement, and recorded:

- `turbo` over `viridis` and `coolwarm`; `coolwarm` is unusable for this at any scheme.
- 800 × 600 costs nothing against 1600 × 1200 — resolution is not the binding constraint.
- `top` is blind to two regions and leaves the camera set.
- Parallel projection, on the comparability argument.
- A log legend maximises separation and misreads the part; it is rejected on the image, not the number.

**An owner decision, not settled here:**

- [ ] **The legend rule, 0 → allowable/2 linear.** `REQ-OPT-001`'s render settings are fixed by
      eye in M2 (`requirements.md` section 8). The study says `allowable_half` is marginal at
      `iso` on one quiet pair and `p99` is better by 3.6 ΔE at the cost of depending on the field.
      That trade is the owner's.
- [ ] **Three cameras or four.** Dropping `top` is a cost argument as much as a coverage one.

Neither blocks M2.7, which needs *an* image and a locked range, not the final one.

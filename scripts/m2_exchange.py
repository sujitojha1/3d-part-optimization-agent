"""M2.7: one real exchange through glc_v5, image-only and image-plus-numbers.

Gate 2b proved an image travels. This asks whether the answer that comes back
is usable: does the model name a region from the closed D-06 set, and fill
the D-07 prediction {region, metric, direction, band} unaided? And, for
architecture question 1 (solution-architecture section 9), does the region
claim move when the solver's numbers are in the same prompt?

Three conditions on the same three frozen contours (REQ-OPT-001 as accepted
on 22 Sep: turbo, 800 x 600, linear 0 -> allowable/2, iso / front / arm_root):

- A  image_only      - the pictures and the task, no solver numbers.
- B  image_numbers   - the same prompt with the scalar result appended:
                       governing max_vm, the flagged raw peak, max_disp, mass.
                       Never the per-region peaks or the peak's label, which
                       would hand over the answer the image is meant to give.
- C  two_turn        - turn 1 is A's region claim alone; turn 2 reveals B's
                       numbers and asks for the edit and the prediction, and
                       whether the committed claim should be revised.

Each runs REPEATS times, so a moved claim can be told from sampling noise.
Plus SimJEB design 148 LC1 (issue #50 v0.4): where is the concentration, and
does it look mesh-driven? Sent twice - at its own full range and under the
frozen 0 -> 301 MPa legend - and checked against the nodal field in
data/simjeb/148field.csv.

Truth for ge_bracket is M2.5's record at D-24 region 2.0 (out/lc1_solve):
the governing peak outside the support zone is labelled base_plate. The D-07
prediction is checked for completeness and validity only; scoring it needs
the next evaluation, which is M3's loop.

Run with the FEM environment's Python (Pillow, numpy), after
scripts/ge_bracket_contour.py render --scheme allowable_half --size 800x600
--tag frozen, with glc_v5 serving on GLC_URL (default http://127.0.0.1:8111):
    $FEM_PYTHON scripts/m2_exchange.py [--provider gemini_1] [--repeats 3]

Writes out/m2_exchange/result.json with every request's prompt text, reply,
tokens and latency. Exit 0 when every call returned a schema-valid answer,
2 otherwise.
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parts import ge_bracket as gb  # noqa: E402

GLC_URL = os.environ.get("GLC_URL", "http://127.0.0.1:8111")
OUT = ROOT / "out" / "m2_exchange"
FROZEN = ROOT / "out" / "ge_bracket_contour" / "frozen"
CAMERAS = ("iso", "front", "arm_root")
SOLVE = ROOT / "out" / "lc1_solve" / "result.json"
SIMJEB_CSV = ROOT / "data" / "simjeb" / "148field.csv"
SIMJEB_IMAGES = {
    "native_range": ROOT / "out" / "gate2a" / "148_ver_stress.png",
    "frozen_legend": ROOT / "out" / "ge_bracket_contour" / "simjeb148" / "ver_iso.png",
}
SIZE = (800, 600)

LABELS = ["pin_bore", "clevis_arm", "arm_root_fillet", "base_plate", "bolt_boss", "bulk"]
METRICS = ["max_vm", "max_disp", "mass"]
DIRECTIONS = ["up", "down", "flat"]
BANDS = ["0-5%", "5-15%", "15-30%", ">30%"]

REGION_TEXT = """Regions (closed set; answer with one label exactly):
- pin_bore: the two cylindrical bores in the clevis arms that carry the pin.
- clevis_arm: the two upright lugs/arms around the pin bores.
- arm_root_fillet: the fillets where each arm meets the top of the base plate.
- base_plate: the plate itself - top, bottom, outline walls, pockets, centre hole.
- bolt_boss: the four bolt holes and the rounded lobes of the outline around them.
- bulk: anything not covered above (empty on this part)."""

TASK_TEXT = """You are the analysis step of a design-optimisation agent.

Part: ge_bracket, a Ti-6Al-4V jet-engine bracket - a base plate bolted down at four
holes, with two clevis arms carrying a pin. Load case LC1: 35,585.77 N pulling the pin
vertically (+z); the four bolt holes are fixed. Allowable von Mises 602.1 MPa (yield
903 MPa / safety factor 1.5); displacement limit 0.4957 mm. Objective: reduce mass
while staying inside both limits.

The images are von Mises contours of the current design from {ncams} fixed cameras
({cams}). The colour bar is locked at 0-301 MPa for the whole run, so
anything above 301 MPa saturates at the darkest red.

{regions}

Permitted edits - exactly one parameter per iteration, within bounds, on its step:
{edits}

Stress concentrated on the fixed bolt-hole surfaces is a support artifact; the
pipeline excludes it when it reads the governing stress."""

NUMBERS_TEXT = """Solver result for this design:
- max von Mises outside the support zone: 435.8 MPa (margin 1.38 on 602.1 MPa)
- raw peak von Mises: 618.1 MPa on a fixed bolt-hole face, flagged as a support singularity
- max displacement: 0.4515 mm (limit 0.4957 mm)
- mass: 1,198.77 g"""

ASK_REGION = ("From the images, name the region that holds the stress concentration "
              "governing this design, and say whether you also see a support artifact "
              "at the bolt holes. Give a one-sentence reason.")
ASK_FULL = (ASK_REGION + " Then propose exactly one edit, and predict its effect on the "
            "next evaluation as {region, metric, direction, band}: the region where the "
            "effect shows, the metric that changes most, its direction, and the size band "
            "of the relative change.")
ASK_TURN2 = ("Now the solver's numbers for the same design:\n\n" + NUMBERS_TEXT + "\n\n"
             "Keep or revise your region claim (say which), then propose exactly one edit "
             "and predict its effect on the next evaluation as {region, metric, direction, "
             "band}.")


def edits_text():
    return "\n".join(f"- {name}: baseline {r['baseline']} mm, bounds {r['min']}-{r['max']} mm, "
                     f"step {r['step']} mm" for name, r in gb.PARAMS.items())


def region_schema():
    return {"region": {"type": "string", "enum": LABELS},
            "support_artifact_seen": {"type": "boolean"},
            "reason": {"type": "string"}}


def full_schema(with_revision=False):
    props = dict(region_schema())
    if with_revision:
        props["region_revised"] = {"type": "boolean"}
    props["edit"] = {"type": "object", "properties": {
        "parameter": {"type": "string", "enum": list(gb.PARAMS)},
        "new_value": {"type": "number"}},
        "required": ["parameter", "new_value"], "additionalProperties": False}
    props["prediction"] = {"type": "object", "properties": {
        "region": {"type": "string", "enum": LABELS},
        "metric": {"type": "string", "enum": METRICS},
        "direction": {"type": "string", "enum": DIRECTIONS},
        "band": {"type": "string", "enum": BANDS}},
        "required": ["region", "metric", "direction", "band"], "additionalProperties": False}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


def only_region_schema():
    props = region_schema()
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


SIMJEB_CLASSES = ["bolt_holes", "pin_bore", "free_surface"]
SIMJEB_PROMPT = """This is a finite-element von Mises contour of a jet-engine bracket
(SimJEB design 148) under a vertical pin load, bolted down at its bolt holes, which are
fixed. Where is the highest stress concentration - on the bolt holes, the pin bore, or
the free surface? Does that peak look mesh-driven (a singularity at a constraint or a
sharp corner that would keep rising under refinement) rather than a real, converging
stress? Give a one-sentence reason."""
SIMJEB_SCHEMA = {"type": "object", "properties": {
    "location": {"type": "string", "enum": SIMJEB_CLASSES},
    "mesh_driven": {"type": "string", "enum": ["likely", "unlikely", "cannot_tell"]},
    "reason": {"type": "string"}},
    "required": ["location", "mesh_driven", "reason"], "additionalProperties": False}


def data_url(path, size=SIZE, blank_title=False):
    image = Image.open(path).convert("RGB")
    if image.size != size:
        image = image.resize(size, Image.LANCZOS)
    if blank_title:  # the title strip names the camera; white it out
        image.paste((255, 255, 255), (0, 0, size[0], 30))
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), buf.tell()


def post(body):
    req = urllib.request.Request(GLC_URL + "/v1/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            reply = json.load(resp)
    except urllib.error.HTTPError as e:
        reply = {"http_error": e.code, "detail": e.read().decode(errors="replace")[:2000]}
    except urllib.error.URLError as e:
        reply = {"http_error": None, "detail": str(e)}
    return reply, round(time.perf_counter() - t, 3)


def answer(reply):
    if isinstance(reply.get("parsed"), dict):
        return reply["parsed"]
    text = (reply.get("text") or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def chat(messages, schema, name, provider, max_tokens=600):
    body = {"messages": messages,
            "response_format": {"type": "json_schema", "schema": schema, "name": name,
                                "strict": True},
            "max_tokens": max_tokens, "temperature": 0, "agent": "m2_exchange"}
    if provider:
        body["provider"] = provider
    reply, wall = post(body)
    got = answer(reply)
    call = {"provider": reply.get("provider"), "model": reply.get("model"),
            "input_tokens": reply.get("input_tokens"),
            "output_tokens": reply.get("output_tokens"),
            "latency_ms": reply.get("latency_ms"), "wall_s": wall,
            "cost_usd": (reply.get("cost") or {}).get("total_usd"),
            "text": reply.get("text"), "answer": got,
            "error": reply if "http_error" in reply else None}
    return got, call


def user_turn(text, images):
    return {"role": "user", "content": [{"type": "text", "text": text}] + [
        {"type": "image_url", "image_url": {"url": url}} for url in images]}


def redact(messages):
    """The transcript as sent, with each image replaced by a placeholder."""
    out = []
    for m in messages:
        if isinstance(m["content"], str):
            out.append(m)
            continue
        out.append({"role": m["role"], "content": [
            c if c["type"] == "text" else {"type": "image_url", "image_url": "<png>"}
            for c in m["content"]]})
    return out


def valid_edit(edit):
    r = gb.PARAMS.get(edit.get("parameter"))
    v = edit.get("new_value")
    if r is None or not isinstance(v, (int, float)):
        return False
    on_step = abs((v - r["min"]) / r["step"] - round((v - r["min"]) / r["step"])) < 1e-6
    return r["min"] <= v <= r["max"] and on_step and v != r["baseline"]


def checks(got, truth, full=True):
    c = {"region_in_closed_set": got.get("region") in LABELS,
         "region_hit": got.get("region") == truth}
    if full:
        p = got.get("prediction") or {}
        c["prediction_complete"] = (p.get("region") in LABELS and p.get("metric") in METRICS
                                    and p.get("direction") in DIRECTIONS
                                    and p.get("band") in BANDS)
        c["edit_valid"] = valid_edit(got.get("edit") or {})
    return c


def simjeb_truth():
    header = SIMJEB_CSV.open().readline().strip().split(",")
    cols = [header.index(c) for c in ("surf", "ver_stress")]
    table = np.loadtxt(SIMJEB_CSV, delimiter=",", skiprows=1, usecols=cols)
    surf = table[table[:, 0] != 0]
    klass = {1: "free_surface", 2: "bolt_holes", 3: "pin_bore"}
    order = np.argsort(surf[:, 1])[::-1]
    top = surf[order[:max(1, len(order) // 1000)]]
    free = surf[surf[:, 0] == 1][:, 1]
    peak_class = klass[int(surf[order[0], 0])]
    return {"peak_mpa": round(float(surf[order[0], 1]), 1), "peak_class": peak_class,
            "top_0p1pct_classes": dict(Counter(klass[int(k)] for k in top[:, 0])),
            "free_surface_max_mpa": round(float(free.max()), 1),
            # A peak on the fixed bolt-hole surfaces is a constraint singularity.
            "mesh_driven": "likely" if peak_class == "bolt_holes" else "unlikely"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", help="pin a gateway provider; default: router")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--extra-camera", action="append", default=[],
                        help="probe only: add a camera rendered in out/ge_bracket_contour/probe_below")
    parser.add_argument("--tag", help="write to out/m2_exchange_TAG, so a probe keeps the record")
    parser.add_argument("--skip-simjeb", action="store_true")
    parser.add_argument("--neutral-names", action="store_true",
                        help="probe only: blank the title strip and call the cameras view 1..n")
    args = parser.parse_args()
    cameras = list(CAMERAS) + args.extra_camera

    def image_dir(cam):
        return FROZEN if cam in CAMERAS else FROZEN.parent / "probe_below"

    out = OUT if not args.tag else OUT.with_name(f"{OUT.name}_{args.tag}")
    missing = [p for p in [image_dir(c) / f"{c}.png" for c in cameras]
               + ([] if args.skip_simjeb else list(SIMJEB_IMAGES.values()))
               if not p.exists()]
    if missing:
        sys.exit(f"missing inputs: {missing}")
    out.mkdir(parents=True, exist_ok=True)

    solve = json.loads(SOLVE.read_text())
    truth = solve["result"]["peak_vm_outside_support_zone"]["region"]["label"]
    images = [data_url(image_dir(c) / f"{c}.png", blank_title=args.neutral_names)[0]
              for c in cameras]
    names = ([f"view {i}" for i in range(1, len(cameras) + 1)] if args.neutral_names
             else cameras)
    task = TASK_TEXT.format(regions=REGION_TEXT, edits=edits_text(), ncams=len(cameras),
                            cams=", ".join(names))
    runs = []

    for rep in range(args.repeats):
        for cond, text in (("A_image_only", task + "\n\n" + ASK_FULL),
                           ("B_image_numbers", task + "\n\n" + NUMBERS_TEXT + "\n\n" + ASK_FULL)):
            messages = [user_turn(text, images)]
            got, call = chat(messages, full_schema(), "exchange", args.provider)
            runs.append({"condition": cond, "repeat": rep, "checks": checks(got, truth),
                         "transcript": redact(messages), "calls": [call], "answer": got})

        messages = [user_turn(task + "\n\n" + ASK_REGION, images)]
        got1, call1 = chat(messages, only_region_schema(), "region", args.provider)
        messages += [{"role": "assistant", "content": json.dumps(got1)},
                     {"role": "user", "content": ASK_TURN2}]
        got2, call2 = chat(messages, full_schema(with_revision=True), "exchange", args.provider)
        c = checks(got2, truth)
        c["turn1_region_hit"] = got1.get("region") == truth
        c["turn1_region_in_closed_set"] = got1.get("region") in LABELS
        runs.append({"condition": "C_two_turn", "repeat": rep, "checks": c,
                     "transcript": redact(messages), "calls": [call1, call2],
                     "answer": {"turn1": got1, "turn2": got2}})

    s_truth = simjeb_truth()
    simjeb_runs = []
    for name, path in ({} if args.skip_simjeb else SIMJEB_IMAGES).items():
        url, nbytes = data_url(path)
        messages = [user_turn(SIMJEB_PROMPT, [url])]
        got, call = chat(messages, SIMJEB_SCHEMA, "simjeb", args.provider, max_tokens=300)
        simjeb_runs.append({"image": name, "png_bytes": nbytes, "answer": got,
                            "checks": {"location": got.get("location") == s_truth["peak_class"],
                                       "mesh_driven": got.get("mesh_driven")
                                       == s_truth["mesh_driven"]},
                            "transcript": redact(messages), "calls": [call]})

    def claims(cond, key=lambda r: r["answer"].get("region")):
        return [key(r) for r in runs if r["condition"] == cond]

    region_a = claims("A_image_only")
    region_b = claims("B_image_numbers")
    region_c1 = claims("C_two_turn", lambda r: r["answer"]["turn1"].get("region"))
    region_c2 = claims("C_two_turn", lambda r: r["answer"]["turn2"].get("region"))
    all_calls = [c for r in runs + simjeb_runs for c in r["calls"]]
    schema_ok = all(c["answer"] and not c["error"] for c in all_calls)
    summary = {
        "truth_region": truth, "simjeb_truth": s_truth,
        "region_claims": {"A_image_only": region_a, "B_image_numbers": region_b,
                          "C_turn1": region_c1, "C_turn2": region_c2},
        "claim_moved_A_to_B": [a != b for a, b in zip(region_a, region_b)],
        "claim_moved_C_turn1_to_turn2": [a != b for a, b in zip(region_c1, region_c2)],
        "region_hit_rate": {k: sum(x == truth for x in v) / len(v) for k, v in
                            (("A", region_a), ("B", region_b), ("C1", region_c1),
                             ("C2", region_c2))},
        "prediction_complete": all(r["checks"]["prediction_complete"] for r in runs),
        "edit_valid": all(r["checks"]["edit_valid"] for r in runs),
        "tokens_in_mean": round(np.mean([c["input_tokens"] or 0 for c in all_calls])),
        "latency_ms_mean": round(np.mean([c["latency_ms"] or 0 for c in all_calls])),
        "cost_usd_total": round(sum(c["cost_usd"] or 0 for c in all_calls), 6),
        "models": sorted({f"{c['provider']}:{c['model']}" for c in all_calls}),
        "schema_ok": schema_ok,
    }
    result = {"task": "M2.7", "gateway": GLC_URL, "images": {
        "cameras": cameras, "size": list(SIZE), "source": str(FROZEN.relative_to(ROOT))},
        "summary": summary, "runs": runs, "simjeb": simjeb_runs}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    for r in runs:
        a = r["answer"] if r["condition"] != "C_two_turn" else r["answer"]["turn2"]
        print(r["condition"], r["repeat"], a.get("region"), a.get("edit"), a.get("prediction"),
              "|", a.get("reason"))
    for r in simjeb_runs:
        print("simjeb", r["image"], r["answer"], r["checks"])
    sys.exit(0 if schema_ok else 2)


if __name__ == "__main__":
    main()

"""Gate 2b (M1.5): an image reaches a vision model through glc_v5.

Sends PNGs to the running gateway's /v1/vision route and checks that the
answers could only have come from the pixels:

- nonce: a freshly drawn random code the model cannot guess or recall.
- contour_<w>: the Gate 2a SimJEB design 148 contour at each image size. The
  title's design number and the legend range are in the pixels only, never in
  the prompt.
- chat: the same contour through /v1/chat as an OpenAI-shape image_url block,
  the form a multi-turn agent exchange uses.

Run with the FEM environment's Python for Pillow (scripts/fem_env.py finds
it), after scripts/render_field.py
and with glc_v5 serving on GLC_URL (default http://127.0.0.1:8111):
    $FEM_PYTHON scripts/gate2b_vision.py [--provider gemini]

The gate is transport: every call's `checks` must pass. Each contour call also
asks for the peak's image quadrant and records it under `reading`. That is a
question about how well the model reads a contour (M2.6, M2.7), not whether
the image arrived, so it is reported but does not gate.

Writes out/gate2b/result.json with every request's transcript, tokens and
latency. Exit 0 when every transport check passes, 2 otherwise.
"""

import argparse
import base64
import io
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CONTOUR = ROOT / "out" / "gate2a" / "148_ver_stress.png"
OUT = ROOT / "out" / "gate2b"
GLC_URL = os.environ.get("GLC_URL", "http://127.0.0.1:8111")
WIDTHS = (1600, 800)  # native Gate 2a render, and half size
NONCE_ALPHABET = "ACDEFHJKMNPRTUVWXY34679"  # no look-alikes (0/O, 1/I, 5/S, 8/B)

# Ground truth from Gate 2a: 148_ver_stress.png's legend and title. The LC1
# peak (1,719.3 MPa) sits on the bolt hole at pixel (1165, 855) of 1600 x 1200.
TRUTH = {"design": 148, "legend_max": 1719, "legend_min": 1, "units": "MPa",
         "peak_quadrant": "bottom-right"}
QUADRANTS = ["top-left", "top-right", "bottom-left", "bottom-right"]

CONTOUR_PROMPT = (
    "This is a finite-element stress contour of a bracket. Read it and fill the schema: "
    "the design number in the title, the largest and smallest numbers on the colour bar, "
    "the colour bar's units, and the image quadrant that holds the single highest-stress "
    "(darkest red) spot on the part.")
CONTOUR_SCHEMA = {
    "type": "object",
    "properties": {
        "design": {"type": "integer"},
        "legend_max": {"type": "number"},
        "legend_min": {"type": "number"},
        "units": {"type": "string"},
        "peak_quadrant": {"type": "string", "enum": QUADRANTS},
    },
    "required": ["design", "legend_max", "legend_min", "units", "peak_quadrant"],
    "additionalProperties": False,
}
NONCE_SCHEMA = {"type": "object", "properties": {"code": {"type": "string"}},
                "required": ["code"], "additionalProperties": False}


def png_data_url(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), buf.tell()


def nonce_image(code):
    image = Image.new("RGB", (640, 240), "white")
    font = ImageFont.load_default(size=96)
    ImageDraw.Draw(image).text((320, 120), code, fill="black", font=font, anchor="mm")
    return image


def post(route, body):
    req = urllib.request.Request(GLC_URL + route, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            reply = json.load(resp)
    except urllib.error.HTTPError as e:
        reply = {"http_error": e.code, "detail": e.read().decode(errors="replace")[:2000]}
    return reply, round(time.perf_counter() - t, 3)


def answer(reply):
    """The model's JSON answer: the gateway's parsed output, else the text."""
    if isinstance(reply.get("parsed"), dict):
        return reply["parsed"]
    text = (reply.get("text") or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def record(name, route, reply, wall_s, image_bytes, image_size, got, checks, reading=None):
    return {
        "name": name, "route": route, "ok": bool(checks) and all(checks.values()),
        "checks": checks, "reading": reading, "answer": got,
        "image": {"size": image_size, "png_bytes": image_bytes},
        "provider": reply.get("provider"), "model": reply.get("model"),
        "attempted": reply.get("attempted"),
        "input_tokens": reply.get("input_tokens"), "output_tokens": reply.get("output_tokens"),
        "latency_ms": reply.get("latency_ms"), "wall_s": wall_s,
        "cost_usd": (reply.get("cost") or {}).get("total_usd"),
        "text": reply.get("text"), "error": reply.get("http_error") and reply,
    }


def contour_checks(got):
    return {
        "design": got.get("design") == TRUTH["design"],
        "legend_max": got.get("legend_max") == TRUTH["legend_max"],
        "legend_min": got.get("legend_min") == TRUTH["legend_min"],
        "units": str(got.get("units", "")).strip().lower() == TRUTH["units"].lower(),
    }


def contour_reading(got):
    return {"peak_quadrant": got.get("peak_quadrant") == TRUTH["peak_quadrant"]}


def vision_call(image, prompt, schema, provider):
    url, nbytes = png_data_url(image)
    body = {"image": url, "prompt": prompt, "schema": schema, "max_tokens": 400,
            "temperature": 0, "agent": "gate2b"}
    if provider:
        body["provider"] = provider
    reply, wall = post("/v1/vision", body)
    return reply, wall, nbytes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", help="pin a gateway provider, e.g. gemini; default: router")
    args = parser.parse_args()
    if not CONTOUR.exists():
        sys.exit(f"no contour at {CONTOUR}; run scripts/render_field.py first")
    OUT.mkdir(parents=True, exist_ok=True)
    runs = []

    code = "".join(secrets.choice(NONCE_ALPHABET) for _ in range(6))
    image = nonce_image(code)
    image.save(OUT / "nonce.png")
    reply, wall, nbytes = vision_call(
        image, "Transcribe the code printed in this image exactly.", NONCE_SCHEMA, args.provider)
    got = answer(reply)
    runs.append(record("nonce", "/v1/vision", reply, wall, nbytes, image.size, got,
                       {"code": str(got.get("code", "")).replace(" ", "").upper() == code}))
    runs[-1]["expected"] = code

    contour = Image.open(CONTOUR).convert("RGB")
    for width in WIDTHS:
        image = contour.resize((width, round(contour.height * width / contour.width)),
                               Image.LANCZOS) if width != contour.width else contour
        reply, wall, nbytes = vision_call(image, CONTOUR_PROMPT, CONTOUR_SCHEMA, args.provider)
        got = answer(reply)
        runs.append(record(f"contour_{width}", "/v1/vision", reply, wall, nbytes, image.size,
                           got, contour_checks(got), contour_reading(got)))

    url, nbytes = png_data_url(contour)
    body = {"messages": [{"role": "user", "content": [
                {"type": "text", "text": CONTOUR_PROMPT},
                {"type": "image_url", "image_url": {"url": url}}]}],
            "response_format": {"type": "json_schema", "schema": CONTOUR_SCHEMA,
                                "name": "contour", "strict": True},
            "max_tokens": 400, "temperature": 0, "agent": "gate2b"}
    if args.provider:
        body["provider"] = args.provider
    reply, wall = post("/v1/chat", body)
    got = answer(reply)
    runs.append(record("chat_1600", "/v1/chat", reply, wall, nbytes, contour.size, got,
                       contour_checks(got), contour_reading(got)))

    result = {"ok": all(r["ok"] for r in runs), "gateway": GLC_URL, "truth": TRUTH, "runs": runs}
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    summary = [{k: r[k] for k in ("name", "ok", "provider", "model", "input_tokens",
                                  "latency_ms", "checks", "reading")} for r in runs]
    print(json.dumps({"ok": result["ok"], "runs": summary}, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

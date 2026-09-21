#!/usr/bin/env python3
"""Gate 4 (M1.11): a FreeCAD CAM Job runs headless.

Runs scripts/cam_check.py on each test block in its own FEM-environment
process, the way the L1 capability will call it, and checks the exit code and
the result: the clean block leaves no residual stock, the undercut block does,
and each block writes G-code. Prints the per-step timings.

Usage: python3 scripts/gate4_cam.py [--resolution MM]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fem_env  # noqa: E402

PYTHON = fem_env.python()
EXPECT_RESIDUAL = {"clean": False, "undercut": True}


def run_block(block, resolution):
    proc = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "cam_check.py"), block, "--resolution", str(resolution)],
        capture_output=True, text=True, timeout=600,
    )
    result_file = ROOT / "out" / "gate4" / block / "result.json"
    result = json.loads(result_file.read_text()) if result_file.exists() else {}
    return proc.returncode, result, proc.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resolution", type=float, default=0.25, help="heightmap cell, mm")
    args = parser.parse_args()
    if not PYTHON.exists():
        sys.exit(f"no FEM Python at {PYTHON}; run scripts/setup_fem_env.sh, "
                 f"or point FEM_ENV at a FreeCAD 1.1.3 install")

    failures = []
    for block, expected in EXPECT_RESIDUAL.items():
        code, result, stderr = run_block(block, args.resolution)
        if code != 0 or not result.get("ok"):
            failures.append(f"{block}: exit {code}, {result.get('error') or stderr.strip()[-500:]}")
            continue
        gcode = ROOT / result["gcode_file"]
        if not gcode.exists() or gcode.stat().st_size == 0:
            failures.append(f"{block}: no G-code at {gcode}")
        if result["residual_stock"] != expected:
            failures.append(f"{block}: residual_stock={result['residual_stock']}, expected {expected}")
        t = result["timings_s"]
        print(f"{block:9s} residual {result['residual_volume_mm3']:7.1f} mm3 "
              f"(max {result['max_residual_mm']} mm)  G-code {result['gcode_lines']} lines  "
              f"job+ops {t['job_and_ops']}s  sanity {t['sanity_check']}s  post {t['post_process']}s  "
              f"sim {t['simulate']}s  residual {t['residual']}s  total {t['total']}s")

    if failures:
        print("GATE 4 FAIL\n  " + "\n  ".join(failures))
        sys.exit(1)
    print("GATE 4 PASS")


if __name__ == "__main__":
    main()

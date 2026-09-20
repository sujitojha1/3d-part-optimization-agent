"""The part M2A is locked to, and its frozen source checksums.

M2A locked Bracket_Modified_FVZ on 2026-09-20, replacing Iteration1. Both are
GE-challenge bracket candidates from docs/ge-geometry-comparison.md, in the same
native frame and envelope, but they are lightweighted differently:

  Iteration1            283,730 mm3, one closed shell, no enclosed void. Weight is
                        taken out by open pockets cut up from the underside.
  Bracket_Modified_FVZ  172,106 mm3, two closed shells. The underside is continuous
                        and the weight is taken out by a sealed internal cavity at a
                        uniform 3.17 mm wall, so no tool can reach the interior.

Iteration1 stays selectable so its published results remain reproducible. Set the
environment variable GE_PART to override for a one-off run, e.g.

    GE_PART=Iteration1 vendor/fem-env/bin/python scripts/ge_manual_mesh.py
"""

import os

# stem -> SHA-256 of the frozen source STEP
SOURCES = {
    "GE_Challenge_Bracket": "d34fab379fd6293e862a5db22fe42421e3a32c9ee865706e6fc3ed2b9a5b0dc9",
    "Bracket_Modified_FVZ": "aa9cf67d296938b0dfa2c3af542e40e643568277d09de52c17afd0e9e908e023",
    "Iteration1": "a0ba77206bce822bc607722f07734f6d989a6375992545921921c887e6ea0e0e",
}

# Where each source lives. The SimJEB downloads are frozen originals; the challenge
# solid is ours, built by scripts/ge_challenge_solid.py from FVZ's outer surface.
# Note it is frozen as generated: OCC writes a timestamp into the STEP header, so
# regenerating the file changes its bytes and its checksum must be re-recorded.
SOURCE_DIRS = {"GE_Challenge_Bracket": "ge_manual"}

LOCKED = "GE_Challenge_Bracket"
PART = os.environ.get("GE_PART", LOCKED)
if PART not in SOURCES:
    raise SystemExit(f"GE_PART={PART!r} is not a frozen source; choose from {sorted(SOURCES)}")
SOURCE_SHA256 = SOURCES[PART]
SOURCE_DIR = SOURCE_DIRS.get(PART, "simjeb")

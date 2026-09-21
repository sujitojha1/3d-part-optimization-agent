"""Where the FEM toolchain lives, on the D-17 machine and off it.

D-17 pins the toolchain to vendor/fem-env, the macOS arm64 prefix that
scripts/setup_fem_env.sh builds from env/fem-osx-arm64.lock. The Windows
machine M2.5 runs on has no such prefix: FreeCAD 1.1.3 is a system install
carrying its own Python 3.11, ccx and Gmsh. Both layouts put the binaries in
bin/ and the workbenches in Mod/, so one set of rules covers them.

The vendor prefix wins whenever it exists, so nothing here changes what the
D-17 machine does. Off it, FEM_ENV overrides the search, and otherwise the
running FreeCAD install is used, or a system install is looked up when
FreeCAD is not importable (gate4_cam.py runs under a plain python3).

Callers that record a path should pass it through rel(), which stays
repo-relative on the D-17 machine and prints an absolute path off it.

Script docstrings write the interpreter as $FEM_PYTHON, which is
vendor/fem-env/bin/python under D-17 and the FreeCAD install's bin/python.exe
off it. Run this module to resolve one:

    python scripts/fem_env.py                 print every resolved path
    FEM_PYTHON="$(python scripts/fem_env.py python)"
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "fem-env"

# Where a system FreeCAD lands on Windows, newest install last.
_WINDOWS_GLOBS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
]


def _system_freecad():
    found = []
    for base in _WINDOWS_GLOBS:
        if base.name and base.is_dir():
            found += [p for p in sorted(base.glob("FreeCAD*")) if (p / "Mod" / "Fem").is_dir()]
    return found[-1] if found else None


def home():
    """The prefix holding bin/ and Mod/: vendor/fem-env, or the FreeCAD install."""
    override = os.environ.get("FEM_ENV")
    if override:
        return Path(override)
    if VENDOR.exists():
        return VENDOR
    freecad = sys.modules.get("FreeCAD")
    if freecad is not None:
        return Path(freecad.getHomePath())
    system = _system_freecad()
    if system is not None:
        return system
    return VENDOR  # nothing found; report the D-17 path in the error


def on_d17():
    """True when the pinned vendor/fem-env prefix is the one in use."""
    return home() == VENDOR


def _exe(name):
    """A binary in the prefix, with or without the Windows .exe suffix."""
    plain = home() / "bin" / name
    windows = plain.with_name(f"{name}.exe")
    return windows if not plain.exists() and windows.exists() else plain


def python():
    """The interpreter that has FreeCAD, Fem, Path, gmsh and pyvista."""
    return _exe("python")


def ccx():
    """The CalculiX binary: 2.23 under D-17, 2.22 in the FreeCAD 1.1.3 bundle."""
    return _exe("ccx")


def ccx_writer():
    """FreeCAD's femsolver deck writer, read to check the D-06 label chain."""
    return home() / "Mod" / "Fem" / "femsolver" / "calculix" / "write_mesh.py"


def rel(path):
    """A path for a run record: repo-relative when inside the repo, else absolute."""
    path = Path(path)
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main():
    """Print a resolved path, or every one of them, for use from a shell."""
    paths = {"home": home(), "python": python(), "ccx": ccx(), "ccx_writer": ccx_writer()}
    if len(sys.argv) > 1:
        if sys.argv[1] not in paths:
            sys.exit(f"unknown path {sys.argv[1]}; one of {', '.join(paths)}")
        print(paths[sys.argv[1]])
        return
    print(f"{'d17_met':11} {on_d17()}")
    for name, path in paths.items():
        print(f"{name:11} {path}  {'' if path.exists() else '(missing)'}".rstrip())


if __name__ == "__main__":
    main()

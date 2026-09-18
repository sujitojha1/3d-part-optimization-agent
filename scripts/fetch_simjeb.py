#!/usr/bin/env python3
"""Fetch the SimJEB reference files into the gitignored data/simjeb/.

Downloads the design-148 sample zip and the per-design metadata table from
Harvard Dataverse by pinned file ID, checks each against a pinned SHA-256
(see docs/simjeb-dataset.md section 1), and unzips the sample.

These files are dev-time reference data only. Never commit them: the CAD is
licensed non-commercial by GrabCAD.

Usage: python3 scripts/fetch_simjeb.py [--force]
"""

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

URL = "https://dataverse.harvard.edu/api/access/datafile/{id}"
DEST = Path(__file__).resolve().parent.parent / "data" / "simjeb"

# `format=original` returns the file as uploaded (a CSV, matching Dataverse's
# published MD5) rather than the TSV that Dataverse re-derives on ingest.
FILES = [
    {
        "name": "SimJEB_sample_files.zip",
        "id": 4640735,
        "query": "",
        "sha256": "ce91d436cc29f6c1e51aa7ee7ec6174d054f7d8370006ad15eae97da37c1c62f",
        "unzip": True,
    },
    {
        "name": "all_bracket_metadata.tab",
        "id": 4639239,
        "query": "?format=original",
        "sha256": "e6dae5909c899875112191a0dd80a1bfaa30769e696363f24931831936762dd2",
        "unzip": False,
    },
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(spec: dict, force: bool) -> None:
    path = DEST / spec["name"]
    if path.exists() and not force and sha256(path) == spec["sha256"]:
        print(f"ok      {spec['name']} (cached)")
    else:
        url = URL.format(id=spec["id"]) + spec["query"]
        print(f"fetch   {spec['name']} <- {url}")
        tmp = path.with_suffix(path.suffix + ".part")
        # curl uses the system trust store, which python.org builds of
        # Python do not, so TLS verification works behind proxies too.
        subprocess.run(
            ["curl", "--fail", "--location", "--silent", "--show-error",
             "--retry", "3", "--output", str(tmp), url],
            check=True,
        )
        actual = sha256(tmp)
        if actual != spec["sha256"]:
            tmp.unlink()
            sys.exit(
                f"CHECKSUM MISMATCH for {spec['name']} (Dataverse file {spec['id']})\n"
                f"  expected {spec['sha256']}\n"
                f"  actual   {actual}\n"
                "The upstream file has changed. Do not use it until "
                "docs/simjeb-dataset.md has been rechecked."
            )
        tmp.replace(path)
        print(f"ok      {spec['name']} sha256 verified")

    if spec["unzip"]:
        with zipfile.ZipFile(path) as z:
            z.extractall(DEST)
            print(f"unzip   {len(z.namelist())} files -> {DEST.relative_to(DEST.parents[1])}/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    for spec in FILES:
        fetch(spec, args.force)


if __name__ == "__main__":
    main()

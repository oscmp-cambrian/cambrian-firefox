#!/usr/bin/env python3
"""Bind a reusable image to its toolchain/configuration inputs, not browser code."""
import argparse
import hashlib
import json
from pathlib import Path

INPUTS = (
    "python/mozboot", "python/mach", "python/mozbuild", "taskcluster",
    "build/moz.configure", "build/mach_virtualenv_packages.txt", "moz.configure",
    "cambrian/ci/Dockerfile", "cambrian/ci/install-toolchains.sh",
    "cambrian/ci/mozconfig", "cambrian/ci/toolchain-manifest.py",
)


def fingerprint(root):
    digest = hashlib.sha256()
    for name in INPUTS:
        entry = root / name
        if not entry.exists():
            raise ValueError(f"Missing toolchain input: {name}")
        paths = sorted(entry.rglob("*")) if entry.is_dir() else [entry]
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("write", "check"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path("/opt/firefox-toolchains/builder.json"))
    parser.add_argument("--revision")
    args = parser.parse_args()
    actual = fingerprint(args.root)
    if args.mode == "write":
        args.manifest.write_text(json.dumps({"schema": 1, "source_revision": args.revision,
                                           "inputs_sha256": actual}, indent=2) + "\n")
    else:
        expected = json.loads(args.manifest.read_text())
        if expected.get("schema") != 1 or expected.get("inputs_sha256") != actual:
            raise SystemExit("Builder inputs changed. Run Jenkinsfile.build-image and select its new digest.")
        print("Builder toolchain inputs match this source checkout.")


if __name__ == "__main__":
    main()

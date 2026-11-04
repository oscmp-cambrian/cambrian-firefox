#!/usr/bin/env bash
set -euo pipefail
[[ ${1:-} =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected an exact source revision.' >&2; exit 2; }
python3 cambrian/ci/toolchain-manifest.py write --revision "$1"
git init
git add .
git -c user.name='Builder bootstrap' -c user.email='builder@localhost' commit -qm 'Bootstrap source snapshot'
./mach --no-interactive bootstrap --no-system-changes --application-choice=browser
./mach --no-interactive python -c 'from mozboot.base import BaseBootstrapper; b = BaseBootstrapper(no_interactive=True); b.application = "browser"; b.ensure_rust_modern()'
./mach --no-interactive configure
./mach --no-interactive python --virtualenv build -c 'import sys; print(sys.version)'
python3 cambrian/ci/toolchain-manifest.py check
rustc --version
/opt/firefox-toolchains/clang/bin/clang --version

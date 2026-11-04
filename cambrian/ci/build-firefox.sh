#!/usr/bin/env bash
set -euo pipefail
[[ ${BUILD_JOBS:-4} =~ ^([1-9]|[1-5][0-9]|6[0-4])$ ]] || { echo 'BUILD_JOBS must be 1..64.' >&2; exit 2; }
[[ ${BUILDER_IMAGE:-} =~ @sha256:[0-9a-f]{64}$ ]] || { echo 'BUILDER_IMAGE must use a digest.' >&2; exit 2; }
cd /build/source
python3 cambrian/ci/toolchain-manifest.py check
python3 cambrian/tests/test_launcher.py
python3 cambrian/tests/test_ci.py
./cambrian/build.sh -j"${BUILD_JOBS:-4}"
./mach xpcshell-test netwerk/test/unit/test_host_overrides_pref.js
./mach gtest 'HostOverride.*'
./mach xpcshell-test security/manager/ssl/tests/unit/test_session_resumption.js
./mach xpcshell-test security/manager/ssl/tests/unit/test_ssl_session_cache_pbm_exit.js
revision=$(git rev-parse HEAD)
export CAMBRIAN_PACKAGE_OUTPUT="/build/artifacts/CambrianFirefox-157.0-${revision:0:12}-linux-x86_64.tar.xz"
./cambrian/package.sh
mkdir /build/package
tar -xJf "$CAMBRIAN_PACKAGE_OUTPUT" -C /build/package
python3 cambrian/ci/verify-package.py /build/package/cambrian-firefox
cp /opt/firefox-toolchains/builder.json /build/artifacts/builder.json
cp /build/package/cambrian-firefox/manifest.json /build/artifacts/package-manifest.json
python3 - <<'PYTHON'
import json, os, subprocess
from pathlib import Path
Path('/build/artifacts/build.json').write_text(json.dumps({
    'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'builder_image': os.environ['BUILDER_IMAGE'],
    'jenkins_build_url': os.environ.get('BUILD_URL'),
    'build_jobs': os.environ.get('BUILD_JOBS', '4'),
}, indent=2) + '\n')
PYTHON
cd /build/artifacts
sha256sum "${CAMBRIAN_PACKAGE_OUTPUT##*/}" > "${CAMBRIAN_PACKAGE_OUTPUT##*/}.sha256"

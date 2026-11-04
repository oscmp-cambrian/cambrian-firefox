#!/usr/bin/env bash
set -euo pipefail
: "${BUILDER_IMAGE:?Set the published builder digest}"
[[ $BUILDER_IMAGE =~ @sha256:[0-9a-f]{64}$ ]] || exit 2
mkdir -p artifacts
scratch=$(mktemp -d "${WORKSPACE:-$PWD}/.firefox-ci.XXXXXX")
container=''
cleanup() {
  status=$?
  trap - EXIT
  if [[ -n $container ]]; then
    docker cp "$container:/build/artifacts/." artifacts/ || true
    docker rm -f "$container" >/dev/null || true
  fi
  rm -rf -- "$scratch"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# A shallow local clone supplies real Git provenance without credentials or worktree pointers.
git clone --no-local --depth 1 --no-checkout "file://$PWD" "$scratch/git"
git -C "$scratch/git" remote remove origin
container=$(docker create --init --shm-size=1g \
  -e BUILDER_IMAGE -e BUILD_URL -e BUILD_JOBS "$BUILDER_IMAGE")
docker cp "$scratch/git/.git" "$container:/build/source/.git"
docker start "$container" >/dev/null
docker exec --user root "$container" chown -R builder:builder /build/source
docker exec "$container" git reset --hard HEAD
docker exec "$container" bash cambrian/ci/build-firefox.sh 2>&1 | tee artifacts/build.log

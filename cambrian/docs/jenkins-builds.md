# Native Firefox builds in Jenkins

## Jobs and prerequisites

Create two **Pipeline from SCM** jobs for
`https://github.com/oscmp-cambrian/cambrian-firefox.git`, selecting the reviewed
branch. **Disable lightweight checkout**: Jenkins Git lightweight retrieval
can fetch the full upstream history despite shallow-clone options. Use
`Jenkinsfile.build-image` for the image producer and `Jenkinsfile` for
the browser. Configure Git shallow clone depth 1 and a 60-minute clone timeout:
Firefox is a large repository. Use the existing GitHub read credential, not a
new credential invented by this project. Pipeline scripts remain sandboxed.

The existing `docker-build-agent` needs Bash, Git, Docker CLI and its configured
Docker daemon. The controller performs no native builds. Docker must support
Linux amd64 containers and have verified HTTPS access to Harbor. No daemon socket
is mounted into the compiler container. Source/Git metadata and artifacts travel
through `docker cp`, including when Docker is remote. The compiler runs as the
image's unprivileged `builder` user; a short root `chown` prepares copied source.

Use trusted owner-controlled source jobs. Do not expose Harbor credentials or
this Docker-capable worker to untrusted/fork Jenkinsfiles. Change-request jobs
and automatic branch indexing do not publish or compile; reviewed builds must
be manually started. Build #1 always registers parameters and exits, including when job parameters
were provisioned beforehand. Publication requires a subsequent manual build. No shared-library pin, Dokku deployment,
production bootstrap, or new registry scanning policy is introduced.

Allow several GB for the builder, plus source, Git checkout, temporary source
transfer and native object output. Plan at least 60 GB free and a worker with
4 CPUs and adequate RAM/swap; tune `BUILD_JOBS` for the host. Builds can take over
an hour. The six-hour timeout includes compilation and tests. The compiler
container and its source/object data are removed on completion/failure; no
unrelated images, volumes, databases or workspaces are pruned. Jenkins keeps
10 build logs and artifacts from the last 3 builds. Docker layer caches and
Jenkins checkouts remain subject to normal administrator retention.

## Configuration that must be set

These two jobs are new. The Harbor repository is new; it lives in the existing
`cambrian` project. Confirm existing robot access includes it. **No new credential
IDs are required.** Parameters use the Cambrian registry defaults:

| Parameter | Default / purpose |
| --- | --- |
| `CONTAINER_REGISTRY` | `harbor-proxy.oscmp.com` |
| `CONTAINER_REPOSITORY` | `cambrian/cambrian-firefox-builder` (the build environment, not a runnable browser image) |
| `REGISTRY_PUSH_CREDENTIALS_ID` | Producer: `oscmp-harbor-publisher` |
| `REGISTRY_PULL_CREDENTIALS_ID` | Browser: `oscmp-harbor-deployer` |
| `BUILD_IMAGE_ENABLED` | Producer: true; false skips both building and publishing |
| `PUBLISH_IMAGE_ENABLED` | Producer: true; false only tests Docker image construction |
| `BUILDER_IMAGE_DIGEST` | Browser: **required**, blank initially; paste `sha256:...` from the producer's `builder-image.txt` |
| `BUILD_JOBS` | Browser: 4, accepted range 1..64 |

Registry/repository, credential selectors and the digest can also have explicit
job environment defaults; build parameters take precedence. Environment defaults
must be configured in Jenkins, not merely exported in an operator shell. A
standalone job's parameter form is refreshed from these source/job defaults on
every run; select the desired digest on each build unless a job environment
default is configured. This native job does not use the web consumers' shared
library or its multibranch-params integration.

For lab validation, preconfigure/pass `CONTAINER_REGISTRY=registry.cambrian.test`,
`CONTAINER_REPOSITORY=cambrian/cambrian-firefox-builder`, and credential selectors
`lab-harbor-publisher` / `lab-harbor-puller`. Inspect the logged effective target
before any publish. Never alias the production hostname to the lab. Registry
trust belongs to the Docker daemon; bootstrap downloads use normal verified TLS.
No production credentials or private lab CA are baked into the builder image.

## Publish once, build repeatedly

1. Start the producer manually. Check its effective registry/repository, then
   select both build and publish. It builds from exactly the checked-out Git
   revision, using a source archive (ignored files/secrets are not Docker context).
2. Download `builder-image.txt` from Jenkins artifacts. It contains the repository
   and immutable digest. The tag is `linux-x86_64-<full source SHA>-<build number>`;
   configure Harbor immutable-tag retention to protect published builder versions.
3. Start the browser job with the same registry/repository and the `sha256:...`
   digest. It pulls the prebuilt image, verifies compatibility and builds native
   C++/Rust from the selected branch. It never runs `docker build` or `apt`.
4. Download `CambrianFirefox-157.0-<revision>-linux-x86_64.tar.xz` and its `.sha256`
   from Jenkins artifacts. In the download directory run `sha256sum -c <file>.sha256`,
   then `tar -xJf <file>.tar.xz` and `./cambrian-firefox/firefox`.
   **No login required** for the desktop browser; Jenkins artifact access uses
   your normal Jenkins account. Desktop GTK libraries are still required on the
   machine running the extracted browser.

The producer uses a digest-pinned Ubuntu 24.04 base. Ubuntu packages update when
that image job is rebuilt; package repositories are not snapshot-pinned, so the
same source is not a promise of bit-for-bit identical images. Mozilla bootstrap
selects tools for this Firefox source. Rust is explicitly installed because the
no-system-changes bootstrap alone skips it (issue #3). A configure pass warms
build dependencies before publishing. The final image excludes the bootstrap
source checkout and native object tree. It retains toolchain state/virtualenvs.

The compatibility manifest hashes bootstrap, Mach/mozbuild, taskcluster,
configure inputs, Python site/dependency definitions and the CI image definition. Ordinary browser C++/JS edits reuse
the image. A matching source location `/build/source` preserves warmed Mach
virtualenv paths. A change to those inputs stops compilation with instructions
to publish a new builder. Rebuild periodically for OS/toolchain security updates,
then select and verify the new digest. Old digest selection is an explicit
rollback of build tooling, not an application deployment rollback. Normal builds
may still access upstream package services when Mach requires additional data;
this is not an offline/reproducible-build guarantee.

## Required validation (Agent/CI)

Before integration, run both actual sandboxed Jenkins jobs in the lab. Record
source SHA, image producer build, immutable image digest, browser build and all
result artifacts. Local mocks alone do not qualify Jenkins CPS, credentials,
remote-Docker transfers or Harbor access.

The consumer runs launcher/CI unit checks, native DNS overrides and snapshot
GTests, existing TLS resumption/private-browsing suites, and both packaged-browser
socket-process matrices with real TLS verification. Once the SOCKS feature is
present, it also runs SOCKS4/5, local/remote DNS, both socket-process settings,
IPv6 proxy listener and PAC cases. It exercises the portable launcher and records
a screenshot. Any failed command fails the job; successful reports alone do not
override a failed build. `build.json`, `builder.json`, `package-manifest.json`,
JSON reports, Mozilla logs and checksums accompany the archive.

Also check that automatic/PR runs do not publish, malformed digests fail before
registry access, and a toolchain mismatch fails before compilation. Failure paths
must preserve available logs and remove only the task's compiler container and
temporary Git metadata. GUI use on a desktop is optional; production Harbor
publication is an owner action after review, not a prerequisite for lab acceptance.

## Validation records

[PR #7](https://github.com/oscmp-cambrian/cambrian-firefox/pull/7) records the
implementation's current verification status and exact Jenkins/source/image
results. Required checks remain outstanding until their successful evidence is
recorded there. Future changes require fresh evidence using the steps above.

The builder's source revision can differ from the browser's source revision:
compatibility is determined by the recorded toolchain inputs, while each artifact
records both revisions/digests. This allows browser and documentation changes to
reuse a validated image without hiding which source produced either artifact.

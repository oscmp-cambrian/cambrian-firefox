def value(String key, String fallback) {
  return params.containsKey(key) ? params[key].toString() : (env."${key}" ?: fallback)
}

def run(String kind) {
  def imageJob = kind == 'image'
  def definitions = imageJob ? [
    booleanParam(name: 'BUILD_IMAGE_ENABLED', defaultValue: true,
      description: 'Build the reusable toolchain image on an owner-started build.'),
    booleanParam(name: 'PUBLISH_IMAGE_ENABLED', defaultValue: true,
      description: 'Push the builder to Harbor; requires the existing publisher credential.')
  ] : [
    string(name: 'BUILDER_IMAGE_DIGEST', defaultValue: env.BUILDER_IMAGE_DIGEST ?: '',
      description: 'Required sha256:... from the successful build-image job. Never a mutable tag.'),
    string(name: 'BUILD_JOBS', defaultValue: '4',
      description: 'Parallel compiler jobs (1..64). Reduce for smaller workers.')
  ]
  definitions += [
    string(name: 'CONTAINER_REGISTRY', defaultValue: env.CONTAINER_REGISTRY ?: 'harbor-proxy.oscmp.com',
      description: 'Harbor hostname, optionally with port; no URL scheme.'),
    string(name: 'CONTAINER_REPOSITORY', defaultValue: env.CONTAINER_REPOSITORY ?: 'cambrian/cambrian-firefox-builder',
      description: 'Builder image repository in the existing cambrian Harbor project.'),
    string(name: imageJob ? 'REGISTRY_PUSH_CREDENTIALS_ID' : 'REGISTRY_PULL_CREDENTIALS_ID',
      defaultValue: imageJob ? (env.REGISTRY_PUSH_CREDENTIALS_ID ?: 'oscmp-harbor-publisher') :
        (env.REGISTRY_PULL_CREDENTIALS_ID ?: 'oscmp-harbor-deployer'),
      description: 'Existing Harbor username/password credential; lab jobs must override this.')
  ]
  properties([
    parameters(definitions), disableConcurrentBuilds(),
    buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '3'))
  ])
  if (env.CHANGE_ID || env.BRANCH_NAME?.startsWith('PR-')) {
    echo 'Change-request jobs do not use registry credentials or publish. Run the reviewed source branch in a trusted job.'
    return
  }
  if (currentBuild.getBuildCauses('hudson.model.Cause$UserIdCause').isEmpty()) {
    echo 'Parameters registered. Start this expensive native build manually with the reviewed settings.'
    return
  }
  if (!params.containsKey(imageJob ? 'BUILD_IMAGE_ENABLED' : 'BUILDER_IMAGE_DIGEST')) {
    echo 'Parameters registered. Use Build with Parameters to select the reviewed settings.'
    return
  }
  def registry = value('CONTAINER_REGISTRY', 'harbor-proxy.oscmp.com')
  def repository = value('CONTAINER_REPOSITORY', 'cambrian/cambrian-firefox-builder')
  if (!(registry ==~ /[a-z0-9]+([.-][a-z0-9]+)*(:[0-9]{1,5})?/) ||
      !(repository ==~ /[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)+/)) {
    error('Invalid registry hostname or lowercase repository path.')
  }
  def revision = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
  def image = "${registry}/${repository}"
  def digest = imageJob ? '' : value('BUILDER_IMAGE_DIGEST', '')
  def jobs = imageJob ? '4' : value('BUILD_JOBS', '4')
  if (!imageJob && (!(digest ==~ /sha256:[0-9a-f]{64}/) || !(jobs ==~ /([1-9]|[1-5][0-9]|6[0-4])/))) {
    error('Set BUILDER_IMAGE_DIGEST to sha256:<64 lowercase hex digits> and BUILD_JOBS to 1..64.')
  }
  echo "Effective target: ${image}; source=${revision}; mode=${kind}; builder=${digest}; compiler jobs=${jobs}. No application deployment."
  withEnv(["CONTAINER_REGISTRY=${registry}", "IMAGE_REPOSITORY=${image}",
           "SOURCE_REVISION=${revision}", "BUILD_JOBS=${jobs}",
           "BUILDER_IMAGE=${image}@${digest}",
           "IMAGE_TAG=linux-x86_64-${revision}-${env.BUILD_NUMBER}"]) {
    try {
      timeout(time: 6, unit: 'HOURS') {
        sh 'rm -rf artifacts; mkdir -p artifacts'
        if (imageJob) {
          if (value('BUILD_IMAGE_ENABLED', 'true') != 'true') {
            echo 'Builder creation disabled; nothing will be published.'
            return
          }
          stage('Build reusable toolchain image') {
            sh(script: '''#!/usr/bin/env bash
set -euo pipefail
git archive HEAD | docker build --platform linux/amd64 --progress plain \
  --build-arg SOURCE_REVISION="$SOURCE_REVISION" \
  -f cambrian/ci/Dockerfile -t "$IMAGE_REPOSITORY:$IMAGE_TAG" -
''')
          }
          if (value('PUBLISH_IMAGE_ENABLED', 'true') == 'true') {
            stage('Publish builder to Harbor') {
              withCredentials([usernamePassword(
                credentialsId: value('REGISTRY_PUSH_CREDENTIALS_ID', 'oscmp-harbor-publisher'),
                usernameVariable: 'REGISTRY_USER', passwordVariable: 'REGISTRY_PASSWORD'
              )]) {
                sh(script: '''#!/usr/bin/env bash
set -euo pipefail
set +x
export DOCKER_CONFIG=$(mktemp -d)
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
printf '%s' "$REGISTRY_PASSWORD" | docker login "$CONTAINER_REGISTRY" --username "$REGISTRY_USER" --password-stdin
docker push "$IMAGE_REPOSITORY:$IMAGE_TAG"
docker image inspect "$IMAGE_REPOSITORY:$IMAGE_TAG" --format '{{range .RepoDigests}}{{println .}}{{end}}' | \
  awk -v repository="$IMAGE_REPOSITORY@" 'index($0, repository) == 1 {print}' > artifacts/builder-image.txt
test "$(wc -l < artifacts/builder-image.txt)" -eq 1
cat artifacts/builder-image.txt
''')
              }
            }
          }
        } else {
          stage('Pull pinned toolchain image') {
            withCredentials([usernamePassword(
              credentialsId: value('REGISTRY_PULL_CREDENTIALS_ID', 'oscmp-harbor-deployer'),
              usernameVariable: 'REGISTRY_USER', passwordVariable: 'REGISTRY_PASSWORD'
            )]) {
              sh(script: '''#!/usr/bin/env bash
set -euo pipefail
set +x
export DOCKER_CONFIG=$(mktemp -d)
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
printf '%s' "$REGISTRY_PASSWORD" | docker login "$CONTAINER_REGISTRY" --username "$REGISTRY_USER" --password-stdin
docker pull "$BUILDER_IMAGE"
''')
            }
          }
          stage('Build, test and package Firefox') {
            sh 'bash cambrian/ci/run-container.sh'
          }
        }
      }
    } finally {
      archiveArtifacts(artifacts: 'artifacts/**', allowEmptyArchive: true, fingerprint: true)
      if (imageJob) {
        sh(returnStatus: true, script: 'docker image rm "$IMAGE_REPOSITORY:$IMAGE_TAG"')
      }
    }
  }
}

return this

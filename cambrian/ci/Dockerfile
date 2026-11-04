FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852 AS system
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential python3 python3-venv python3-pip git curl ca-certificates \
    xz-utils unzip zip file pkg-config libgtk-3-dev libdbus-glib-1-dev \
    libasound2-dev libx11-xcb-dev libxt-dev libpulse-dev libdrm-dev libgbm-dev \
    libxrandr-dev libxcomposite-dev libxdamage-dev libegl1-mesa-dev nodejs openssl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 builder \
    && mkdir -p /build/source /build/obj /build/artifacts /opt/firefox-toolchains \
    && chown -R builder:builder /build /opt/firefox-toolchains
ENV MOZBUILD_STATE_PATH=/opt/firefox-toolchains \
    MOZBUILD_ROOT=/opt/firefox-toolchains \
    CARGO_HOME=/opt/firefox-toolchains/cargo \
    RUSTUP_HOME=/opt/firefox-toolchains/rustup-home \
    PATH=/opt/firefox-toolchains/cargo/bin:$PATH \
    MOZCONFIG=/build/source/cambrian/ci/mozconfig \
    MOZ_OBJDIR=/build/obj \
    MOZ_HEADLESS=1
USER builder
WORKDIR /build/source

FROM system AS bootstrap
COPY --chown=builder:builder . /build/source/
ARG SOURCE_REVISION
RUN bash cambrian/ci/install-toolchains.sh "$SOURCE_REVISION"

FROM system AS builder
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/oscmp-cambrian/cambrian-firefox" \
      org.opencontainers.image.revision=$SOURCE_REVISION \
      org.opencontainers.image.title="Cambrian Firefox Linux x86_64 build environment"
COPY --from=bootstrap --chown=builder:builder /opt/firefox-toolchains /opt/firefox-toolchains
CMD ["sleep", "infinity"]

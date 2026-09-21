# Spec 062 spike: a dev container whose terminal is served to a browser.
# Build context is this folder; nothing from the product is copied in.
FROM rust:1-bookworm AS build
WORKDIR /src
COPY server/Cargo.toml server/Cargo.lock* server/
COPY server/src server/src
COPY web web
RUN cd server && cargo build --release

FROM node:22-bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl less vim-tiny procps ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Both CLIs exactly as published; no credentials, no patched login (Decision 3, 9).
RUN npm install -g @anthropic-ai/claude-code @openai/codex && npm cache clean --force

COPY --from=build /src/server/target/release/remote-terminal-spike /usr/local/bin/remote-terminal-spike
COPY entrypoint.sh /usr/local/bin/spike-entrypoint
RUN chmod +x /usr/local/bin/spike-entrypoint \
    && useradd --create-home --uid 10001 --shell /bin/bash dev \
    && mkdir -p /workspace && chown -R dev:dev /workspace /home/dev

USER dev
# Without a UTF-8 locale readline echoes umlauts as octal escapes (spike finding).
ENV LANG=C.UTF-8 \
    SHELL=/bin/bash \
    SPIKE_WORKDIR=/workspace \
    SPIKE_BIND=0.0.0.0:8791
WORKDIR /workspace
EXPOSE 8791
# Home holds ~/.claude and ~/.codex: the personal login lives here, not in the image.
VOLUME ["/home/dev", "/workspace"]
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS http://127.0.0.1:8791/healthz || exit 1
ENTRYPOINT ["spike-entrypoint"]

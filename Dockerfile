# Official LM-Proxy image.
#
# Build:  docker build -t lm-proxy .
# Run:    docker run -p 8000:8000 -v ./config.toml:/app/config.toml --env-file .env lm-proxy
#
# Extra Python packages (e.g. for custom loggers / DB log storage) can be baked in:
#   docker build --build-arg EXTRA_PIP_PACKAGES="lm-proxy-db-connector sqlalchemy psycopg2-binary" -t lm-proxy .

FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml LICENSE README.md ./
COPY lm_proxy ./lm_proxy
RUN pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.13-slim
LABEL org.opencontainers.image.title="LM-Proxy" \
      org.opencontainers.image.description="OpenAI-compatible proxy server for LLM inference (OpenAI, Anthropic, Google, local models)" \
      org.opencontainers.image.source="https://github.com/Nayjest/lm-proxy" \
      org.opencontainers.image.documentation="https://github.com/Nayjest/lm-proxy#readme" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1

ARG EXTRA_PIP_PACKAGES=""

# [all] enables the Anthropic and Google connectors; pyyaml enables YAML config files.
RUN --mount=type=bind,from=build,source=/wheels,target=/wheels \
    pip install --no-cache-dir "$(ls /wheels/lm_proxy-*.whl)[all]" pyyaml \
    && if [ -n "$EXTRA_PIP_PACKAGES" ]; then pip install --no-cache-dir $EXTRA_PIP_PACKAGES; fi

RUN useradd --create-home --shell /usr/sbin/nologin lmproxy \
    && mkdir -p /app/storage \
    && chown -R lmproxy:lmproxy /app
USER lmproxy
WORKDIR /app

EXPOSE 8000
CMD ["lm-proxy", "--config", "/app/config.toml"]

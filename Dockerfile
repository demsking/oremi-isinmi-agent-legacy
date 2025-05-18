#
## Stage 1: Builder
FROM python:3.11-slim AS builder

ENV UV_LINK_MODE=copy

# Set the shell to /bin/bash and enable pipefail
SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --locked --no-install-project --compile-bytecode

# Sync the project
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked

#
## Stage 2: Final
FROM python:3.11-slim

# Set the shell to /bin/bash and enable pipefail
SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

# Copy the environment, but not the source code
COPY --from=builder --chown=oremi:oremi /app/.venv /opt/oremi-isinmi-agent/.venv

# Binaries
COPY bin/* /opt/oremi-isinmi-agent/bin/
RUN chmod +x /opt/oremi-isinmi-agent/bin/*

# Copy application files
COPY models/ /opt/oremi-isinmi-agent/models
COPY server/ /opt/oremi-isinmi-agent/server
COPY pyproject.toml LICENSE DOCUMENTATION.md /opt/oremi-isinmi-agent/

ENV PATH="/opt/oremi-isinmi-agent/bin:$PATH"
ENV PYTHONPATH="/opt/oremi-isinmi-agent:/opt/oremi-isinmi-agent/.venv/lib/python3.11/site-packages"
ENV PYTHONUNBUFFERED="1"
ENV PYTHONDONTWRITEBYTECODE="1"

ENV TZ=UTC

ENV HOST="0.0.0.0"
ENV PORT=7337

# Volumes
VOLUME "/var/cache/oremi-isinmi-agent"
VOLUME "/root/.cache/huggingface"

# Expose the port
EXPOSE 7337

# Execute the application
CMD ["oremi-isinmi-agent"]

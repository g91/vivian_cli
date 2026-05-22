# =============================================================================
# Vivian CLI — Dockerfile
# =============================================================================
# Multi-stage build:
#   builder  — installs Python deps into a venv
#   final    — lean runtime image
#
# Usage (TUI / interactive):
#   docker build -t vivian-cli .
#   docker run -it --rm -v vivian-config:/root/.vivian vivian-cli
#
# Usage (web GUI):
#   docker run -it --rm -p 5000:5000 -v vivian-config:/root/.vivian vivian-cli --web-gui --web-host 0.0.0.0 --no-open-browser
# =============================================================================

ARG PYTHON_VERSION=3.12
ARG VENV_PATH=/opt/venv

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

ARG VENV_PATH

# System packages needed to compile any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install dependencies
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:$PATH"

WORKDIR /build

# Install core runtime deps first (layer-cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "prompt_toolkit>=3.0.0" "httpx>=0.24.0" "rich>=13.0.0"

# Install the package itself (editable so source changes are reflected on bind-mount)
COPY . .
RUN pip install --no-cache-dir -e . --no-deps


# ── Stage 2: final runtime ───────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS final

ARG VENV_PATH

LABEL org.opencontainers.image.title="Vivian CLI" \
      org.opencontainers.image.description="AI-powered terminal assistant with pentesting tools" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/g91/vivian_cli"

# Runtime system packages (git for /commit, /cpr, etc.; curl for health-checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        openssh-client \
        nmap \
    && rm -rf /var/lib/apt/lists/*

# Pull in the venv from builder
COPY --from=builder ${VENV_PATH} ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:$PATH"

# Copy source
WORKDIR /app
COPY --from=builder /build /app

# Config directory — persist across restarts with a named volume
RUN mkdir -p /root/.vivian
VOLUME ["/root/.vivian"]

# Default exposed ports:
#   5000 — web GUI (--web-gui)
#   7979 — desktop web GUI shell (--desktop-gui)
#   7878 — desktop web IDE (--desktop-gui)
EXPOSE 5000 7979 7878

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TERM=xterm-256color \
    NO_COLOR="" \
    VIVIAN_DOCKER=1

# Health-check: only meaningful when running the web GUI
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:5000/ || exit 1

# Default: interactive TUI mode.
# Override CMD in docker-compose or with `docker run ... -- --web-gui ...`
ENTRYPOINT ["python", "-m", "vivian_cli"]
CMD []

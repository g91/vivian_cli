# =============================================================================
# Vivian CLI — Dockerfile
# =============================================================================
# Multi-stage build:
#   builder  — installs Python deps into a venv
#   final    — lean runtime image
#
# Build args:
#   PYTHON_VERSION   Python image tag (default: 3.12)
#   EXTRAS           Comma-separated optional extras to bake in.
#                    Options: dev, parsecvision, dma, all
#                    Default: dev
#                    Example: --build-arg EXTRAS=dev,parsecvision
#
# Usage (TUI / interactive):
#   docker build -t vivian-cli .
#   docker run -it --rm -v vivian-config:/root/.vivian vivian-cli
#
# Usage (web GUI):
#   docker run -it --rm -p 5000:5000 -v vivian-config:/root/.vivian vivian-cli --web-gui --web-host 0.0.0.0 --no-open-browser
#
# Usage (UESDKGen GUI — requires X11 forwarding from host):
#   Linux:   docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix vivian-cli python apps/UESDKGen/UESDKGen.py
#   Windows: set up VcXsrv/WSLg and export DISPLAY before running
# =============================================================================

ARG PYTHON_VERSION=3.12
ARG VENV_PATH=/opt/venv
# Optional feature packs to install in the image (comma-separated)
ARG EXTRAS=dev

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

ARG VENV_PATH
ARG EXTRAS

# Build-time system packages:
#   gcc / libffi-dev / libssl-dev  — C extensions (cryptography, etc.)
#   tk-dev / python3-tk            — tkinter (for GUI apps: UESDKGen)
#   libgl1 / libglib2.0-0          — opencv runtime (parsecvision extra)
#   libjpeg-dev / zlib1g-dev       — Pillow compile deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libssl-dev \
        tk-dev \
        python3-tk \
        libgl1 \
        libglib2.0-0 \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install dependencies
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:$PATH"

WORKDIR /build

# Install core runtime deps first (layer-cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "prompt_toolkit>=3.0.0" "httpx>=0.24.0" "rich>=13.0.0"

# Copy full source, then install package + requested extras
# Shell test avoids empty-bracket error when EXTRAS is unset
COPY . .
RUN if [ -n "${EXTRAS}" ]; then \
        pip install --no-cache-dir -e ".[${EXTRAS}]"; \
    else \
        pip install --no-cache-dir -e .; \
    fi


# ── Stage 2: final runtime ───────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS final

ARG VENV_PATH

LABEL org.opencontainers.image.title="Vivian CLI" \
      org.opencontainers.image.description="AI-powered terminal assistant with pentesting tools" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/g91/vivian_cli"

# Runtime system packages (git for /commit, /cpr, etc.; curl for health-checks)
# python3-tk + libx11-6 + libxext6 support X11-forwarded GUI apps (UESDKGen)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        openssh-client \
        nmap \
        python3-tk \
        libx11-6 \
        libxext6 \
        libxrender1 \
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

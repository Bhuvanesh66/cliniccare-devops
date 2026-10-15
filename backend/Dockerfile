# syntax=docker/dockerfile:1

# ---- build stage: install dependencies into a self-contained virtualenv ----
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r /tmp/requirements.txt \
 && /opt/venv/bin/pip uninstall --yes pip

# ---- runtime stage: only the virtualenv and the application code ----
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime

# Commit SHA from CI; reported by /api/info so a pod can be traced to its source.
ARG GIT_SHA=local

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_SHA=${GIT_SHA}

# pip is only needed at build time. Removing it from the runtime image drops
# the libraries it vendors (urllib3, msgpack, setuptools), which Trivy flagged
# with HIGH CVEs, and leaves no package manager inside the running container.
RUN python -m pip uninstall --yes pip \
 && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Non-root: the process can't modify the image or bind privileged ports.
USER 10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Migrations are not run here: `python -m app.migrate` runs once beforehand
# (compose `migrate` service / Kubernetes init container).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

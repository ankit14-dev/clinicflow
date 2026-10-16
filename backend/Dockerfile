# syntax=docker/dockerfile:1

# ---- build: install dependencies into a self-contained virtualenv ----
FROM python:3.14-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip uninstall -y pip   # not needed at runtime; its vendored urllib3/msgpack carry CVEs

# ---- runtime: only the venv and the app, running as a non-root user ----
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# the base image's own pip is unused too: remove it so it is not shipped (and scanned) in production
RUN python -m pip uninstall -y pip \
    && useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
# apply DB migrations, then start the API (exec: uvicorn becomes PID 1 and gets SIGTERM)
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]

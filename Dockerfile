# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM node:22-bookworm-slim AS signatures
WORKDIR /build
COPY backend/package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev --no-audit --no-fund

FROM python:3.11-slim-bookworm AS python-deps
WORKDIR /build
COPY backend/requirements.txt ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/pip pip install wheel setuptools && pip install --no-build-isolation -r requirements.txt

FROM python:3.11-slim-bookworm AS runtime
ENV TZ=Asia/Shanghai PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" PLAYWRIGHT_BROWSERS_PATH=/opt/browsers \
    HOME=/home/app
COPY --from=python-deps /opt/venv /opt/venv
COPY --from=signatures /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo Asia/Shanghai > /etc/timezone \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY backend/ /app/backend/
COPY --from=signatures /build/node_modules /app/backend/node_modules
COPY --from=frontend /build/dist /app/frontend/dist
COPY LICENSE /app/LICENSE
RUN mkdir -p /app/backend/data && chown -R app:app /app/backend/data /home/app
USER 10001:10001
WORKDIR /app/backend
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=4)"
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]

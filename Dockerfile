# Container image for the web preview, deployed to Azure App Service (see deploy/azure.sh).
# App Service routes to WEBSITES_PORT=8000.
FROM node:22-slim AS dashboard
WORKDIR /build
RUN npm install -g bun@1
COPY web/dashboard/package.json web/dashboard/bun.lock* ./
RUN bun install --frozen-lockfile || bun install
COPY web/dashboard/ ./
RUN bun run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ROOT=/app PYTHONPATH=/app
# opencv-python-headless needs a couple of shared libraries even in its headless build.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src src
COPY web/service web/service
COPY --from=dashboard /build/dist web/dashboard/dist
RUN useradd --uid 10001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "web.service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

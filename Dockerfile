# Un seul service : l'API FastAPI + l'app web (export Expo) servie à la même adresse.
# Build : docker build -t lifeos .   (depuis la racine du dépôt)

# ---------- 1. Export web de l'app mobile ----------
FROM node:20-slim AS web
WORKDIR /mobile
COPY mobile/package.json mobile/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY mobile/ ./
RUN npx expo export --platform web

# ---------- 2. Backend + app web ----------
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /mobile/dist /app/web
ENV WEB_DIR=/app/web
# Render fournit $PORT ; 8000 par défaut en local.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

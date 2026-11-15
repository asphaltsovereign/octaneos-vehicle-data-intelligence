FROM node:22-alpine AS frontend-build
WORKDIR /opt/octaneos/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 OCTANE_ENV=production OCTANE_DEMO=0
WORKDIR /opt/octaneos
COPY backend/requirements-lock.txt ./backend/requirements-lock.txt
RUN pip install --no-cache-dir -r ./backend/requirements-lock.txt && useradd --create-home --uid 10001 sentinel
COPY backend/ ./backend/
COPY --from=frontend-build /opt/octaneos/frontend/dist ./frontend/dist
WORKDIR /opt/octaneos/backend
USER sentinel
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/ready',timeout=8)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

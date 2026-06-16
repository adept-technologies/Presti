# Stage 1 — Build Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY ./frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY ./frontend/ ./
ARG BUILD_CONFIG=production
RUN npx ng build --configuration $BUILD_CONFIG

# Stage 2 - Python Dependencies Builder
FROM python:3.11-slim AS python-builder
WORKDIR /app
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3 - Final Runtime Image
FROM python:3.11-slim
WORKDIR /app

# Copy Python packages and executables from builder (system-wide install so nobody can read them)
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=python-builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy backend code
COPY ./backend .

# Copy frontend build
COPY --from=frontend-build /frontend/dist/lead-gen/browser/ ./static/

# Update PATH
ENV PYTHONPATH=/app
ENV QUART_APP=main.py
ENV QUART_RUN_HOST=0.0.0.0

EXPOSE 5050

# Run as non-root user(user nobody) for security (remediates Semgrep dockerfile.security.missing-user finding)
# Transfer ownership of ONLY the log directory to nobody.
RUN chown -R nobody:nogroup /app/config

USER nobody

CMD ["gunicorn", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5050", "--timeout", "300", "main:app"]
# One container for the whole app: FastAPI serves the API and the built frontend.

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# The official Python image gets each patch release (with its security fixes) promptly;
# uv's python images can lag behind, so uv is copied in instead.
FROM python:3.14-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY pdf.py ./
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist

# One worker: the app keeps its data in memory. Hosts like Render set $PORT and put a
# proxy in front; VISITOR_IP_HEADER says which of its headers holds the visitor's real IP.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

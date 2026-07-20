# Stage 1: build the React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI runtime serving the built frontend
FROM python:3.12-slim AS backend
WORKDIR /app

# setuptools needs app/ present to resolve [tool.setuptools.packages.find],
# so pyproject.toml and the source tree are copied together rather than
# pyproject.toml first for a separate cached dependency layer (the usual
# requirements.txt trick doesn't apply cleanly to an inline pyproject.toml
# dependency list without an extra lock/export step).
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN pip install --no-cache-dir .

COPY --from=frontend-build /frontend/dist ./app/static

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]

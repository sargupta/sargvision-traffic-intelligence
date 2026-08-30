# SARGVISION Traffic Intelligence — API and intelligence loop.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi>=0.115" "uvicorn[standard]>=0.32" "pydantic>=2.9" \
      "polars>=1.17" "duckdb>=1.1" "pyarrow>=18.0" "numpy>=2.0" "scipy>=1.14" \
      "google-genai>=1.0" "httpx>=0.28"

COPY packages/ ./packages/
COPY apps/api/ ./apps/api/
COPY apps/__init__.py ./apps/

# The curated tables are the baseline layer the live engine compares against.
# They are reproducible from scripts/build_analytics.py and are baked in so the
# container has no runtime dependency on object storage.
COPY data/curated/ ./data/curated/

EXPOSE 8080
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

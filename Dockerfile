# SARGVISION Traffic Intelligence — API and intelligence loop.
FROM python:3.12-slim

# Every timestamp this system shows is read by an officer in Siliguri. Cloud
# Run defaults to UTC, which put 10:32 in the header at 16:02 local — a
# five-and-a-half hour error on a screen whose whole job is "what is happening
# now". tzdata is installed because the slim image has no zone database.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=Asia/Kolkata

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
 && ln -snf /usr/share/zoneinfo/Asia/Kolkata /etc/localtime \
 && echo "Asia/Kolkata" > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

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

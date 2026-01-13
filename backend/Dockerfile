FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal; add build tools only if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install -v --no-cache-dir -r /app/requirements.txt

# Copy the FastAPI app package to /app/app so imports like `from app...` work
COPY backend/app /app/app

EXPOSE 8000

# Configure via env:
#   DATASCAN_MONGO_URL=mongodb://datascan-mongo:27017
#   DATASCAN_MONGO_DB=datascan
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]



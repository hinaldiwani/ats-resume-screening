# docker/Dockerfile
#
# Builds the FastAPI application image. Run via docker/docker-compose.yml,
# which also brings up the MySQL service this app depends on.

FROM python:3.11-slim

WORKDIR /app

# System dependencies needed by PyMuPDF/pdfplumber/cryptography at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads logs

EXPOSE 8000

# --workers is left at Uvicorn's default (1) here; docker-compose.yml's
# production profile can override CMD with gunicorn+uvicorn workers for
# multi-process serving (see README's deployment section).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

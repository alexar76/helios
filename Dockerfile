FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY helios/ helios/
COPY templates/ templates/
COPY helios.config.example.yaml ./helios.config.yaml

RUN pip install --no-cache-dir -e .

RUN useradd -r -u 10001 helios
USER helios

ENV HELIOS_DATA_DIR=/data
ENV HELIOS_HTTP_PORT=8791

EXPOSE 8791

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8791/health').read()" || exit 1

CMD ["helios", "serve", "--port", "8791"]

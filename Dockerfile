FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Instala dependencias de servidor e visao, e embute os assets WASM/wheels para execucao offline
RUN pip install --upgrade pip \
    && pip install -e ".[server,vision]" \
    && python src/viodigital/build_static.py \
    && rm -rf /app/dist /app/build \
    && test -f src/viodigital/web/static/vendor/pyodide/pyodide.js \
    && test -f src/viodigital/web/static/vendor/pyodide/pyodide.asm.wasm \
    && test -f src/viodigital/web/static/vendor/zxing/zxing_reader.wasm \
    && test -f src/viodigital/web/static/vendor/pdfjs/pdf.min.js \
    && ls src/viodigital/web/static/wheels/viodigital-*.whl >/dev/null


FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="VioDigital" \
      org.opencontainers.image.description="Verificador e decodificador offline de documentos oficiais brasileiros (CRLV-e, CNH, ATPV-e, CIN e +160 templates Serpro/VIO)" \
      org.opencontainers.image.url="https://vioweb.vercel.app" \
      org.opencontainers.image.source="https://github.com/Kauerc10/VioDigital" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Bibliotecas compartilhadas de runtime exigidas por opencv-python-headless / PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system viodigital \
    && useradd --system --gid viodigital --create-home --home-dir /home/viodigital viodigital

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=viodigital:viodigital /app /app

USER viodigital

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]

CMD ["uvicorn", "viodigital.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

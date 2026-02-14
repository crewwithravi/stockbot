FROM python:3.11-slim

WORKDIR /app

RUN useradd -r -m -s /bin/false stockbot && \
    mkdir -p /home/stockbot/.local/share/crewai && \
    chown -R stockbot:stockbot /home/stockbot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app/ .
COPY static/ static/

RUN mkdir -p /app/data && chown -R stockbot:stockbot /app

USER stockbot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "300", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]

FROM python:3.11-slim

WORKDIR /app

# Install deps first — cached layer reused when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude venv, .env, tests via .dockerignore)
COPY app/ ./app/
COPY migrations/ ./migrations/

# Run as non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

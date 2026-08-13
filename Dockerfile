FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr,
# so logs are flushed immediately for `docker logs` / `kubectl logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 5000

# Run with gunicorn for a production-style process; still binds 0.0.0.0:5000.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:create_app()"]

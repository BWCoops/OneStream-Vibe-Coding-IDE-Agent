FROM python:3.12-slim

WORKDIR /app

COPY services/data-orchestration/pyproject.toml .
RUN pip install --no-cache-dir .

COPY services/data-orchestration/ .

EXPOSE 8084

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8084"]

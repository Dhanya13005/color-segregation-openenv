FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Defaults — real secrets come from HF Space Secrets at runtime
ENV FASTAPI_PORT=7860
ENV DEBUG=false
ENV API_BASE_URL=https://api.openai.com/v1
ENV MODEL_NAME=gpt-4.1-mini
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/api/status || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
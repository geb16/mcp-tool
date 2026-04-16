FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY src ./src
COPY .env.example ./.env.example

EXPOSE 8080

CMD ["python", "-m", "enterprise_mcp.mcp.http_server"]
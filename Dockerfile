FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY data/ data/
RUN pip install --no-cache-dir ".[api]"
ENV PYTHONPATH=/app/src
EXPOSE 8100
CMD ["uvicorn", "reportanalyst.api.main:app", "--host", "0.0.0.0", "--port", "8100"]

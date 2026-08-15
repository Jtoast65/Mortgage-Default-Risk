FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source, committed artifacts, and the deployed model (data/ is gitignored, not copied).
COPY src/ ./src/
COPY api/ ./api/
COPY artifacts/ ./artifacts/
COPY models/ ./models/

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

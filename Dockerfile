FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
# build-essential and curl are needed for compiling certain python packages (like bcrypt/chromadb)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# The default command runs the Uvicorn server.
# Note: For Celery, you would override the command in your docker-compose or deployment setup:
# CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "-Q", "ingestion"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

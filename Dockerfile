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

ENV PORT=8080
ENV HOST=0.0.0.0
ENV ANONYMIZED_TELEMETRY=False

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

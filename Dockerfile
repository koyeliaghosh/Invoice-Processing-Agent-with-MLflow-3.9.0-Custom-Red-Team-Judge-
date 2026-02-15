FROM python:3.11-slim

# Install system dependencies required for compilation (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model explicitly
RUN python -m spacy download en_core_web_sm

# Copy application source code
COPY src/ src/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port 8080 for Cloud Run
ENV PORT 8080
EXPOSE 8080

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "src.app:app"]

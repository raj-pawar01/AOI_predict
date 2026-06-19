# Use an official lightweight Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV OMP_NUM_THREADS=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies (plus gunicorn for production)
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . .

# Expose the application port
EXPOSE 7860

# Start Flask using gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 app:app"]

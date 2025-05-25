# eidbi-query-system/backend/Dockerfile

# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Add the current directory to Python path for imports to work
ENV PYTHONPATH=/app

# Install system dependencies if needed (e.g., for certain libraries)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
# Make sure .dockerignore excludes venv, __pycache__, etc.
COPY . .

# Cloud Run sets the PORT environment variable automatically
ENV PORT 8080

# Make port available to the world outside this container
EXPOSE ${PORT}

# Run the application using Uvicorn
# exec allows signals to be passed correctly
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} 
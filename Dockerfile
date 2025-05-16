# Root Dockerfile for EIDBI Query System Backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy requirements file from backend directory
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Cloud Run sets the PORT environment variable
ENV PORT 8080
EXPOSE ${PORT}

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} 
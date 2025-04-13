# eidbi-query-system/frontend/Dockerfile

# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit application code
COPY . .

# Expose the port Streamlit runs on (default is 8501)
EXPOSE 8501

# Define environment variable for the port (Cloud Run uses this)
# Streamlit also uses SERVER_PORT
ENV PORT 8501
ENV SERVER_PORT 8501

# Health check (optional but recommended for Cloud Run)
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s \
    CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

# Run the Streamlit application
# Use --server.port and --server.address to bind correctly
CMD exec streamlit run streamlit_app.py --server.port ${PORT} --server.address=0.0.0.0 --server.enableCORS false 
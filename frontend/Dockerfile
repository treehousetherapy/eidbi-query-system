# Dockerfile for EIDBI Query System Frontend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port Streamlit will run on
ENV PORT=8501
EXPOSE ${PORT}

# Command to run the application
CMD streamlit run streamlit_app.py --server.port=${PORT} --server.address=0.0.0.0 
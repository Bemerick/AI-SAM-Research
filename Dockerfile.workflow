# Workflow Job Dockerfile for Nightly SAM.gov Processing
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY app/ ./app/
COPY run_end_to_end_workflow.py .

# Default command runs the workflow for today's date
CMD ["python", "run_end_to_end_workflow.py"]

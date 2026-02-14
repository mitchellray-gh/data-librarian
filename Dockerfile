FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY examples/ ./examples/

# Install the package
RUN pip install -e .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "data_librarian.interface.api:app", "--host", "0.0.0.0", "--port", "8000"]

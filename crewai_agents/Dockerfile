FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy project definition
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY . .

# Set python path
ENV PYTHONPATH=/app/src

# Expose API port
EXPOSE 8002

# Run API
CMD ["python", "api.py"]

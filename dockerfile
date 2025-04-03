# Use a lightweight Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \  # Only need client libs, not the server
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Create and activate a virtual environment
RUN python3 -m venv /app/venv

# Install Python dependencies
RUN /app/venv/bin/pip install --no-cache-dir -r ./setup/requirements.txt

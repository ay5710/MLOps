# Use a lightweight Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies (combined into a single RUN to reduce layers)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    unzip \
    wget \
    gnupg \
 && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
 && apt-get update && apt-get install -y google-chrome-stable \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for better layer caching)
COPY ./setup/requirements.txt /app/setup/

# Install Python dependencies directly (no virtual environment needed in Docker)
RUN pip install --no-cache-dir -r ./setup/requirements.txt

# Copy the rest of the application
COPY . /app

# Copy a template .env file (the OpenAI token should be injected at runtime)
COPY ./setup/.env.template /app/.env

# Make necessary scripts executable
RUN chmod +x /app/main.py /app/scheduler.py /app/setup/db_init.py

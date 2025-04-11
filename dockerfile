# Use a lightweight Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    tzdata \
    curl \
    wget \
    gnupg \
    unzip \
    postgresql-client \
    build-essential \
 && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
 && apt-get update && apt-get install -y google-chrome-stable \
 && rm -rf /var/lib/apt/lists/* /root/.cache/*

# Set timezone
RUN ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime && echo "Europe/Paris" > /etc/timezone
RUN echo "Verifying timezone during build:" && date

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set workdir
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies via Poetry (without venv)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy a template .env file in the root directory
COPY ./setup/.env.template /app/.env

# Make the scripts executable
RUN chmod +x /app/main.py /app/scheduler.py /app/setup/db_init.py

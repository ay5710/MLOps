# Use a lightweight Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    postgresql \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Create and activate a virtual environment
RUN python3 -m venv /app/venv

# Install Python dependencies
RUN /app/venv/bin/pip install --no-cache-dir -r ./setup/requirements.txt

# Use bash explicitly
SHELL ["/bin/bash", "-c"]

# Set static environment variables
ENV DB_NAME="MLOps-db" \
    DB_USER="MLOps-user" \
    DB_HOST="localhost"

# Generate a random password and store in .env file
RUN DB_PASSWORD=$(openssl rand -hex 16) && \
    echo "DB_PASSWORD=$DB_PASSWORD" > /app/.env && \
    echo "DB_NAME=$DB_NAME" >> /app/.env && \
    echo "DB_USER=$DB_USER" >> /app/.env && \
    echo "DB_HOST=$DB_HOST" >> /app/.env && \
    echo "OPENAI_API_KEY=" >> /app/.env && \
    echo "AWS_ACCESS_KEY_ID=" >> /app/.env && \
    echo "AWS_SECRET_ACCESS_KEY=" >> /app/.env && \
    echo "AWS_SESSION_TOKEN=" >> /app/.env && \
    echo "AWS_S3_ENDPOINT=" >> /app/.env && \
    echo "AWS_DEFAULT_REGION=" >> /app/.env

# Expose PostgreSQL port
EXPOSE 5432

# Initialize PostgreSQL and create the user & database
RUN mkdir -p /var/lib/postgresql/data && chown -R postgres:postgres /var/lib/postgresql
USER postgres
RUN initdb -D /var/lib/postgresql/data && \
    pg_ctl -D /var/lib/postgresql/data -l logfile start && \
    DB_PASSWORD=$(grep DB_PASSWORD /app/.env | cut -d '=' -f2) && \
    psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" && \
    psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Switch back to root user
USER root

# Run both scripts at container startup
CMD ["/bin/bash", "-c", "/app/venv/bin/python setup/db_init.py && /app/venv/bin/python scheduler.py"]

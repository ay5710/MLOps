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

# Install Python dependencies
RUN pip install --no-cache-dir python-dotenv -r ./setup/requirements.txt

# Ensure environment variables are available to Python
ENV DB_NAME="" \
    DB_USER="" \
    DB_PASSWORD="" \
    DB_HOST="" \
    OPENAI_API_KEY="" \
    AWS_ACCESS_KEY_ID="" \
    AWS_SECRET_ACCESS_KEY="" \
    AWS_SESSION_TOKEN="" \
    AWS_S3_ENDPOINT="" \
    AWS_DEFAULT_REGION=""

# Create the .env file inside the container
RUN echo "DB_NAME=$DB_NAME" >> /app/.env && \
    echo "DB_USER=$DB_USER" >> /app/.env && \
    echo "DB_PASSWORD=$DB_PASSWORD" >> /app/.env && \
    echo "DB_HOST=$DB_HOST" >> /app/.env && \
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> /app/.env && \
    echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" >> /app/.env && \
    echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> /app/.env && \
    echo "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN" >> /app/.env && \
    echo "AWS_S3_ENDPOINT=$AWS_S3_ENDPOINT" >> /app/.env && \
    echo "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION" >> /app/.env

# Run the application
CMD ["sh", "-c", "source virtualenv/bin/activate && python scheduler.py"]

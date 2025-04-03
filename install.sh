#!/bin/bash


# Install PostgreSQL
echo "Installing PostgreSQL..."
sudo apt install postgresql

## Configure PostgreSQL
echo "Configuring PostgreSQL..."

DB_PASSWORD=$(openssl rand -base64 12)  # Random password
DB_NAME="MLOps-db"
DB_USER="MLOps-user"
DB_HOST="localhost"

sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";"
sudo -u postgres psql -c "CREATE USER \"$DB_USER\" WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"

## Save credentials to a .env file
echo "Saving database configuration..."
cat > .env << EOL
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=$DB_HOST
EOL


# Install Chrome
echo "Installing Chrome..."
chmod +x ./setup/chrome.sh && ./setup/chrome.sh


# Install Python and dependencies within a virtual environment
echo "Installing Python..."
sudo apt-get -y update
sudo apt-get install -y python3 python3-pip python3-venv
sudo python3 -m pip install --upgrade pip

echo "Creating a venv..."
python3 -m venv MLOps
source MLOps/bin/activate

echo "Installing Python depencies..."
pip install -r ./setup/requirements.txt


# Creating the tables and restoring backup
python -m setup.db_init


# Get OpenAI token and save to the .env file
echo "Please enter OpenAI token:"
read -s TOKEN
echo "Token received."
echo "OPENAI_API_KEY=$TOKEN" >> .env
echo "Token added to configuration file."


# Launch the scheduler
python scheduler.py &

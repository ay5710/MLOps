#!/bin/bash

# Install Chrome
echo "Installing Chrome..."
chmod +x ./setup/chrome.sh && ./setup/chrome.sh

# Install Python and dependencies within a virtual environment
echo "Installing Python..."
apt-get -y update
apt-get install -y python3 python3-pip python3-venv
python3 -m pip install --upgrade pip

echo "Creating a venv..."
python3 -m venv virtualenv
source virtualenv/bin/activate

echo "Installing Python depencies..."
python3 -m pip install --upgrade pip
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

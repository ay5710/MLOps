#!/bin/bash


# Install Chrome
echo "Installing Chrome..."
sudo apt install -y wget gnupg

# Download Google's signing key using the newer method
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor | sudo tee /usr/share/keyrings/google-chrome.gpg > /dev/null

# Add Chrome repository using the newer method with signed-by option
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Update package lists with the new repository
sudo apt update

# Install Google Chrome and verify installation
sudo apt install -y google-chrome-stable
google-chrome --version
echo "Google Chrome has been installed successfully!"


# Install Python and dependencies within a virtual environment
echo "Installing Python..."
sudo apt-get -y update
sudo apt-get install -y python3 python3-pip python3-venv
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
# python scheduler.py &

#!/bin/bash

# Update package lists
sudo apt update

# Install dependencies
sudo apt install -y wget gnupg

# Download Google's signing key using the newer method
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor | sudo tee /usr/share/keyrings/google-chrome.gpg > /dev/null

# Add Chrome repository using the newer method with signed-by option
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Update package lists again with the new repository
sudo apt update

# Install Google Chrome
sudo apt install -y google-chrome-stable

# Verify installation
google-chrome --version

echo "Google Chrome has been installed successfully!"
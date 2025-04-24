#!/bin/bash
set -e

echo "Pulling latest changes..."
git pull

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing/updating dependencies..."
pip install -r requirements.txt

echo "Restarting the bot..."
pm2 restart changify-bot

echo "Update completed successfully!"
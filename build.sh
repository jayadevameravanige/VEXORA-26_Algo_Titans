#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Frontend dependencies and build
cd react-frontend
npm install
npm run build

# Go back to root
cd ..

# Create the folder where Flask expects static files
mkdir -p frontend

# Move built files to the frontend folder
cp -r react-frontend/dist/* frontend/

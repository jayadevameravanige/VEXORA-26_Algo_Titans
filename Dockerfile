# --- Stage 1: Build the React Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/react-frontend
COPY react-frontend/package*.json ./
RUN npm install
COPY react-frontend/ ./
RUN npm run build

# --- Stage 2: Final Production Image ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (needed for pandas/sklearn/psycopg2)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask API
COPY api/ /app/api/
COPY ml/ /app/ml/
COPY voter_data.csv /app/  

# Copy the built React app from Stage 1 to the 'frontend' folder
# This matches the '../frontend' path in your api/app.py
COPY --from=frontend-builder /app/react-frontend/dist /app/frontend

# Expose the port Flask/Gunicorn will run on
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=api/app.py
ENV PYTHONUNBUFFERED=1

# Run the application with Gunicorn
# Using 4 workers for better performance
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "api.app:app"]

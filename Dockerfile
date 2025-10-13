# Use a slim Python base image
FROM python:3.10

# Set workdir
WORKDIR /app

# Install system dependencies required by psycopg2 and PyMuPDF (fitz)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    pkg-config \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source
COPY . /app

# Expose port
EXPOSE 5000

# Run Flask app
CMD ["python", "app.py"]
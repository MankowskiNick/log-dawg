FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ssh \
    curl \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/src/ ./src/
COPY backend/config/ ./config/
COPY README.md .

# Create directories for reports, repository, and logs
RUN mkdir -p reports repo logs

# Create non-root user for security
RUN useradd -m -u 1000 logdawg && \
    chown -R logdawg:logdawg /app

USER logdawg

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]

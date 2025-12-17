# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install SQLite runtime library
RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Cloud Run sets PORT environment variable automatically
# Default to 8080 if not set (Cloud Run standard)
ENV PORT=8080

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Run the application with production settings
# Use PORT environment variable for Cloud Run compatibility
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2

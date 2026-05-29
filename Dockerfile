# AutoClip Dockerfile
# Build backend service image

FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependency files
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -r autoclip && useradd -r -g autoclip autoclip

# Remove build tools to reduce image size
RUN apt-get remove -y build-essential && apt-get autoremove -y && apt-get clean

# Copy project files
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY *.sh ./
COPY env.example .env
COPY docker-entrypoint.sh ./

# Create necessary directories
RUN mkdir -p data/projects data/uploads data/temp data/output logs

# Set permissions
RUN chown -R autoclip:autoclip /app
RUN chmod +x *.sh
RUN chmod +x docker-entrypoint.sh
RUN chmod -R 755 data logs

# Switch to non-root user
USER autoclip

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Startup command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

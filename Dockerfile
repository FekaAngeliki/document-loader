# Banking-Grade Document Loader with Web Service
FROM python:3.11-slim

# Banking security requirements
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Skip system dependencies due to corporate SSL issues

# Copy merged requirements first for better caching
COPY requirements.txt ./requirements.txt

# Install Python dependencies with SSL workaround
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""

RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY web_service/ ./web_service/
# Environment variables should be provided at runtime via container orchestration

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user (banking security requirement)
USER appuser

# Health check disabled due to curl dependency and corporate SSL issues
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Expose port
EXPOSE 8080

# Set working directory for web service
WORKDIR /app/web_service

# Run web service
CMD ["python", "-m", "app.main"]
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install UV for dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -r uv.lock

# Copy source code
COPY . .

# Install the package
RUN uv pip install --system -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port (if needed for web interface)
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["document-loader"]
# Use Python 3.13 as base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./
COPY server.py ./
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY prompts/ ./prompts/
COPY staticFiles/ ./staticFiles/

# Install dependencies using uv
RUN uv sync --frozen

# Expose port for HTTP transport
EXPOSE 8000

# Run MCP server (direct execution to use HTTP config from server.py)
CMD ["uv", "run", "python", "server.py"]


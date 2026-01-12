FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install the package in editable mode with dev dependencies
RUN uv sync --all-groups \
    && rm -rf /root/.cache/uv \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

# Set up pre-commit hooks (optional, will be set up when first run)
RUN git config --global --add safe.directory /workspace || true

CMD ["/bin/bash"]

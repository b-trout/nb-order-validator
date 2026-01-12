FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with sudo privileges
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set working directory
WORKDIR /workspace

# Change ownership of the workspace
RUN chown -R $USERNAME:$USERNAME /workspace

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY .git/ ./.git/

# Install the package in editable mode with dev dependencies
RUN uv sync --all-groups \
    && rm -rf /root/.cache/uv \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

# Switch to non-root user
USER $USERNAME

# Set up git safe directory for the user
RUN git config --global --add safe.directory /workspace || true

CMD ["/bin/bash"]

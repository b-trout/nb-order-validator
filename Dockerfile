FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Build arguments for version and user
ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0
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
COPY --chown=$USERNAME:$USERNAME pyproject.toml ./
COPY --chown=$USERNAME:$USERNAME .pre-commit-hooks.yaml ./
COPY --chown=$USERNAME:$USERNAME README.md ./
COPY --chown=$USERNAME:$USERNAME src/ ./src/
COPY --chown=$USERNAME:$USERNAME tests/ ./tests/

# Switch to non-root user before installation
USER $USERNAME

# Install the package in editable mode with dev dependencies
# Use SETUPTOOLS_SCM_PRETEND_VERSION to set version without .git directory
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_NB_ORDER_VALIDATOR=${SETUPTOOLS_SCM_PRETEND_VERSION}
RUN uv sync --all-groups \
    && rm -rf ~/.cache/uv

# Set up git safe directory for the user
RUN git config --global --add safe.directory /workspace || true

CMD ["/bin/bash"]

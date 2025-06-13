FROM python:3.11-slim-bullseye

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Install curl & git
RUN apt update && apt install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=devcontainer
ARG USER_UID=1001
ARG USER_GID=1001

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME --shell /bin/bash
USER $USERNAME

# Install Node.js
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
    && export NVM_DIR="$HOME/.nvm" \
    && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" \
    && nvm install 20

FROM python:3.11-slim-bullseye

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Install curl & git
RUN apt update && apt install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

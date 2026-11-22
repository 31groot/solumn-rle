FROM python:3.11.9-slim

# tmux/asciinema: terminal tooling for the agent harness (network is off at run time).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest==8.3.3 PyYAML==6.0.2

COPY certs/sandbox-root-ca.crt /usr/local/share/ca-certificates/sandbox-root-ca.crt
RUN update-ca-certificates

WORKDIR /app
COPY app/ /app/

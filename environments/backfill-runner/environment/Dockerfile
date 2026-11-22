FROM python:3.11.9-slim

# tmux/asciinema: terminal tooling for the agent harness (network is off at run time).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema curl procps cron sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest==8.3.3

WORKDIR /app
COPY app/ /app/
RUN python3 db.py data/app.db && python3 migrate.py

FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATABASE_PATH=/var/data/chatops.sqlite3

WORKDIR /app

# Install the Python dependencies first so Docker can reuse this layer when
# only application code changes. Install the Chromium build that matches the
# Playwright version in requirements.txt, along with its Linux dependencies.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Keep the UI test suite in the image; the Slack command runner executes it.
COPY . .

RUN mkdir -p /var/data

EXPOSE 10000

# Render supplies PORT. The fallback makes the image straightforward to run
# locally with Docker as well.
CMD ["sh", "-c", "exec python -m uvicorn chatops_qa.app:app --host 0.0.0.0 --port ${PORT:-10000}"]

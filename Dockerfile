FROM python:3.11-slim

# System deps for Playwright and scraping
RUN apt-get update && apt-get install -y \
    git \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install chromium

# Copy project
COPY . .

# Create output and log dirs
RUN mkdir -p _outputs/digital_products _outputs/web_hunter _outputs/youtube _logs

ENV PYTHONUNBUFFERED=1

CMD ["python", "scheduler.py"]

FROM python:3.11-slim

# System deps
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

# Copy project
COPY . .

# Create output and log dirs
RUN mkdir -p _outputs/digital_products _outputs/web_hunter _outputs/youtube \
             _outputs/seo_content _outputs/data_products _outputs/leads_api \
             _outputs/web_navrhy _logs _config

ENV PYTHONUNBUFFERED=1
ENV CONTINUOUS_LOOP=true
ENV LOOP_DELAY_MINUTES=60
# Railway injects PORT automatically
ENV PORT=8080

# scheduler.py: FastAPI server (port $PORT) + scheduled factory jobs
CMD ["python", "scheduler.py"]

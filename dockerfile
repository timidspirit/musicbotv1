# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy bot script and requirements file
COPY bot.py .
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg && \
    pip install -r requirements.txt

# Create cache directory
RUN mkdir /app/cache

# Set environment variables (default values for variables like PREFIX, IDLE_TIMEOUT, etc.)
ENV DISCORD_TOKEN="your_discord_bot_token" 
ENV CACHE_DIR="/app/cache"
ENV IDLE_TIMEOUT=10
ENV PREFIX="!"

# Run the bot
CMD ["python", "bot.py"]

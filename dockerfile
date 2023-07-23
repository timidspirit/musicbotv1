# Use a Python base image
FROM python:3.11.4-slim

# Set the working directory
WORKDIR /app

# Copy the Python script into the container
COPY import.py /app/

# Install the required dependencies
RUN pip install discord youtube_dl

# Run the Python script
CMD ["python", "import.py"]

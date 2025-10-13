# Use lightweight Python runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for Cloud Run
ENV PORT 8080

# Run using Functions Framework
CMD ["functions-framework", "--target=handle_webhook", "--port=8080"]

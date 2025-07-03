FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements .
RUN pip install --no-cache-dir -r requirements

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers=4"]

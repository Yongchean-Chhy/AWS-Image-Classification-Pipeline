FROM python:3.11-slim

WORKDIR /app

# Copy requirement files first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files into the container
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to launch the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
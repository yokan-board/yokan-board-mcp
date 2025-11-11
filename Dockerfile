# Use a slim Python image as the base
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY src/ ./src/

# Expose the port the application runs on (default for FastAPI is 8000)
EXPOSE 8888

# Command to run the application
# CMD ["python", "-m", "src.main"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8888"]

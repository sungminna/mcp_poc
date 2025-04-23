# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Specify Poetry version
ENV POETRY_VERSION=2.1.1
# Ensure Poetry runs without prompts
ENV POETRY_NO_INTERACTION=1
# Do not create virtualenvs
ENV POETRY_VIRTUALENVS_CREATE=false

# Set work directory
WORKDIR /app

# Install system dependencies for building mysqlclient and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy only dependency definitions
COPY pyproject.toml poetry.lock* /app/

RUN poetry install --no-root 

# Copy project code
COPY . /app/

# Copy environment file
COPY .env /app/.env

# Expose port 8000 for the application
EXPOSE 8000

# Start the application using Gunicorn
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
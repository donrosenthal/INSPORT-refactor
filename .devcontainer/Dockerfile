FROM mcr.microsoft.com/vscode/devcontainers/python:3.12

# Set the working directory to match devcontainer.json workspaceFolder
WORKDIR /workspaces/${localWorkspaceFolderBasename}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up environment
ENV PYTHONUNBUFFERED=1

# Copy requirements first (better Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application (this line would normally be last)
# COPY . .

# Optional: Default command to run when container starts
# CMD ["python", "your_main_script.py"]





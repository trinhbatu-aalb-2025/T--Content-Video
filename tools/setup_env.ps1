# Setup environment and install dependencies
Write-Host "Setting up Python environment..." -ForegroundColor Yellow

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
    
    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
    
    # Check system
    Write-Host "Checking system..." -ForegroundColor Green
    python check_ffmpeg.py
    
} else {
    Write-Host "Virtual environment not found. Creating new one..." -ForegroundColor Yellow
    python -m venv venv
    & "venv\Scripts\Activate.ps1"
    pip install -r requirements.txt
    python check_ffmpeg.py
}

Write-Host "Setup complete!" -ForegroundColor Green 
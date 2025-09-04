# Video Processor Runner for Windows (PowerShell)
# Script nay chay tu thu muc goc cua du an

# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Colors for output
$Red = "`e[91m"
$Green = "`e[92m"
$Yellow = "`e[93m"
$Blue = "`e[94m"
$White = "`e[97m"
$NC = "`e[0m"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "$Green[INFO]$NC $Message"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "$Yellow[WARNING]$NC $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Host "$Red[ERROR]$NC $Message"
}

function Write-Header {
    param([string]$Title)
    Write-Host "$Blue================================$NC"
    Write-Host "$Blue$Title$NC"
    Write-Host "$Blue================================$NC"
}

# Function to check project structure
function Test-ProjectStructure {
    Write-Status "Kiem tra cau truc du an..."
    
    if (-not (Test-Path "run\all_in_one.py")) {
        Write-Error "Khong tim thay file all_in_one.py trong thu muc run\"
        Write-Error "Vui long chay script nay tu thu muc goc cua du an"
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
    
    Write-Status "Cau truc du an hop le!"
}

# Function to check Python
function Test-Python {
    Write-Status "Kiem tra Python..."
    
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python khong duoc tim thay"
        }
        Write-Status "Python da san sang!"
    }
    catch {
        Write-Error "Python khong duoc tim thay. Vui long cai dat Python."
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
}

# Function to setup virtual environment
function Setup-VirtualEnvironment {
    Write-Status "Kiem tra virtual environment..."
    
    if (-not (Test-Path "venv")) {
        Write-Warning "Khong tim thay virtual environment. Tao moi..."
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Khong the tao virtual environment"
            Read-Host "Nhan Enter de thoat"
            exit 1
        }
    }
    
    Write-Status "Kich hoat virtual environment..."
    
    try {
        & "venv\Scripts\Activate.ps1"
        Write-Status "Virtual environment da duoc kich hoat!"
    }
    catch {
        Write-Error "Khong the kich hoat virtual environment"
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
}

# Function to install requirements
function Install-Requirements {
    Write-Status "Kiem tra va cai dat dependencies..."
    
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Khong the cai dat dependencies"
            Read-Host "Nhan Enter de thoat"
            exit 1
        }
        Write-Status "Dependencies da duoc cai dat!"
    } else {
        Write-Warning "Khong tim thay requirements.txt"
    }
}

# Function to extract folder ID from Google Drive link
function Get-FolderId {
    param([string]$InputLink)
    
    # Remove extra spaces
    $inputLink = $InputLink.Trim()
    
    # Check if it's already a folder ID (no / in the string)
    if ($inputLink -notmatch "/") {
        return $inputLink
    }
    
    # Extract folder ID from Google Drive link
    if ($inputLink -match "folders/([^/?]+)") {
        return $matches[1]
    }
    
    # If no match found, try to extract from URL path
    $uri = [System.Uri]$inputLink
    $segments = $uri.Segments
    if ($segments.Length -ge 3) {
        return $segments[2].TrimEnd('/')
    }
    
    return $null
}

# Function to validate folder ID
function Test-FolderId {
    param([string]$FolderId)
    
    if ([string]::IsNullOrEmpty($FolderId)) {
        Write-Error "Folder ID khong hop le"
        return $false
    }
    
    if ($FolderId -notmatch "^[0-9a-zA-Z_-]+$") {
        Write-Error "Folder ID khong hop le (chi chua chu so, chu cai, dau gach duoi va dau gach ngang)"
        return $false
    }
    
    Write-Status "Folder ID hop le: $FolderId"
    return $true
}

# Function to run existing folder
function Run-ExistingFolder {
    Write-Header "CHAY VIDEO TU FOLDER MAC DINH"
    
    Write-Status "Bat dau xu ly video..."
    python run\all_in_one.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Co loi xay ra khi chay script"
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
    
    Write-Status "Xu ly video hoan tat!"
}

# Function to run custom folder
function Run-CustomFolder {
    Write-Header "CHAY VIDEO TU FOLDER TUY CHON"
    
    Write-Status "Nhap Google Drive link hoac Folder ID:"
    $inputLink = Read-Host
    
    $folderId = Get-FolderId $inputLink
    
    if (-not (Test-FolderId $folderId)) {
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
    
    Write-Status "Tao file tam thoi voi folder ID: $folderId"
    
    # Create temporary copy of all_in_one.py with custom folder ID
    Copy-Item "run\all_in_one.py" "run\all_in_one_temp.py"
    
    # Replace the folder ID in the temporary file
    $content = Get-Content "run\all_in_one_temp.py" -Raw
    $content = $content -replace 'INPUT_FOLDER_ID = "[^"]*"', "INPUT_FOLDER_ID = `"$folderId`""
    Set-Content "run\all_in_one_temp.py" $content
    
    Write-Status "Bat dau xu ly video tu folder: $folderId"
    python run\all_in_one_temp.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Co loi xay ra khi chay script"
        Remove-Item "run\all_in_one_temp.py" -ErrorAction SilentlyContinue
        Read-Host "Nhan Enter de thoat"
        exit 1
    }
    
    # Clean up temporary file
    Remove-Item "run\all_in_one_temp.py" -ErrorAction SilentlyContinue
    
    Write-Status "Xu ly video hoan tat!"
}

# Function to show menu
function Show-Menu {
    Write-Header "VIDEO PROCESSOR RUNNER"
    Write-Host "$WhiteChon lua chon:$NC"
    Write-Host ""
    Write-Host "$White1. Chay video tu folder mac dinh$NC"
    Write-Host "$White2. Chay video tu folder tuy chon$NC"
    Write-Host "$White3. Thoat$NC"
    Write-Host ""
}

# Function to get user choice
function Get-UserChoice {
    do {
        $choice = Read-Host "Nhap lua chon cua ban (1-3)"
        
        switch ($choice) {
            "1" { return 1 }
            "2" { return 2 }
            "3" { return 3 }
            default {
                Write-Error "Lua chon khong hop le. Vui long chon 1, 2 hoac 3."
            }
        }
    } while ($true)
}

# Main function
function Main {
    # Check project structure
    Test-ProjectStructure
    
    # Check Python
    Test-Python
    
    # Setup virtual environment
    Setup-VirtualEnvironment
    
    # Install requirements
    Install-Requirements
    
    # Show menu
    Show-Menu
    $userChoice = Get-UserChoice
    
    # Run appropriate function based on choice
    switch ($userChoice) {
        1 { Run-ExistingFolder }
        2 { Run-CustomFolder }
        3 { 
            Write-Status "Tam biet!"
            exit 0
        }
    }
    
    Write-Host ""
    Write-Status "Hoan thanh!"
    Read-Host "Nhan Enter de thoat"
}

# Run main function
Main


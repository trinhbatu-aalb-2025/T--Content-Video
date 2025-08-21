#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cấu hình chính cho Video Converter
"""

import os
from pathlib import Path

# Đường dẫn gốc của dự án
PROJECT_ROOT = Path(__file__).parent.parent

# Cấu trúc thư mục
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = PROJECT_ROOT / "temp"
TOOLS_DIR = PROJECT_ROOT / "tools"
RUN_DIR = PROJECT_ROOT / "run"
SRC_DIR = PROJECT_ROOT / "src"

# Đảm bảo các thư mục tồn tại
for directory in [LOGS_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

# API Keys
DEEPGRAM_API_KEY = 'bb69898295e896c0123d4cdd01a43fdcb78b7b4b'
GEMINI_API_KEY = 'AIzaSyCNdaVmt9KwMN0mEfSSEQ37oG8U5T088JU'

# Google Sheets
SPREADSHEET_ID = '1X2aAjmotV3OvESfO_hFWDiyzpMIxaSGTB4M_e5LAMYg'
SHEET_NAME = 'Mp3 to text'

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

# File paths
TOKEN_FILE = CONFIG_DIR / "token.json"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret_978352364973-qoautr8eke7219mroqstbch3mehnt42r.apps.googleusercontent.com.json"
FFMPEG_PATH = TOOLS_DIR / "ffmpeg.exe"

# Logging
LOG_FILE = LOGS_DIR / "video_converter.log"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# FFmpeg settings
FFMPEG_SETTINGS = {
    'mp3_quality': '-q:a 2',  # High quality MP3
    'voice_extraction': '-af "highpass=f=200,lowpass=f=3000"',  # Voice frequency range
    'sample_rate': '16000',  # Sample rate for speech recognition
}

# Deepgram settings
DEEPGRAM_SETTINGS = {
    'model': 'nova-2',  # Best model for accuracy
    'language': 'vi',  # Vietnamese
    'punctuate': True,
    'diarize': True,
    'utterances': True,
    'timestamps': True,
}

# Gemini settings
GEMINI_SETTINGS = {
    'model': 'gemini-1.5-pro',
    'temperature': 0.7,
    'max_tokens': 4000,
} 
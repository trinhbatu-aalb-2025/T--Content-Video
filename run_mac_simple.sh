#!/usr/bin/env bash

# Video Processor Runner for Mac/Linux - Simple Version
# Script này chạy từ thư mục gốc của dự án

echo "================================"
echo "   VIDEO PROCESSOR RUNNER - SIMPLE"
echo "================================"
echo

# Check if we're in the right directory
if [ ! -f "run/all_in_one.py" ]; then
    echo "[ERROR] Không tìm thấy file all_in_one.py trong thư mục run/"
    echo "[ERROR] Vui lòng chạy script này từ thư mục gốc của dự án"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 không được tìm thấy. Vui lòng cài đặt Python3."
    exit 1
fi

# Setup virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Tạo virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể tạo virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERROR] Không thể kích hoạt virtual environment"
    exit 1
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể cài đặt dependencies"
        exit 1
    fi
fi

# Run the video processor
echo "[INFO] Bắt đầu xử lý video..."
python3 run/all_in_one.py

if [ $? -ne 0 ]; then
    echo "[ERROR] Xử lý video thất bại!"
    exit 1
fi

echo "[INFO] Xử lý video thành công!"

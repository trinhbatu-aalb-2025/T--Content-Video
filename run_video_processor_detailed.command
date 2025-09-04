#!/usr/bin/env bash

# Video Processor Runner for Mac - Detailed Log
# Script này chạy từ thư mục gốc của dự án
# Double-click để chạy trên Mac

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Mac-specific setup and permissions
echo "[INFO] Thiết lập quyền cho Mac..."

# Set proper permissions (755 = rwxr-xr-x)
chmod 755 "$0"

# Remove Windows line endings if present (CRLF -> LF)
sed -i '' -e 's/\r$//' "$0"

# Remove quarantine attribute if macOS blocks "downloaded from Internet"
xattr -dr com.apple.quarantine "$0" 2>/dev/null || true

echo "[INFO] Quyền đã được thiết lập!"
echo

# Open Terminal window with title
echo -e "\033]0;Video Processor - Detailed Log\007"

echo "================================"
echo "   VIDEO PROCESSOR RUNNER - DETAILED"
echo "================================"
echo

# Check if we're in the right directory
echo "[INFO] Kiểm tra cấu trúc dự án..."
if [ ! -f "run/all_in_one.py" ]; then
    echo "[ERROR] Không tìm thấy file all_in_one.py trong thư mục run/"
    echo "[ERROR] Vui lòng chạy script này từ thư mục gốc của dự án"
    echo "[INFO] Nhấn Enter để thoát..."
    read
    exit 1
fi
echo "[INFO] Cấu trúc dự án hợp lệ!"
echo

# Check Python
echo "[INFO] Kiểm tra Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 không được tìm thấy. Vui lòng cài đặt Python3."
    echo "[INFO] Nhấn Enter để thoát..."
    read
    exit 1
fi
echo "[INFO] Python3 đã sẵn sàng!"
echo

# Setup virtual environment
echo "[INFO] Kiểm tra virtual environment..."
if [ ! -d "venv" ]; then
    echo "[WARNING] Không tìm thấy virtual environment. Tạo mới..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể tạo virtual environment"
        echo "[INFO] Nhấn Enter để thoát..."
        read
        exit 1
    fi
fi

echo "[INFO] Kích hoạt virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERROR] Không thể kích hoạt virtual environment"
    echo "[INFO] Nhấn Enter để thoát..."
    read
    exit 1
fi
echo "[INFO] Virtual environment đã được kích hoạt!"
echo

# Install requirements
echo "[INFO] Kiểm tra dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể cài đặt dependencies"
        echo "[INFO] Nhấn Enter để thoát..."
        read
        exit 1
    fi
    echo "[INFO] Dependencies OK!"
else
    echo "[WARNING] Không tìm thấy requirements.txt"
fi
echo

# Show menu
echo "================================"
echo "   CHỌN LỰA CHỌN:"
echo "================================"
echo
echo "1. Chạy video từ folder mặc định (log chi tiết)"
echo "2. Chạy video từ folder tùy chọn (log chi tiết)"
echo "3. Thoát"
echo

while true; do
    read -p "Nhập lựa chọn của bạn (1-3): " choice
    
    case $choice in
        1)
            echo
            echo "================================"
            echo "   CHẠY VIDEO TỪ FOLDER MẶC ĐỊNH"
            echo "================================"
            echo
            echo "[INFO] Bắt đầu xử lý video với log chi tiết..."
            echo "[INFO] Sẽ hiển thị:"
            echo "[INFO] - Số lượng video trong folder"
            echo "[INFO] - Tên video đang xử lý"
            echo "[INFO] - Tiến trình xử lý (%)"
            echo "[INFO] - Trạng thái từng bước"
            echo
            python3 run/all_in_one.py
            if [ $? -ne 0 ]; then
                echo "[ERROR] Xử lý video thất bại!"
                echo "[INFO] Nhấn Enter để thoát..."
                read
                exit 1
            fi
            echo "[INFO] Xử lý video thành công!"
            break
            ;;
        2)
            echo
            echo "================================"
            echo "   CHẠY VIDEO TỪ FOLDER TÙY CHỌN"
            echo "================================"
            echo
            echo "[INFO] Nhập Google Drive link hoặc Folder ID:"
            read -p "" input_link
            
            # Extract folder ID from Google Drive link
            folder_id="$input_link"
            if [ -z "$input_link" ]; then
                echo "[ERROR] Không được để trống"
                echo "[INFO] Nhấn Enter để thoát..."
                read
                exit 1
            fi
            
            # Check if it's a Google Drive link
            if [[ "$input_link" == *"drive.google.com"* ]]; then
                echo "[INFO] Phát hiện Google Drive link, đang trích xuất Folder ID..."
                # Extract folder ID from Google Drive link
                folder_id=$(echo "$input_link" | grep -o 'folders/[a-zA-Z0-9_-]*' | cut -d'/' -f2)
                if [ -z "$folder_id" ]; then
                    folder_id="$input_link"
                fi
                echo "[INFO] Đã trích xuất Folder ID: $folder_id"
            else
                echo "[INFO] Sử dụng input trực tiếp làm Folder ID"
            fi
            
            echo "[INFO] Folder ID: $folder_id"
            echo "[INFO] Bắt đầu xử lý video từ folder: $folder_id với log chi tiết..."
            echo "[INFO] Sẽ hiển thị:"
            echo "[INFO] - Số lượng video trong folder"
            echo "[INFO] - Tên video đang xử lý"
            echo "[INFO] - Tiến trình xử lý (%)"
            echo "[INFO] - Trạng thái từng bước"
            echo
            
            # Run with custom folder ID
            python3 run/all_in_one.py --custom-folder "$folder_id"
            if [ $? -ne 0 ]; then
                echo "[ERROR] Xử lý video thất bại!"
                echo "[INFO] Nhấn Enter để thoát..."
                read
                exit 1
            fi
            echo "[INFO] Xử lý video thành công!"
            break
            ;;
        3)
            echo "[INFO] Tạm biệt!"
            exit 0
            ;;
        *)
            echo "[ERROR] Lựa chọn không hợp lệ. Vui lòng chọn 1, 2 hoặc 3."
            ;;
    esac
done

echo
echo "[INFO] Hoàn thành!"
echo "[INFO] Nhấn Enter để thoát..."
read

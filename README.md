# 🎬 Content Video Processor - Hệ Thống Xử Lý Video Toàn Diện

## 📋 Tổng Quan

Hệ thống **Content Video Processor** cung cấp giải pháp toàn diện cho việc xử lý video tự động:
**MP4 → Voice Only → Text (VI/CN) → Translate → Rewrite → Drive + Sheets**

### 🚀 **Tính Năng Chính:**
- **Tách voice từ video** (loại bỏ background music)
- **Chuyển đổi voice → Text** bằng Deepgram API (hỗ trợ tiếng Việt và tiếng Trung)
- **Tự động dịch tiếng Trung sang tiếng Việt** (nếu phát hiện)
- **Viết lại text** bằng Gemini API với cấu trúc chuyên nghiệp
- **Upload tự động** lên Google Drive và cập nhật Google Sheets
- **Xử lý hàng loạt** với kiểm tra trạng thái thông minh

## 📁 Cấu Trúc Dự Án

```
Content-Video/
├── README.md                           # File này - Hướng dẫn tổng quan
├── run_video_processor.bat             # Script chung cho Windows (Khuyến nghị)
├── run_video_processor.sh              # Script chung cho Linux/Mac (Khuyến nghị)
├── run_windows.bat                     # Script wrapper cho Windows
├── run_linux_mac.sh                    # Script wrapper cho Linux/Mac
├── video_processor_runners/            # Bộ script chạy video processor
│   ├── README.md                       # Hướng dẫn sử dụng runners
│   ├── RUNNER_README.md               # Hướng dẫn chi tiết
│   ├── windows/                       # Script cho Windows
│   │   ├── README.md                  # Hướng dẫn Windows
│   │   ├── run_video_processor.bat    # Batch script
│   │   └── run_video_processor.ps1    # PowerShell script
│   ├── linux_mac/                     # Script cho Linux/Mac
│   │   ├── README.md                  # Hướng dẫn Linux/Mac
│   │   └── run_video_processor.sh     # Bash script
│   └── tools/                         # Công cụ hỗ trợ
│       ├── README.md                  # Hướng dẫn tools
│       └── check_drive_access.py      # Kiểm tra quyền truy cập Google Drive
├── run/                               # Thư mục chứa script chính
│   ├── all_in_one.py                  # Script chính xử lý video
│   ├── video_checker.py               # Module kiểm tra video
│   └── ...                            # Các module khác
├── venv/                              # Virtual environment
├── requirements.txt                   # Dependencies
├── config/                            # Cấu hình
├── tools/                             # Công cụ FFmpeg
└── ...                                # Các file khác
```

## 🚀 Cách Sử Dụng Nhanh

### 🎯 **Script Chung (Khuyến Nghị):**

#### **Trên Windows:**
```cmd
# Double-click hoặc chạy từ Command Prompt - Log ngắn gọn
run_video_processor.bat

# Chạy với log chi tiết để debug
debug_all_in_one.bat

```

#### **Nếu script không chạy được:**
```cmd

# Mở Command Prompt
# Di chuyển đến thư mục gốc: cd C:\Content-Video
# Chạy script
cmd /c run_video_processor.bat
```

#### **Trên Linux/Mac:**
```bash
# Cấp quyền thực thi
chmod +x run_video_processor.sh

# Chạy script
./run_video_processor.sh
```

Script này sẽ:
1. **Tự động phát hiện hệ điều hành**
2. **Hiển thị menu chọn Windows/Mac**
3. **Chạy script phù hợp** với hệ điều hành đã chọn
4. **Sửa lỗi font chữ** với encoding UTF-8

### 🔧 **Lưu ý về Font Chữ:**
- Các script đã được sửa để tránh lỗi hiển thị ký tự có dấu
- Sử dụng encoding UTF-8 và ký tự ASCII đơn giản
- Nếu vẫn gặp lỗi font, hãy thử chạy trong Command Prompt thay vì PowerShell

### 🔧 **Script Riêng Biệt (Tùy Chọn):**

#### Windows:
```cmd
# Double-click hoặc chạy từ Command Prompt
run_windows.bat
```

#### Linux/Mac:
```bash
# Cấp quyền thực thi
chmod +x run_linux_mac.sh

# Chạy script
./run_linux_mac.sh
```

### Kiểm tra quyền truy cập Google Drive:
```bash
python video_processor_runners/tools/check_drive_access.py
```

## 🎯 Menu Options

Khi chạy script, bạn sẽ thấy menu với 3 options:

```
================================
VIDEO PROCESSOR MENU
================================
Chọn một trong các options sau:

1. Chạy với folder hiện tại (sử dụng folder ID mặc định)
2. Chạy với folder tùy chỉnh (nhập link hoặc ID Google Drive)
3. Thoát
```

### Option 1: Chạy với folder hiện tại
- Sử dụng folder ID mặc định: `17_ncdjiRI2K4c4OA-sp3Uyi4bskP0CIu`
- Chạy trực tiếp `all_in_one.py` không thay đổi
- Phù hợp khi bạn muốn xử lý video trong folder cố định

### Option 2: Chạy với folder tùy chỉnh
- **Hỗ trợ nhập link Google Drive hoặc ID**
- Tự động tách ID từ link
- Kiểm tra tính hợp lệ của ID
- Tạo file Python tạm thời với folder ID mới
- Xử lý video trong folder được chỉ định
- Tự động dọn dẹp file tạm sau khi hoàn thành

### ✅ Các Định Dạng Link Hỗ Trợ:
```
✅ https://drive.google.com/drive/folders/1ABC123DEF456GHI789JKL
✅ https://drive.google.com/file/d/1ABC123DEF456GHI789JKL/view
✅ https://drive.google.com/open?id=1ABC123DEF456GHI789JKL
✅ 1ABC123DEF456GHI789JKL (ID trực tiếp)
```

## 🔐 Quyền Truy Cập Google Drive

### ✅ Có thể truy cập:
- Folder được chia sẻ **công khai** (Anyone with the link)
- Folder được chia sẻ với **email của tài khoản Google Cloud**
- Folder thuộc về **tài khoản Google Cloud** đã xác thực

### ❌ Không thể truy cập:
- Folder **riêng tư** của tài khoản khác
- Folder chỉ chia sẻ với **tài khoản khác**

## 🛠️ Yêu Cầu Hệ Thống

### Trước khi chạy, đảm bảo:
1. **Python** 3.7+ đã được cài đặt
2. **FFmpeg** đã được cài đặt và có trong PATH
3. **Google Drive API** đã được bật
4. **OAuth credentials** có quyền truy cập folder
5. **Deepgram API key** hợp lệ
6. **Gemini API key** hợp lệ

### Script sẽ tự động:
- Kiểm tra Python có sẵn không
- Tạo virtual environment nếu chưa có
- Kích hoạt virtual environment
- Cài đặt dependencies từ `requirements.txt`
- **Tách ID từ link Google Drive**
- **Kiểm tra tính hợp lệ của ID**

## 🔧 Cấu Hình API Keys

### 1. **Deepgram API Key:**
```python
# Trong file run/all_in_one.py (dòng 108)
self.deepgram_api_key = '62577e5f53dd9757f0e88250e7326f78281bfa5b'
```

### 2. **Gemini API Key:**
```python
# Trong file run/all_in_one.py (dòng 113)
self.gemini_api_key = 'AIzaSyCT45_AEnJETS3wsyjXbyKrj7w4US9KXZE'
```

### 3. **Google OAuth Credentials:**
- File `client_secret_*.json` đã có sẵn trong thư mục gốc
- Token sẽ được tạo tự động khi chạy lần đầu

## 📊 Kết Quả Mong Đợi

### 📁 Files được tạo:
- ✅ **Voice only MP3** được upload lên Drive
- ✅ **Text gốc** (với timeline) được upload lên Drive
- ✅ **Text viết lại** (cấu trúc đầy đủ) được upload lên Drive
- ✅ **Text không timeline** (chỉ nội dung chính) được tạo
- ✅ **Gợi ý tiêu đề, captions, CTA** được tạo

### 📊 Google Sheets được cập nhật:
- ✅ **Cột A:** Link MP4 gốc
- ✅ **Cột B:** Tên Video (từ file MP4)
- ✅ **Cột C:** Link MP3 voice only
- ✅ **Cột D:** Link text gốc
- ✅ **Cột E:** Text gốc MP3 (có timeline)
- ✅ **Cột F:** Link text cải tiến
- ✅ **Cột G:** Text cải tiến (chỉ nội dung chính có timeline)
- ✅ **Cột H:** Text no timeline (chỉ nội dung chính)
- ✅ **Cột I:** Gợi ý tiêu đề (5 tiêu đề + 3 captions + 1 CTA)

### 📋 Kết quả hiển thị:
```
🎉 === KẾT QUẢ XỬ LÝ ===
📊 Tổng số video: 5
✅ Thành công: 4
❌ Thất bại: 1
📊 Google Sheets đã được cập nhật tự động

📋 CHI TIẾT VIDEO THÀNH CÔNG:
  🎬 video1.mp4
    🎤 Voice: 1abc123...
    📄 Text: 2def456...
    ✍️ Rewritten: 3ghi789...

🔗 LINKS:
🎤 Voice Only Folder: https://drive.google.com/drive/folders/...
📄 Text Original Folder: https://drive.google.com/drive/folders/...
✍️ Text Rewritten Folder: https://drive.google.com/drive/folders/...
```

## 🔧 Troubleshooting

### Lỗi thường gặp:

#### 1. **"Python không được tìm thấy"**
- **Giải pháp:** Cài đặt Python 3.7+ và thêm vào PATH

#### 2. **"Không tìm thấy file all_in_one.py"**
- **Giải pháp:** Chạy script từ thư mục gốc của dự án

#### 3. **"Không thể kích hoạt virtual environment"**
- **Giải pháp:** Kiểm tra thư mục `venv` và quyền truy cập

#### 4. **"Không thể cài đặt dependencies"**
- **Giải pháp:** Kiểm tra kết nối internet và file `requirements.txt`

#### 5. **"Không thể tách ID từ link"**
- **Giải pháp:** Kiểm tra link Google Drive có đúng format không

#### 6. **"ID folder không hợp lệ"**
- **Giải pháp:** ID Google Drive thường có 25-44 ký tự

#### 7. **"Không có quyền truy cập folder"**
- **Giải pháp:** Sử dụng `check_drive_access.py` để kiểm tra

#### 8. **"OAuth authentication failed"**
- **Giải pháp:** 
  1. Kiểm tra file `client_secret_*.json`
  2. Thêm email vào danh sách testers trong Google Cloud Console
  3. Hoặc tạo OAuth credentials mới

#### 9. **"FFmpeg not found"**
- **Giải pháp:** Cài đặt FFmpeg và thêm vào PATH

#### 10. **"API quota exceeded"**
- **Giải pháp:** Kiểm tra Deepgram/Gemini API limits

## 🔧 Cài Đặt FFmpeg

### Windows:
1. Tải FFmpeg từ https://ffmpeg.org/download.html
2. Giải nén vào thư mục (ví dụ: `C:\ffmpeg`)
3. Thêm `C:\ffmpeg\bin` vào PATH

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

### macOS:
```bash
brew install ffmpeg
```

## 🔧 Giải Quyết Vấn Đề Google Cloud

### Vấn đề: Ứng dụng chưa được Google xác minh

#### Giải pháp 1: Thêm email vào danh sách testers (Khuyến nghị)
1. Truy cập https://console.cloud.google.com/
2. Vào **APIs & Services** > **OAuth consent screen**
3. Tìm phần **Test users**
4. Click **Add Users** và thêm email của bạn
5. Click **Save**

#### Giải pháp 2: Tạo OAuth credentials mới
1. Tạo project mới trong Google Cloud Console
2. Bật Google Drive API và Google Sheets API
3. Tạo OAuth 2.0 Client ID cho Desktop application
4. Tải file JSON và thay thế file cũ

## 📖 Tài Liệu Chi Tiết

### Xem các file README trong thư mục `video_processor_runners/`:
- `video_processor_runners/README.md` - Hướng dẫn tổng quan
- `video_processor_runners/RUNNER_README.md` - Hướng dẫn chi tiết
- `video_processor_runners/windows/README.md` - Hướng dẫn Windows
- `video_processor_runners/linux_mac/README.md` - Hướng dẫn Linux/Mac
- `video_processor_runners/tools/README.md` - Hướng dẫn tools

## 📞 Hỗ Trợ

Nếu gặp vấn đề, hãy kiểm tra:
1. Log file trong thư mục `run/`
2. Cấu hình API keys
3. Quyền truy cập Google Drive (sử dụng `check_drive_access.py`)
4. Kết nối internet
5. Format link Google Drive

## 🎉 Kết Luận

Hệ thống **Content Video Processor** cung cấp giải pháp toàn diện cho việc xử lý video:
- **Tự động hóa hoàn toàn** từ video đến text
- **Hỗ trợ đa ngôn ngữ** (Việt-Trung)
- **AI-powered text rewriting** với cấu trúc chuyên nghiệp
- **Tích hợp Google Drive/Sheets** để quản lý kết quả
- **Xử lý hàng loạt** với kiểm tra trạng thái thông minh

**🚀 Chúc bạn sử dụng hệ thống thành công!**

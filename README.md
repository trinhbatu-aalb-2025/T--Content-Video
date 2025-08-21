# 🎬 Video Converter - All-in-One Processing System

Hệ thống xử lý video toàn diện: **MP4 → Voice Only → Text (VI/CN) → Translate → Rewrite → Drive**

## 🚀 **TÍNH NĂNG CHÍNH**

- ✅ **Tách voice từ video** (loại bỏ background music)
- ✅ **Chuyển đổi voice thành text** (hỗ trợ tiếng Việt và tiếng Trung)
- ✅ **Tự động dịch tiếng Trung sang tiếng Việt**
- ✅ **Viết lại text bằng AI** (Gemini)
- ✅ **Upload lên Google Drive** tự động
- ✅ **Cập nhật Google Sheets** với kết quả
- ✅ **Timeline chính xác** (giây 1-3: xin chào...)

## 📁 **CẤU TRÚC THƯ MỤC**

```
video-converter/
├── run/
│   ├── all_in_one.py          # File chính
│   └── prompt_template.txt    # Template viết lại text
├── tools/
│   ├── ffmpeg.exe            # FFmpeg binary
│   └── install.bat           # Script cài đặt
├── config/
│   ├── client_secret_*.json  # Google Auth
│   └── token.json            # Google token (tự tạo)
├── docs/                     # Tài liệu hướng dẫn
├── Instructions for use/      # Hướng dẫn sử dụng
└── requirements.txt          # Dependencies
```

## 🔧 **CÁCH SỬ DỤNG**

### **1. Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

### **2. Cấu hình API Keys:**
- **Deepgram API Key:** Đã cấu hình sẵn
- **Gemini API Key:** Đã cấu hình sẵn
- **Google OAuth:** File `config/client_secret_*.json` đã có sẵn

### **3. Cấu hình Google Drive Folders:**
Mở file `run/all_in_one.py` (dòng 1634-1643) và thay đổi:

```python
# CẤU HÌNH TẠI ĐÂY - Thay đổi các giá trị bên dưới
# ===================================================

# ID của folder chứa video (input) - Thay đổi nếu cần
INPUT_FOLDER_ID = "17_ncdjiRI2K4c4OA-sp3Uyi4bskP0CIu"

# ID của folder để upload voice only - Thay đổi nếu cần  
VOICE_ONLY_FOLDER_ID = "1FUP92ha2uaxPmB3a680eOd7TAqH1SqGT"

# ID của folder để upload text gốc - Thay đổi nếu cần
TEXT_ORIGINAL_FOLDER_ID = "1ZswATID5nLDRjap6yvDJYaa435Nrp8eo"

# ID của folder để upload text đã viết lại - Thay đổi nếu cần
TEXT_REWRITTEN_FOLDER_ID = "18XIdyGd-9ahPLHElJBBwXeATgcFanoQR"
```

### **4. Chạy hệ thống:**
```bash
python run/all_in_one.py
```

## 🔍 **Cách lấy Folder ID từ Google Drive:**

1. **Mở folder trên Google Drive** mà bạn muốn sử dụng
2. **Copy URL** từ thanh địa chỉ trình duyệt
3. **URL có dạng:** `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. **Copy phần `FOLDER_ID_HERE`** (chuỗi ký tự dài)

## 📋 **Giải thích từng folder:**

#### **🎬 INPUT_FOLDER_ID** (Bắt buộc thay đổi)
- **Chức năng:** Folder chứa video MP4 cần xử lý
- **Cách thay đổi:** Thay ID này để lấy video từ drive khác
- **Ví dụ:** Nếu muốn xử lý video từ folder khác, chỉ cần thay đổi ID này

#### **🎤 VOICE_ONLY_FOLDER_ID** (Có thể giữ nguyên)
- **Chức năng:** Folder lưu file MP3 voice only (đã tách khỏi video)
- **Cách thay đổi:** Thay đổi nếu muốn lưu MP3 vào folder khác

#### **📄 TEXT_ORIGINAL_FOLDER_ID** (Có thể giữ nguyên)
- **Chức năng:** Folder lưu file text gốc từ video
- **Cách thay đổi:** Thay đổi nếu muốn lưu text gốc vào folder khác

#### **✍️ TEXT_REWRITTEN_FOLDER_ID** (Có thể giữ nguyên)
- **Chức năng:** Folder lưu file text đã viết lại bởi Gemini
- **Cách thay đổi:** Thay đổi nếu muốn lưu text cải tiến vào folder khác

## 🔄 **Ví dụ thay đổi để lấy video từ drive khác:**

```python
# Trước khi thay đổi:
INPUT_FOLDER_ID = "17_ncdjiRI2K4c4OA-sp3Uyi4bskP0CIu"

# Sau khi thay đổi (ví dụ):
INPUT_FOLDER_ID = "1ABC123DEF456GHI789JKL"  # ID folder mới chứa video
```

## ⚠️ **Lưu ý quan trọng:**

1. **Chỉ cần thay đổi `INPUT_FOLDER_ID`** nếu muốn lấy video từ drive khác
2. **Các folder khác có thể giữ nguyên** để lưu kết quả vào cùng một nơi
3. **Đảm bảo folder có quyền truy cập** với Google account đang sử dụng
4. **Kiểm tra folder tồn tại** trước khi chạy chương trình

## 📊 **Kết quả mong đợi:**

- ✅ Voice only MP3 được upload lên Drive
- ✅ Text gốc (với timeline) được upload lên Drive
- ✅ Text viết lại (theo template) được upload lên Drive
- ✅ Google Sheets được cập nhật tự động với links
- ✅ Cột "Tên Video" được điền với tên file MP4 gốc

## 🌐 **TÍNH NĂNG ĐẶC BIỆT**

### **🔍 Tự động phát hiện ngôn ngữ:**
- Hỗ trợ tiếng Việt và tiếng Trung
- Tự động dịch tiếng Trung sang tiếng Việt
- Timeline chính xác (giây 1-3: xin chào... giây 4-9: giới thiệu...)

### **📊 Xử lý nhiều video:**
- Tự động tìm và xử lý tất cả video trong folder
- Cập nhật Google Sheets với kết quả từng video

### **🎤 Voice Extraction:**
- Tách voice từ video (loại bỏ background music)
- Sử dụng FFmpeg với filter chuyên dụng

## 📞 **HỖ TRỢ**

Nếu gặp vấn đề:
1. Kiểm tra tất cả cấu hình API keys và folder IDs
2. Xem log file `all_in_one.log`
3. Đảm bảo tất cả dependencies đã được cài đặt
4. Kiểm tra quyền truy cập Google Drive/Sheets

**🎉 Chúc bạn sử dụng hệ thống thành công!**

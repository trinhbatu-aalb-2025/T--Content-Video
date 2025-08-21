#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All-in-One: MP4 -> Voice Only -> Text (VI/CN) -> Translate -> Rewrite -> TTS -> Drive
Tất cả trong một script duy nhất

        Luồng xử lý hoàn chỉnh:
        1. Tải video MP4 từ Google Drive
        2. Tách voice từ video (loại bỏ background music)
        3. Upload voice only lên Google Drive
        4. Chuyển đổi voice -> Text bằng Deepgram API (hỗ trợ tiếng Việt và tiếng Trung) với timeline
        5. Nếu phát hiện tiếng Trung: tự động dịch sang tiếng Việt
        6. Upload text gốc (hoặc đã dịch) lên Google Drive
        7. Viết lại text bằng Gemini API (cấu trúc đầy đủ: 5 tiêu đề + nội dung + captions + CTA)
        8. Upload text đã viết lại lên Google Drive
        9. Tạo text không có timeline (chỉ nội dung chính)
        10. Tạo gợi ý tiêu đề, captions, CTA (không có icon)
        11. Cập nhật kết quả lên Google Sheets (2 cột mới: Text no timeline + Gợi ý tiêu đề)

Tính năng mới:
- Tự động phát hiện ngôn ngữ (tiếng Việt/tiếng Trung)
- Dịch tiếng Trung sang tiếng Việt tự động
- Hỗ trợ xử lý nhiều video cùng lúc
- Cập nhật kết quả lên Google Sheets
- Timeline trong text extraction (giây 1-3: xin chào... giây 4-9: giới thiệu...)
- Viết lại text với cấu trúc đầy đủ: 5 tiêu đề + nội dung timeline + captions + CTA
- Tạo text không có timeline (chỉ nội dung chính, chia đoạn rõ ràng)
- Tạo gợi ý tiêu đề, captions, CTA riêng biệt (không có icon)

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import os
import sys
import logging
import tempfile
import shutil
import subprocess
import requests
import json
import re
import signal
import atexit
from typing import List, Dict, Tuple

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

# Import VideoStatusChecker
from video_checker import VideoStatusChecker

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('all_in_one.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AllInOneProcessor:
    """
    Lớp xử lý tất cả trong một: Video -> Voice Only -> Text -> Rewrite -> TTS -> Drive
    
    Chức năng chính:
    - Xác thực với Google Drive API
    - Tải video từ Google Drive
    - Tách voice từ video (loại bỏ background music)
    - Chuyển đổi voice thành text bằng Deepgram (hỗ trợ tiếng Việt và tiếng Trung) với timeline
    - Dịch tiếng Trung sang tiếng Việt
    - Viết lại text bằng Gemini (cấu trúc đầy đủ: 5 tiêu đề + nội dung timeline + captions + CTA)
    - Tạo text không có timeline (chỉ nội dung chính, chia đoạn rõ ràng)
    - Tạo gợi ý tiêu đề, captions, CTA riêng biệt (không có icon)
    - Upload tất cả file lên Google Drive
    - Cập nhật kết quả lên Google Sheets (2 cột mới: Text no timeline + Gợi ý tiêu đề)
    """
    
    def __init__(self):
        # Đăng ký signal handler để xử lý dừng an toàn
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.cleanup)
        
        # Flag để kiểm tra xem có đang dừng không
        self._shutdown_requested = False
        
        """
        Khởi tạo processor với các API keys và services
        """
        
        # API Keys đã được cấu hình sẵn
        self.deepgram_api_key = '62577e5f53dd9757f0e88250e7326f78281bfa5b'  # Deepgram API key
        self.gemini_api_key = 'AIzaSyAYJxS00MlUoO4E3RBIms2D26hoDgOHRRo'  # Gemini API key
        #api3: AIzaSyDv15UVxgZBUJCDNBU946zEJ03W1y4wp58
        # api1: AIzaSyCNdaVmt9KwMN0mEfSSEQ37oG8U5T088JU (Project cũ)
        # api2: AIzaSyA_SI7BvZlJGFHKNI4OF4JTvOlcs1mC7Mw (Project hiện tại)
        
        logger.info(f"🔑 Sử dụng Gemini API key: {self.gemini_api_key[:20]}...")
        
        # Deepgram TTS API key (cùng với STT) - ĐÃ COMMENT
        # self.deepgram_tts_api_key = 'bb69898295e896c0123d4cdd01a43fdcb78b7b4b'
        
        # Google Sheets ID - Thay đổi nếu cần
        self.spreadsheet_id = '1y4Gmc58DCRmnyO9qNlSBklkvebL5mY9gLlOqcP91Epg'
        self.sheet_name = 'Mp3 to text'  # Tên sheet chính xác theo yêu cầu của người dùng
        # Thử với tên sheet khác nếu lỗi
        # Có thể tên sheet có khoảng trắng, sẽ thử với tên khác nếu lỗi
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        # Hoặc có thể tên sheet là "Mp3 to text" hoặc "mp3 to text"
        
        # Sheet IDs để tránh lỗi parse range với tên có khoảng trắng
        self.main_sheet_id = 0  # Sheet "Mp3 to text" - gid=0
        self.prompt_sheet_id = 695659214  # Sheet "Prompt" - gid=695659214
        
        # Khởi tạo các biến chính
        self.creds = None  # Google OAuth credentials
        self.drive_service = None  # Google Drive service
        self.sheets_service = None  # Google Sheets service
        self.temp_dir = tempfile.mkdtemp()  # Thư mục tạm để lưu file
        
        # Khởi tạo Google API services
        self._authenticate_google_apis()
        
        # Khởi tạo VideoStatusChecker sau khi có services
        try:
            self.video_checker = VideoStatusChecker(
                self.drive_service, 
                self.sheets_service,
                self.spreadsheet_id,
                self.sheet_name
            )
            logger.info("✅ VideoStatusChecker đã được khởi tạo")
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo VideoStatusChecker: {str(e)}")
            self.video_checker = None
        
    def _signal_handler(self, signum, frame):
        """
        Signal handler để xử lý dừng an toàn
        """
        logger.info(f"🛑 Nhận tín hiệu dừng (signal {signum})")
        logger.info("🔄 Đang dừng chương trình an toàn...")
        self._shutdown_requested = True
        self.cleanup()
        logger.info("✅ Đã dừng chương trình an toàn")
        sys.exit(0)
        
    def _authenticate_google_apis(self):
        """
        Xác thực với Google APIs sử dụng OAuth 2.0
        
        Quy trình:
        1. Kiểm tra token đã lưu trước đó
        2. Nếu token hết hạn thì refresh
        3. Nếu không có token thì tạo mới qua OAuth flow
        4. Lưu token để sử dụng lần sau
        """
        try:
            # Bước 1: Kiểm tra token đã lưu trước đó
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'token.json')
            if os.path.exists(token_path):
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info("Đã tìm thấy token đã lưu")
            
            # Bước 2: Kiểm tra token có hợp lệ không
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    # Token hết hạn nhưng có refresh token -> refresh
                    logger.info("Token hết hạn, đang refresh...")
                    self.creds.refresh(Request())
                else:
                    # Không có token hoặc không refresh được -> tạo mới
                    logger.info("Tạo xác thực OAuth mới...")
                    client_secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                                     'client_secret_884171212678-khtpb7jc4flg2eh6iepd7nt1gp013fgv.apps.googleusercontent.com.json')  # Thay bằng file credentials mới
                    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Bước 3: Lưu token để sử dụng lần sau
                token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'token.json')
                with open(token_path, 'w') as token:
                    token.write(self.creds.to_json())
                logger.info("Đã lưu token mới")
            
            # Bước 4: Khởi tạo Google Drive service
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Bước 5: Khởi tạo Google Sheets service
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
            
            logger.info("✅ Xác thực Google APIs thành công (OAuth)")
            logger.info("✅ Google Drive service đã sẵn sàng")
            logger.info("✅ Google Sheets service đã sẵn sàng")
            
        except Exception as e:
            logger.error(f"❌ Lỗi xác thực Google APIs: {str(e)}")
            raise

    def detect_chinese_characters(self, text: str) -> bool:
        """
        Phát hiện xem text có chứa ký tự tiếng Trung không
        
        Args:
            text: Text cần kiểm tra
            
        Returns:
            True nếu có ký tự tiếng Trung, False nếu không
        """
        # Unicode ranges cho ký tự tiếng Trung
        chinese_ranges = [
            (0x4E00, 0x9FFF),   # CJK Unified Ideographs
            (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
            (0x20000, 0x2A6DF), # CJK Unified Ideographs Extension B
            (0x2A700, 0x2B73F), # CJK Unified Ideographs Extension C
            (0x2B740, 0x2B81F), # CJK Unified Ideographs Extension D
            (0x2B820, 0x2CEAF), # CJK Unified Ideographs Extension E
        ]
        
        for char in text:
            char_code = ord(char)
            for start, end in chinese_ranges:
                if start <= char_code <= end:
                    return True
        return False

    def extract_text_with_language_detection(self, audio_path: str, output_name: str) -> Tuple[str, str, bool]:
        """
        Chuyển đổi MP3 thành text với phát hiện ngôn ngữ
        Ưu tiên tiếng Trung trước, sau đó mới tiếng Việt
        
        Args:
            audio_path: Đường dẫn đến file MP3
            output_name: Tên file output (không có extension)
            
        Returns:
            Tuple (text_path, detected_language, is_chinese)
        """
        try:
            # Tạo tên file output cho text
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_transcript.txt")
            
            logger.info(f"📝 Bắt đầu chuyển đổi audio thành text: {os.path.basename(audio_path)}")
            
            # Kiểm tra file audio có tồn tại và có kích thước > 0
            if not os.path.exists(audio_path):
                raise Exception(f"File audio không tồn tại: {audio_path}")
            
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                raise Exception(f"File audio rỗng: {audio_path}")
            
            logger.info(f"📊 Kích thước file audio: {file_size:,} bytes")
            
            # ƯU TIÊN TIẾNG TRUNG TRƯỚC (theo yêu cầu của user)
            logger.info("🇨🇳 Ưu tiên thử với tiếng Trung trước...")
            transcript_zh, detected_language_zh = self._try_transcription(audio_path, "zh")
            
            # Kiểm tra kết quả tiếng Trung
            is_chinese = self.detect_chinese_characters(transcript_zh)
            logger.info(f"🇨🇳 Kết quả tiếng Trung: '{transcript_zh[:100]}...' (độ dài: {len(transcript_zh)})")
            logger.info(f"🇨🇳 Có ký tự tiếng Trung: {is_chinese}")
            
            # Nếu tiếng Trung có kết quả tốt, sử dụng luôn
            if transcript_zh and len(transcript_zh.strip()) > 10:
                transcript = transcript_zh
                detected_language = detected_language_zh
                logger.info("✅ Sử dụng kết quả tiếng Trung")
            else:
                # Nếu tiếng Trung không có kết quả, thử tiếng Việt
                logger.info("🇻🇳 Thử với tiếng Việt...")
                transcript_vi, detected_language_vi = self._try_transcription(audio_path, "vi")
                logger.info(f"🇻🇳 Kết quả tiếng Việt: '{transcript_vi[:100]}...' (độ dài: {len(transcript_vi)})")
                
                # So sánh và chọn kết quả tốt hơn
                if len(transcript_vi) > len(transcript_zh):
                    transcript = transcript_vi
                    detected_language = detected_language_vi
                    is_chinese = False
                    logger.info("✅ Sử dụng kết quả tiếng Việt")
                else:
                    transcript = transcript_zh
                    detected_language = detected_language_zh
                    logger.info("✅ Giữ kết quả tiếng Trung")
            
            # Kiểm tra kết quả cuối cùng
            if not transcript or len(transcript.strip()) == 0:
                logger.warning("⚠️ Không có transcript nào được tạo!")
                transcript = "Không thể nhận dạng giọng nói từ audio"
            
            # Lưu transcript vào file text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            
            logger.info(f"✅ Chuyển đổi text thành công!")
            logger.info(f"📁 File text: {output_path}")
            logger.info(f"📝 Độ dài text: {len(transcript)} ký tự")
            logger.info(f"🌐 Ngôn ngữ phát hiện: {detected_language}")
            logger.info(f"🇨🇳 Là tiếng Trung: {is_chinese}")
            logger.info(f"📄 Nội dung: {transcript[:200]}...")
            
            return output_path, detected_language, is_chinese
            
        except Exception as e:
            logger.error(f"❌ Lỗi chuyển đổi audio thành text: {str(e)}")
            raise

    def _try_transcription(self, audio_path: str, language: str) -> Tuple[str, str]:
        """
        Thử chuyển đổi audio thành text với ngôn ngữ cụ thể và timeline
        Cải thiện logic để tăng khả năng lấy được timeline
        
        Args:
            audio_path: Đường dẫn đến file audio
            language: Ngôn ngữ ("vi" hoặc "zh")
            
        Returns:
            Tuple (transcript_with_timeline, detected_language)
        """
        try:
            # Bước 1: Preprocess audio để tối ưu cho timeline
            processed_audio_path = self._preprocess_audio_for_timeline(audio_path)
            
            # Bước 2: Gửi audio đã xử lý đến Deepgram
            with open(processed_audio_path, 'rb') as audio_file:
                url = "https://api.deepgram.com/v1/listen"
                headers = {
                    "Authorization": f"Token {self.deepgram_api_key}",
                    "Content-Type": "audio/mpeg"
                }
                
                # Cải thiện tham số cho Deepgram API để tăng khả năng lấy timeline
                params = {
                    "model": "nova-2",
                    "language": language,
                    "punctuate": "true",
                    "utterances": "true",
                    "diarize": "true",
                    "timestamps": "true",  # Thêm timestamps để lấy timeline
                    "smart_format": "true",  # Thêm smart format
                    "filler_words": "false",  # Loại bỏ filler words
                    "profanity_filter": "false",  # Không filter profanity
                    "redact": "false",  # Không redact
                    "search": None,  # Không search
                    "replace": None,  # Không replace
                    "callback": None,  # Không callback
                    "keywords": None,  # Không keywords
                    "interim_results": "false",  # Không interim results
                    "endpointing": "true",  # Bật endpointing
                    "vad_turnoff": "500",  # VAD turnoff 500ms
                    "encoding": "linear16",  # Encoding
                    "channels": "1",  # Mono channel
                    "sample_rate": "16000"  # Sample rate 16kHz
                }
                
                logger.info(f"🔄 Đang gửi request đến Deepgram API với ngôn ngữ: {language} và timeline")
                logger.info(f"📊 Tham số tối ưu cho timeline: {params}")
                response = requests.post(url, headers=headers, params=params, data=audio_file, timeout=600)
                
                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"📄 Response keys: {list(result.keys())}")
                    
                    if 'results' in result:
                        logger.info(f"📊 Results keys: {list(result['results'].keys())}")
                        
                        if 'channels' in result['results']:
                            channels = result['results']['channels']
                            logger.info(f"🎵 Số channels: {len(channels)}")
                            
                            if len(channels) > 0:
                                channel = channels[0]
                                logger.info(f"🎵 Channel keys: {list(channel.keys())}")
                                
                                if 'alternatives' in channel:
                                    alternatives = channel['alternatives']
                                    logger.info(f"📝 Số alternatives: {len(alternatives)}")
                                    
                                    if len(alternatives) > 0:
                                        alt = alternatives[0]
                                        logger.info(f"📝 Alternative keys: {list(alt.keys())}")
                                        
                                        # Cải thiện logic xử lý transcript với timeline
                                        if 'transcript' in alt and 'words' in alt:
                                            transcript = alt['transcript']
                                            words = alt['words']
                                            
                                            # Log chi tiết về words data
                                            logger.info(f"📊 Số words có timestamps: {len(words)}")
                                            if words:
                                                logger.info(f"📊 Word đầu tiên: {words[0]}")
                                                logger.info(f"📊 Word cuối cùng: {words[-1]}")
                                            
                                            # Tạo transcript với timeline
                                            transcript_with_timeline = self._format_transcript_with_timeline(words, transcript)
                                            
                                            logger.info(f"✅ Transcript với timeline và ngôn ngữ {language}: '{transcript_with_timeline[:100]}...'")
                                            return transcript_with_timeline, language
                                        elif 'transcript' in alt:
                                            # Fallback nếu không có words (timeline)
                                            transcript = alt['transcript']
                                            logger.warning(f"⚠️ Không có words data cho timeline với ngôn ngữ {language}")
                                            
                                            # Thử tạo timeline thủ công
                                            try:
                                                # Lấy độ dài audio từ response nếu có
                                                audio_duration = None
                                                if 'metadata' in result and 'duration' in result['metadata']:
                                                    audio_duration = float(result['metadata']['duration'])
                                                    logger.info(f"📊 Độ dài audio từ metadata: {audio_duration} giây")
                                                
                                                transcript_with_manual_timeline = self._create_manual_timeline(transcript, audio_duration)
                                                logger.info(f"✅ Đã tạo timeline thủ công với ngôn ngữ {language}: '{transcript_with_manual_timeline[:100]}...'")
                                                return transcript_with_manual_timeline, language
                                            except Exception as e:
                                                logger.warning(f"⚠️ Không thể tạo timeline thủ công: {str(e)}")
                                                logger.info(f"✅ Sử dụng transcript không có timeline với ngôn ngữ {language}: '{transcript[:100]}...'")
                                                return transcript, language
                                        else:
                                            logger.warning(f"⚠️ Không có transcript trong alternative cho ngôn ngữ {language}")
                                    else:
                                        logger.warning(f"⚠️ Không có alternatives cho ngôn ngữ {language}")
                                else:
                                    logger.warning(f"⚠️ Không có alternatives trong channel cho ngôn ngữ {language}")
                            else:
                                logger.warning(f"⚠️ Không có channels cho ngôn ngữ {language}")
                        else:
                            logger.warning(f"⚠️ Không có channels trong results cho ngôn ngữ {language}")
                    else:
                        logger.warning(f"⚠️ Không có results trong response cho ngôn ngữ {language}")
                        logger.info(f"📄 Full response: {result}")
                    
                    # Nếu không có transcript, trả về chuỗi rỗng
                    logger.warning(f"⚠️ Không thể trích xuất transcript cho ngôn ngữ {language}")
                    return "", language
                else:
                    logger.error(f"❌ Deepgram API lỗi: {response.status_code} - {response.text}")
                    return "", language
                    
        except Exception as e:
            logger.error(f"❌ Lỗi transcription với ngôn ngữ {language}: {str(e)}")
            return "", language
        finally:
            # Cleanup: Xóa file audio đã xử lý nếu khác với file gốc
            try:
                if processed_audio_path != audio_path and os.path.exists(processed_audio_path):
                    os.remove(processed_audio_path)
                    logger.info(f"🧹 Đã xóa file audio đã xử lý: {os.path.basename(processed_audio_path)}")
            except Exception as e:
                logger.warning(f"⚠️ Không thể xóa file audio đã xử lý: {str(e)}")

    def _format_transcript_with_timeline(self, words: List[Dict], transcript: str) -> str:
        """
        Format transcript với timeline từ words data của Deepgram
        Cải thiện logic để tạo timeline chính xác hơn
        
        Args:
            words: Danh sách words từ Deepgram API với timestamps
            transcript: Transcript gốc
            
        Returns:
            Transcript đã format với timeline
        """
        try:
            if not words:
                logger.warning("⚠️ Không có words data để tạo timeline")
                return transcript
            
            logger.info(f"📊 Số words có timestamps: {len(words)}")
            
            # Kiểm tra chất lượng words data
            valid_words = []
            for word_data in words:
                word = word_data.get('word', '').strip()
                start_time = word_data.get('start', 0)
                end_time = word_data.get('end', 0)
                
                # Chỉ lấy words có đầy đủ thông tin
                if word and start_time is not None and end_time is not None:
                    valid_words.append({
                        'word': word,
                        'start': float(start_time),
                        'end': float(end_time)
                    })
            
            logger.info(f"📊 Số words hợp lệ: {len(valid_words)}")
            
            if not valid_words:
                logger.warning("⚠️ Không có words hợp lệ để tạo timeline")
                return transcript
            
            # Cải thiện logic nhóm words theo khoảng thời gian
            timeline_segments = []
            current_segment = []
            current_start = None
            current_end = None
            
            # Ngưỡng thời gian để tạo segment mới (cải thiện độ nhận diện)
            time_threshold = 1.5  # Giảm xuống 1.5 giây để tạo nhiều segment hơn
            
            for word_data in valid_words:
                word = word_data['word']
                start_time = word_data['start']
                end_time = word_data['end']
                
                # Bắt đầu segment mới nếu:
                # 1. Chưa có segment nào
                # 2. Khoảng cách thời gian > threshold
                # 3. Segment hiện tại đã quá dài (> 10 giây)
                segment_duration = 0
                if current_start is not None and current_end is not None:
                    segment_duration = current_end - current_start
                
                if (current_start is None or 
                    (current_end is not None and start_time - current_end > time_threshold) or 
                    segment_duration > 8.0):  # Giảm xuống 8 giây để tạo segment nhỏ hơn
                    
                    # Lưu segment trước đó nếu có nội dung
                    if current_segment and current_start is not None and current_end is not None:
                        segment_text = ' '.join(current_segment)
                        # Giảm yêu cầu từ 3 từ xuống 1 từ để không bỏ sót
                        if len(segment_text.strip()) > 0:
                            timeline_segments.append({
                                'start': current_start,
                                'end': current_end,
                                'text': segment_text
                            })
                    
                    # Bắt đầu segment mới
                    current_segment = [word]
                    current_start = start_time
                    current_end = end_time
                else:
                    current_segment.append(word)
                    current_end = end_time  # Cập nhật end time liên tục
            
            # Thêm segment cuối cùng
            if current_segment and current_start is not None and current_end is not None:
                segment_text = ' '.join(current_segment)
                # Giảm yêu cầu từ 3 từ xuống 1 từ để không bỏ sót
                if len(segment_text.strip()) > 0:
                    timeline_segments.append({
                        'start': current_start,
                        'end': current_end,
                        'text': segment_text
                    })
            
            # Format thành text với timeline
            formatted_text = f"=== TRANSCRIPT VỚI TIMELINE ===\n\n"
            
            for i, segment in enumerate(timeline_segments, 1):
                start_sec = int(segment['start'])
                end_sec = int(segment['end'])
                text = segment['text'].strip()
                
                # Chỉ thêm segment nếu có nội dung (giảm yêu cầu)
                if text and len(text.strip()) > 0:
                    formatted_text += f"(Giây {start_sec}-{end_sec}) {text}\n\n"
            
            # Thêm transcript gốc ở cuối để tham khảo
            formatted_text += f"=== TRANSCRIPT GỐC ===\n{transcript}\n"
            
            # Kiểm tra nếu không có timeline, tạo timeline thủ công
            if len(timeline_segments) == 0:
                logger.warning("⚠️ Không có timeline từ Deepgram, tạo timeline thủ công...")
                manual_timeline = self._create_manual_timeline(transcript)
                if manual_timeline:
                    formatted_text = f"=== TRANSCRIPT VỚI TIMELINE (THỦ CÔNG) ===\n\n{manual_timeline}\n\n{formatted_text}"
            
            logger.info(f"✅ Đã tạo transcript với {len(timeline_segments)} segments timeline")
            logger.info(f"📊 Timeline segments: {[(s['start'], s['end']) for s in timeline_segments]}")
            return formatted_text
            
        except Exception as e:
            logger.error(f"❌ Lỗi format timeline: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return transcript

    def _preprocess_audio_for_timeline(self, audio_path: str) -> str:
        """
        Xử lý audio để tăng khả năng nhận diện timeline
        Cải thiện chất lượng audio trước khi gửi đến Deepgram
        
        Args:
            audio_path: Đường dẫn đến file audio gốc
            
        Returns:
            Đường dẫn đến file audio đã xử lý
        """
        try:
            import subprocess
            import os
            
            # Tạo tên file output
            base_name = os.path.splitext(audio_path)[0]
            processed_audio_path = f"{base_name}_processed_for_timeline.wav"
            
            logger.info(f"🔧 Đang xử lý audio để tối ưu cho timeline: {os.path.basename(audio_path)}")
            
            # Sử dụng FFmpeg để cải thiện audio
            # 1. Chuyển sang WAV format (Deepgram ưa thích)
            # 2. Mono channel (1 kênh)
            # 3. Sample rate 16kHz
            # 4. Giảm tiếng ồn
            # 5. Tăng độ rõ của giọng nói
            
            # Tìm đường dẫn FFmpeg
            ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'ffmpeg.exe')
            if not os.path.exists(ffmpeg_path):
                # Thử tìm trong PATH
                import shutil
                ffmpeg_path = shutil.which('ffmpeg')
                if not ffmpeg_path:
                    logger.warning("⚠️ Không tìm thấy FFmpeg, sử dụng audio gốc")
                    return audio_path
            
            cmd = [
                ffmpeg_path, '-y',  # Overwrite output file
                '-i', audio_path,  # Input file
                '-ac', '1',  # Mono channel
                '-ar', '16000',  # Sample rate 16kHz
                '-af', 'highpass=f=200,lowpass=f=3000,volume=1.5',  # Audio filters
                '-c:a', 'pcm_s16le',  # PCM 16-bit
                processed_audio_path
            ]
            
            logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
            
            # Chạy FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"✅ Đã xử lý audio thành công: {os.path.basename(processed_audio_path)}")
                return processed_audio_path
            else:
                logger.warning(f"⚠️ FFmpeg lỗi: {result.stderr}")
                logger.info(f"📝 Sử dụng audio gốc: {os.path.basename(audio_path)}")
                return audio_path
                
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý audio: {str(e)}")
            logger.info(f"📝 Sử dụng audio gốc: {os.path.basename(audio_path)}")
            return audio_path

    def _create_manual_timeline(self, transcript: str, audio_duration: float = None) -> str:
        """
        Tạo timeline thủ công khi không có words data từ Deepgram
        
        Args:
            transcript: Transcript gốc
            audio_duration: Độ dài audio (giây), nếu không có sẽ ước tính
            
        Returns:
            Transcript với timeline thủ công
        """
        try:
            if not transcript or len(transcript.strip()) == 0:
                return transcript
            
            # Ước tính độ dài audio nếu không có
            if audio_duration is None:
                # Ước tính dựa trên số từ (điều chỉnh theo ngữ cảnh)
                word_count = len(transcript.split())
                # Điều chỉnh tốc độ nói: 120-180 từ/phút tùy ngữ cảnh
                words_per_minute = 150  # Mặc định
                if word_count < 50:
                    words_per_minute = 120  # Nói chậm hơn cho đoạn ngắn
                elif word_count > 200:
                    words_per_minute = 180  # Nói nhanh hơn cho đoạn dài
                
                audio_duration = (word_count / words_per_minute) * 60  # Chuyển sang giây
                logger.info(f"📊 Ước tính độ dài audio: {audio_duration:.1f} giây từ {word_count} từ (tốc độ {words_per_minute} từ/phút)")
            
            # Chia transcript thành các câu (hỗ trợ cả tiếng Việt và tiếng Trung)
            # Dấu câu tiếng Việt: .!?
            # Dấu câu tiếng Trung: 。！？
            sentences = re.split(r'[.!?。！？]+', transcript)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return transcript
            
            # Tính thời gian cho mỗi câu
            total_sentences = len(sentences)
            time_per_sentence = audio_duration / total_sentences
            
            # Tạo timeline thủ công
            formatted_text = f"=== TRANSCRIPT VỚI TIMELINE (THỦ CÔNG) ===\n\n"
            
            current_time = 0
            for i, sentence in enumerate(sentences):
                if not sentence:
                    continue
                
                # Tính thời gian cho câu này
                sentence_duration = time_per_sentence
                if i == total_sentences - 1:
                    # Câu cuối cùng lấy hết thời gian còn lại
                    sentence_duration = audio_duration - current_time
                
                end_time = current_time + sentence_duration
                
                # Format timeline
                start_sec = int(current_time)
                end_sec = int(end_time)
                
                formatted_text += f"(Giây {start_sec}-{end_sec}) {sentence}.\n\n"
                
                current_time = end_time
            
            # Thêm transcript gốc
            formatted_text += f"=== TRANSCRIPT GỐC ===\n{transcript}\n"
            
            logger.info(f"✅ Đã tạo timeline thủ công với {len(sentences)} câu")
            return formatted_text
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo timeline thủ công: {str(e)}")
            return transcript

    def translate_chinese_to_vietnamese(self, text_path: str, output_name: str) -> str:
        """
        Dịch text tiếng Trung sang tiếng Việt bằng Gemini API với độ chính xác cao

Áp dụng phương pháp dịch "sát nghĩa" + tối ưu cho nội dung nội thất:
1. Tham số ít bay bổng (temperature: 0-0.2, top_p: 0.2-0.4, top_k: 1)
2. Bảng thuật ngữ nội thất & kiến trúc để giữ nghĩa nhất quán
3. Dịch theo từng câu hoặc đoạn ngắn kèm ngữ cảnh video/nội dung
4. QA trung thành: Kiểm tra lại bản dịch để loại bỏ từ Hán Việt khó hiểu, chỉnh câu mượt hơn
5. Giữ tone chuyên nghiệp, phù hợp với bài giới thiệu nội thất

Args:
    text_path: Đường dẫn đến file text tiếng Trung
    output_name: Tên file output (không có extension)

Returns:
    Đường dẫn đến file text đã dịch
        """
        try:
            # Tạo tên file output cho text đã dịch
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_translated.txt")
            
            logger.info(f"🔄 Đang dịch text tiếng Trung sang tiếng Việt (chế độ sát nghĩa): {os.path.basename(text_path)}")
            
            # Đọc text tiếng Trung từ file
            with open(text_path, 'r', encoding='utf-8') as f:
                chinese_text = f.read()
            
            # Bước 1: Chuẩn bị văn bản để dịch
            sentences_with_context = self._prepare_sentences_with_context(chinese_text)
            
            # Bước 2: Dịch nguyên bản sát nghĩa
            translated_sentences = []
            for i, (text, context, has_timeline) in enumerate(sentences_with_context):
                logger.info(f"📝 Đang dịch văn bản {i+1}/{len(sentences_with_context)}")
                
                # Dịch với bảo toàn timeline
                translated_text = self._translate_sentence_with_timeline(text, context)
                translated_sentences.append(translated_text)
            
            # Bước 3: Ghép lại thành văn bản hoàn chỉnh
            final_translation = ' '.join(translated_sentences)
            
            # Bước 4: QA trung thành - kiểm tra và sửa lỗi
            logger.info("🔍 Bước QA trung thành - kiểm tra và sửa lỗi...")
            final_translation = self._qa_fidelity_check_with_timeline(chinese_text, final_translation)
            
            # Lưu text đã dịch vào file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_translation)
            
            logger.info(f"✅ Dịch text thành công (chế độ sát nghĩa)!")
            logger.info(f"📁 File: {output_path}")
            logger.info(f"📝 Độ dài text: {len(final_translation)} ký tự")
            logger.info(f"📄 Nội dung: {final_translation[:200]}...")
            
            return output_path
                
        except Exception as e:
            logger.error(f"❌ Lỗi dịch text: {str(e)}")
            raise

    def _prepare_sentences_with_context(self, text: str) -> List[Tuple[str, str]]:
        """
        Chuẩn bị văn bản để dịch - ĐƠN GIẢN HÓA: Dịch nguyên bản sát nghĩa
        
        Args:
            text: Văn bản tiếng Trung gốc
            
        Returns:
            List các tuple (văn bản, ngữ cảnh)
        """
        try:
            # Không tách câu, chỉ trả về văn bản nguyên bản
            return [(text, "", True)]  # True = có thể có timeline
            
        except Exception as e:
            logger.error(f"❌ Lỗi chuẩn bị văn bản: {str(e)}")
            return [(text, "", True)]

    def _get_terminology_table(self) -> str:
        """
        Tạo bảng thuật ngữ chuyên ngành Trung-Việt
        
        Returns:
            Bảng thuật ngữ dạng string
        """
        # Bảng thuật ngữ chuyên ngành - có thể mở rộng theo nhu cầu
        terminology = """
=== BẢNG THUẬT NGỮ CHUYÊN NGÀNH (TRUNG → VIỆT) ===

# Thuật ngữ xây dựng / thiết kế:
设计 = thiết kế
建筑 = kiến trúc
施工 = thi công
装修 = hoàn thiện nội thất / trang trí nội thất
材料 = vật liệu
结构 = kết cấu
空间 = không gian
布局 = bố cục
风格 = phong cách
方案 = phương án
采光 = lấy sáng / chiếu sáng tự nhiên
隔断 = vách ngăn
承重墙 = tường chịu lực
非承重墙 = tường không chịu lực
吊顶 = trần thả / trần trang trí
地板 = sàn nhà
墙面 = tường
瓷砖 = gạch men
木饰面 = ốp gỗ
护墙板 = ốp tường

# Thuật ngữ phòng / khu vực:
玄关 = khu vực lối vào nhà
客厅 = phòng khách
餐厅 = phòng ăn
卧室 = phòng ngủ
主卧 = phòng ngủ chính
次卧 = phòng ngủ phụ
厨房 = bếp
开放式厨房 = bếp mở
阳台 = ban công
飘窗 = bệ cửa sổ
书房 = phòng làm việc / phòng đọc sách
卫生间 = nhà vệ sinh / phòng tắm
浴室 = phòng tắm

# Thuật ngữ tủ / đồ nội thất (PHÂN BIỆT RÕ):
鞋柜 = tủ giày (KHÔNG phải nhà kho)
储物柜 = tủ đựng đồ
衣柜 = tủ quần áo
书柜 = tủ sách
电视柜 = tủ tivi
床头柜 = tủ đầu giường
餐边柜 = tủ trưng bày
展示柜 = tủ trưng bày
收纳柜 = tủ cất trữ

# Thuật ngữ thông dụng:
我们 = chúng tôi
您 = bạn / ông / bà
这个 = cái này
那个 = cái kia
可以 = có thể
需要 = cần
应该 = nên
必须 = phải
建议 = đề xuất
考虑 = cân nhắc

# Thuật ngữ đánh giá:
很好 = rất tốt
不错 = không tệ
一般 = bình thường
差 = kém
优秀 = xuất sắc
实用 = tiện dụng
美观 = thẩm mỹ / đẹp mắt
舒适 = thoải mái

# Thuật ngữ thời gian:
现在 = bây giờ
以前 = trước đây
以后 = sau này
马上 = ngay lập tức
慢慢 = từ từ

# Thuật ngữ số lượng:
一些 = một số
很多 = nhiều
全部 = tất cả
部分 = một phần
大约 = khoảng

# Thuật ngữ phong cách hô:
师傅 = thầy / chú (người có kinh nghiệm, thợ)
老板 = ông chủ
客户 = khách hàng
朋友 = bạn bè
家人 = gia đình
"""

        return terminology

    def _translate_single_sentence(self, sentence: str, context: str) -> str:
        """
        Dịch một câu với ngữ cảnh và bảng thuật ngữ
        
        Args:
            sentence: Câu cần dịch
            context: Ngữ cảnh (50-300 ký tự trước đó)
            
        Returns:
            Câu đã dịch
        """
        try:
            # Chuẩn bị request đến Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
            
            # Lấy bảng thuật ngữ
            terminology = self._get_terminology_table()
            
            # Prompt chi tiết cho dịch sát nghĩa
            prompt = f"""

=== HƯỚNG DẪN DỊCH SÁT NGHĨA ===

Bạn là biên dịch viên chuyên nghiệp, chuyên dịch các tài liệu và video tiếng Trung sang tiếng Việt, đặc biệt trong lĩnh vực nội thất và kiến trúc.

{terminology}

=== QUY TẮC DỊCH CẢI THIỆN ===
1. **PHÂN TÍCH BỐI CẢNH TRƯỚC KHI DỊCH**: Hiểu rõ ngữ cảnh video (thiết kế nội thất, tủ giày, phòng khách, bếp...)
2. **Ưu tiên chính xác**: Dịch sát nghĩa, đảm bảo giữ nguyên thông tin gốc, không thêm ý tưởng ngoài văn bản.
3. **Tôn trọng bảng thuật ngữ**: Sử dụng đúng nghĩa đã định trong bảng thuật ngữ, đặc biệt các thuật ngữ nội thất.
4. **PHÂN BIỆT TỪ NGỮ TƯƠNG TỰ**: 
   - 鞋柜 (xié guì) = tủ giày (KHÔNG phải nhà kho)
   - 储物柜 (chǔ wù guì) = tủ đựng đồ
   - 玄关 (xuán guān) = khu vực lối vào nhà
   - 客厅 (kè tīng) = phòng khách
   - 厨房 (chú fáng) = bếp
5. **Không dịch tên riêng**: Giữ nguyên tên người, địa danh, thương hiệu.
6. **Giữ phong cách hô**: Duy trì cách xưng hô và giọng điệu phù hợp với ngữ cảnh.
7. **Giữ nguyên bố cục và ý**: Dịch nguyên văn theo câu và đoạn, không gộp hoặc tách nếu không cần thiết.
8. **Tự nhiên & dễ hiểu**: Chuyển các từ Hán Việt ít thông dụng sang từ thuần Việt.

=== VĂN BẢN CẦN DỊCH ===
{sentence}

=== YÊU CẦU ===
- Chỉ trả về bản dịch tiếng Việt, không kèm giải thích.
- Giữ nguyên cấu trúc đoạn và câu.
- Sử dụng tiếng Việt mạch lạc, tự nhiên và chuyên nghiệp.
- Dịch sát nghĩa nhất có thể.
- ĐẶC BIỆT CHÚ Ý: Phân biệt rõ tủ giày, tủ đựng đồ, nhà kho, khu vực lối vào...
"""

            
            # Tham số ít bay bổng cho độ chính xác cao
            data = {
    "contents": [
        {
            "parts": [
                {
                    "text": prompt
                }
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.1,   # Ít sáng tạo, sát nghĩa
        "topP": 0.3,          # Tập trung vào từ/cụm phù hợp nhất
        "topK": 1,            # Chọn kết quả tối ưu
        "maxOutputTokens": 1500  # Tăng giới hạn nếu văn bản dài
    }
            }
            
            # Gửi request đến Gemini API
            response = requests.post(url, json=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                translated_sentence = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return translated_sentence
            else:
                logger.warning(f"⚠️ Lỗi API cho câu: {sentence[:50]}...")
                return sentence  # Trả về câu gốc nếu lỗi
                
        except Exception as e:
            logger.error(f"❌ Lỗi dịch câu: {str(e)}")
            return sentence  # Trả về câu gốc nếu lỗi

    def _translate_sentence_with_timeline(self, text: str, context: str) -> str:
        """
        Dịch văn bản tiếng Trung có timeline sang tiếng Việt
        ĐƠN GIẢN HÓA: Dịch nguyên bản sát nghĩa, bảo toàn timeline
        
        Args:
            text: Văn bản tiếng Trung có timeline cần dịch
            context: Ngữ cảnh (không sử dụng)
            
        Returns:
            Văn bản đã dịch sang tiếng Việt với timeline được bảo toàn
        """
        try:
            import re
            
            # Bước 1: Tách tất cả timeline và nội dung
            timeline_pattern = r'\(Giây\s+\d+-\d+\)'
            timeline_matches = list(re.finditer(timeline_pattern, text))
            
            if not timeline_matches:
                # Không có timeline, dịch toàn bộ văn bản
                return self._translate_single_sentence(text, context)
            
            logger.info(f"📊 Tìm thấy {len(timeline_matches)} timeline trong văn bản")
            
            # Bước 2: Tách văn bản thành các phần
            parts = re.split(timeline_pattern, text)
            timelines = [match.group(0) for match in timeline_matches]
            
            # Bước 3: Dịch từng phần nội dung và ghép lại với timeline
            translated_parts = []
            
            # Phần đầu (trước timeline đầu tiên)
            if parts[0].strip():
                translated_first_part = self._translate_single_sentence(parts[0].strip(), context)
                if translated_first_part:
                    translated_parts.append(translated_first_part)
            
            # Các phần có timeline
            for i, (part, timeline) in enumerate(zip(parts[1:], timelines)):
                if part.strip():
                    translated_part = self._translate_single_sentence(part.strip(), context)
                    translated_parts.append(f"{timeline} {translated_part}")
                else:
                    translated_parts.append(timeline)
            
            # Bước 4: Ghép lại thành văn bản hoàn chỉnh
            final_text = ' '.join(translated_parts)
            
            logger.info(f"📊 Kết quả dịch có timeline: {len(timeline_matches)} segments")
            return final_text
                
        except Exception as e:
            logger.error(f"❌ Lỗi dịch văn bản có timeline: {str(e)}")
            return text  # Trả về văn bản gốc nếu lỗi

    def _qa_fidelity_check(self, original_text: str, translated_text: str) -> str:
        """
        QA trung thành - kiểm tra và sửa lỗi dịch
        
        Args:
            original_text: Văn bản tiếng Trung gốc
            translated_text: Văn bản tiếng Việt đã dịch
            
        Returns:
            Văn bản đã sửa lỗi
        """
        try:
            # Chuẩn bị request đến Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
            
            prompt = f"""
            === QA TRUNG THÀNH - KIỂM TRA DỊCH THUẬT ===
            
            Bạn là chuyên gia kiểm tra chất lượng dịch thuật. Nhiệm vụ: So sánh văn bản gốc và bản dịch, tìm lỗi và sửa.
            
            === VĂN BẢN GỐC (TIẾNG TRUNG) ===
            {original_text}
            
            === BẢN DỊCH (TIẾNG VIỆT) ===
            {translated_text}
            
            === YÊU CẦU KIỂM TRA ===
            1. **Thiếu**: Nội dung gốc có nhưng dịch thiếu
            2. **Thừa**: Nội dung dịch có nhưng gốc không có
            3. **Sai**: Dịch sai ý nghĩa hoặc thuật ngữ
            4. **Tên riêng**: Có dịch nhầm tên riêng không
            5. **Ngữ cảnh**: Có phù hợp với ngữ cảnh không
            
            === HƯỚNG DẪN SỬA ===
            - Liệt kê các lỗi tìm thấy
            - Đưa ra bản dịch đã sửa
            - Giữ nguyên cấu trúc và timeline
            - Chỉ sửa lỗi, không thay đổi nội dung đúng
            
            === ĐỊNH DẠNG TRẢ LỜI ===
            LỖI TÌM THẤY:
            [Liệt kê các lỗi]
            
            BẢN DỊCH ĐÃ SỬA:
            [Bản dịch hoàn chỉnh đã sửa lỗi]
            """
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.3,
                    "topK": 1,
                    "maxOutputTokens": 2000
                }
            }
            
            # Gửi request đến Gemini API
            response = requests.post(url, json=data, timeout=180)
            
            if response.status_code == 200:
                result = response.json()
                qa_result = result['candidates'][0]['content']['parts'][0]['text']
                
                # Trích xuất bản dịch đã sửa từ kết quả QA
                if "BẢN DỊCH ĐÃ SỬA:" in qa_result:
                    parts = qa_result.split("BẢN DỊCH ĐÃ SỬA:")
                    if len(parts) > 1:
                        corrected_translation = parts[1].strip()
                        logger.info("✅ QA trung thành hoàn tất - đã sửa lỗi")
                        return corrected_translation
                
                # Nếu không tìm thấy phần sửa, trả về bản dịch gốc
                logger.info("ℹ️ QA trung thành - không tìm thấy lỗi cần sửa")
                return translated_text
            else:
                logger.warning("⚠️ QA trung thành thất bại - giữ nguyên bản dịch gốc")
                return translated_text
                
        except Exception as e:
            logger.error(f"❌ Lỗi QA trung thành: {str(e)}")
            return translated_text  # Trả về bản dịch gốc nếu lỗi

    def _qa_fidelity_check_with_timeline(self, original_text: str, translated_text: str) -> str:
        """
        QA trung thành với bảo toàn timeline - kiểm tra và sửa lỗi dịch
        CẢI THIỆN: Đặc biệt chú ý bảo toàn timeline
        
        Args:
            original_text: Văn bản tiếng Trung gốc
            translated_text: Văn bản tiếng Việt đã dịch
            
        Returns:
            Văn bản đã sửa lỗi với timeline được bảo toàn
        """
        try:
            import re
            
            # Bước 1: Kiểm tra timeline trong văn bản gốc
            timeline_pattern = r'\(Giây\s+\d+-\d+\)'
            original_timelines = re.findall(timeline_pattern, original_text)
            translated_timelines = re.findall(timeline_pattern, translated_text)
            
            logger.info(f"📊 Timeline trong văn bản gốc: {len(original_timelines)}")
            logger.info(f"📊 Timeline trong văn bản dịch: {len(translated_timelines)}")
            
            # Bước 2: Nếu thiếu timeline, thêm lại
            if len(original_timelines) > len(translated_timelines):
                logger.warning("⚠️ Phát hiện thiếu timeline, đang khôi phục...")
                
                # Tách văn bản thành các phần có timeline
                parts = re.split(timeline_pattern, original_text)
                timelines = re.findall(timeline_pattern, original_text)
                
                # Ghép lại với timeline
                restored_text = ""
                for i, (part, timeline) in enumerate(zip(parts[1:], timelines)):  # Bỏ qua phần đầu
                    # Dịch phần nội dung
                    if part.strip():
                        translated_part = self._translate_single_sentence(part.strip(), "")
                    else:
                        translated_part = ""
                    
                    # Ghép timeline + nội dung đã dịch
                    restored_text += f"{timeline} {translated_part}\n\n"
                
                logger.info("✅ Đã khôi phục timeline thành công")
                return restored_text.strip()
            
            # Bước 3: QA bình thường nếu timeline đã đầy đủ
            return self._qa_fidelity_check(original_text, translated_text)
                
        except Exception as e:
            logger.error(f"❌ Lỗi QA với timeline: {str(e)}")
            return translated_text  # Trả về bản dịch gốc nếu lỗi
    
    def find_video_in_folder(self, folder_id: str, video_name: str = "video1.mp4") -> Dict:
        """
        Tìm video trong Google Drive folder
        
        Args:
            folder_id: ID của folder trên Google Drive
            video_name: Tên file video cần tìm
            
        Returns:
            Dict chứa thông tin video hoặc None nếu không tìm thấy
        """
        try:
            # Tạo query để tìm file trong folder
            query = f"'{folder_id}' in parents and name='{video_name}'"
            
            # Gọi Google Drive API để tìm file
            results = self.drive_service.files().list(
                q=query,
                fields="files(id,name,size,mimeType)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            
            # Kiểm tra kết quả
            if not files:
                logger.warning(f"❌ Không tìm thấy video {video_name} trong folder {folder_id}")
                return None
            
            # Lấy thông tin video đầu tiên tìm thấy
            video_info = files[0]
            logger.info(f"✅ Tìm thấy video: {video_info['name']} (ID: {video_info['id']}, Size: {video_info.get('size', 'Unknown')} bytes)")
            
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Lỗi tìm video: {str(e)}")
            return None
    
    def get_all_videos_in_folder(self, folder_id: str) -> List[Dict]:
        """
        Lấy tất cả video trong Google Drive folder
        
        Args:
            folder_id: ID của folder trên Google Drive
            
        Returns:
            List chứa thông tin tất cả video
        """
        try:
            # Tạo query để tìm tất cả file video trong folder
            query = f"'{folder_id}' in parents and (mimeType contains 'video/' or name contains '.mp4' or name contains '.avi' or name contains '.mov')"
            
            logger.info(f"🔍 Tìm kiếm video trong folder ID: {folder_id}")
            logger.info(f"🔍 Query: {query}")
            
            # Gọi Google Drive API để tìm file
            results = self.drive_service.files().list(
                q=query,
                fields="files(id,name,size,mimeType,trashed)",
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📄 Tổng số file tìm thấy: {len(files)}")
            
            # Hiển thị tất cả file để debug
            for i, file in enumerate(files):
                name = file.get('name', 'Unknown')
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 'Unknown')
                trashed = file.get('trashed', False)
                logger.info(f"  {i+1}. {name} (MIME: {mime_type}, Size: {size}, Trashed: {trashed})")
            
            # Lọc chỉ lấy file video (không bị xóa)
            video_files = []
            for file in files:
                name = file.get('name', '').lower()
                mime_type = file.get('mimeType', '')
                trashed = file.get('trashed', False)
                
                # Bỏ qua file đã bị xóa
                if trashed:
                    logger.info(f"⏭️ Bỏ qua file đã xóa: {file.get('name', 'Unknown')}")
                    continue
                
                # Kiểm tra có phải file video không
                if (mime_type.startswith('video/') or 
                    name.endswith('.mp4') or 
                    name.endswith('.avi') or 
                    name.endswith('.mov') or
                    name.endswith('.mkv')):
                    video_files.append(file)
                    logger.info(f"✅ Thêm video: {file.get('name', 'Unknown')}")
                else:
                    logger.info(f"⏭️ Bỏ qua file không phải video: {file.get('name', 'Unknown')} (MIME: {mime_type})")
            
            logger.info(f"📁 Tìm thấy {len(video_files)} video trong folder")
            for video in video_files:
                logger.info(f"  - {video['name']} (ID: {video['id']}, Size: {video.get('size', 'Unknown')} bytes)")
            
            return video_files
            
        except Exception as e:
            logger.error(f"❌ Lỗi lấy danh sách video: {str(e)}")
            return []
    
    def download_video(self, file_id: str, video_name: str) -> str:
        """
        Tải video từ Google Drive về máy local
        
        Args:
            file_id: ID của file trên Google Drive
            video_name: Tên file để lưu
            
        Returns:
            Đường dẫn đến file video đã tải
        """
        try:
            # Tạo thư mục tạm nếu chưa có
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()
                logger.info(f"Đã tạo thư mục tạm: {self.temp_dir}")
            
            # Đường dẫn file video sẽ lưu
            video_path = os.path.join(self.temp_dir, f"{video_name}")
            
            logger.info(f"🔄 Đang tải video: {video_name}")
            
            # Tải file từ Google Drive
            request = self.drive_service.files().get_media(fileId=file_id)
            with open(video_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"📥 Tải: {int(status.progress() * 100)}%")
            
            logger.info(f"✅ Tải video thành công: {video_path}")
            return video_path
            
        except Exception as e:
            logger.error(f"❌ Lỗi tải video: {str(e)}")
            raise
    
    def convert_to_mp3(self, video_path: str, output_name: str) -> str:
        """
        Chuyển đổi video thành MP3 bằng FFmpeg
        
        Args:
            video_path: Đường dẫn đến file video
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file MP3 đã tạo
        """
        try:
            # Tạo tên file MP3 output
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}.mp3")
            
            logger.info(f"🔄 Đang tách audio từ: {os.path.basename(video_path)}")
            
            # Lệnh FFmpeg để chuyển đổi video thành MP3
            cmd = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "ffmpeg.exe"),  # Đường dẫn FFmpeg
                "-i", video_path,  # Input file
                "-vn",  # Không có video
                "-acodec", "mp3",  # Codec audio MP3
                "-ab", "192k",  # Bitrate 192k
                "-ar", "44100",  # Sample rate 44.1kHz
                "-y",  # Ghi đè file nếu tồn tại
                output_path  # Output file
            ]
            
            # Chạy lệnh FFmpeg
            logger.info("Đang chạy FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            # Kiểm tra kết quả
            if result.returncode == 0:
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"✅ Tách MP3 thành công!")
                    logger.info(f"📁 File: {output_path}")
                    logger.info(f"📊 Kích thước: {file_size:,} bytes")
                    return output_path
                else:
                    raise Exception("Không tạo được file MP3")
            else:
                raise Exception(f"FFmpeg lỗi: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Lỗi chuyển đổi video: {str(e)}")
            raise
    
    def extract_voice_only(self, video_path: str, output_name: str) -> str:
        """
        Tách voice từ video, loại bỏ background music
        
        Sử dụng FFmpeg với filter nâng cao để:
        1. Tách voice khỏi background music
        2. Sử dụng filter phức tạp để nhận diện voice
        3. Tối ưu chất lượng voice cho text recognition
        
        Args:
            video_path: Đường dẫn đến file video
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file MP3 chỉ có voice
        """
        try:
            # Tạo tên file voice output
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_voice_only.mp3")
            
            logger.info(f"🎤 Đang tách voice từ: {os.path.basename(video_path)}")
            logger.info("🔧 Sử dụng filter nâng cao để loại bỏ background music...")
            
            # Lệnh FFmpeg nâng cao để tách voice
            # Sử dụng filter phức tạp hơn để nhận diện và tách voice
            cmd = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "ffmpeg.exe"),  # Đường dẫn FFmpeg
                "-i", video_path,  # Input file
                "-vn",  # Không có video
                "-af", "highpass=f=150,lowpass=f=4000,volume=2.0,anlmdn=s=7:p=0.002:r=0.01",  # Filter nâng cao
                "-acodec", "mp3",  # Codec audio MP3
                "-ab", "192k",  # Bitrate cao hơn cho chất lượng tốt
                "-ar", "44100",  # Sample rate cao hơn
                "-ac", "1",  # Mono channel cho voice
                "-y",  # Ghi đè file nếu tồn tại
                output_path  # Output file
            ]
            
            # Chạy lệnh FFmpeg
            logger.info("Đang chạy FFmpeg với voice filter nâng cao...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # Timeout dài hơn
            
            # Kiểm tra kết quả
            if result.returncode == 0:
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"✅ Tách voice thành công!")
                    logger.info(f"📁 File voice: {output_path}")
                    logger.info(f"📊 Kích thước: {file_size:,} bytes")
                    return output_path
                else:
                    raise Exception("Không tạo được file voice")
            else:
                # Nếu filter phức tạp thất bại, thử filter đơn giản hơn
                logger.warning("⚠️ Filter phức tạp thất bại, thử filter đơn giản...")
                return self._extract_voice_simple(video_path, output_name)
                
        except Exception as e:
            logger.error(f"❌ Lỗi tách voice: {str(e)}")
            # Fallback về phương pháp đơn giản
            return self._extract_voice_simple(video_path, output_name)
    
    def _extract_voice_simple(self, video_path: str, output_name: str) -> str:
        """
        Phương pháp đơn giản để tách voice (fallback)
        
        Sử dụng filter cơ bản để tách voice:
        - Highpass filter: loại bỏ tần số thấp (bass)
        - Lowpass filter: loại bỏ tần số cao (treble)
        - Volume boost: tăng âm lượng voice
        """
        try:
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_voice_simple.mp3")
            
            logger.info("🔄 Thử phương pháp tách voice đơn giản...")
            
            # Lệnh FFmpeg đơn giản để tách voice
            cmd = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "ffmpeg.exe"),
                "-i", video_path,
                "-vn",
                "-af", "highpass=f=300,lowpass=f=2000,volume=2.0",  # Filter đơn giản
                "-acodec", "mp3",
                "-ab", "96k",  # Bitrate thấp cho voice
                "-ar", "16000",  # Sample rate thấp
                "-ac", "1",  # Mono
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✅ Tách voice đơn giản thành công!")
                logger.info(f"📁 File: {output_path}")
                logger.info(f"📊 Kích thước: {file_size:,} bytes")
                return output_path
            else:
                raise Exception(f"FFmpeg lỗi: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Lỗi tách voice đơn giản: {str(e)}")
            raise
    
    def mp3_to_text(self, audio_path: str, output_name: str) -> str:
        """
        Chuyển đổi MP3 thành text bằng Deepgram API (Legacy method - kept for compatibility)
        Args:
            audio_path: Đường dẫn đến file MP3
            output_name: Tên file output (không có extension)
        Returns:
            Đường dẫn đến file text đã tạo
        """
        try:
            # Sử dụng method mới với language detection
            text_path, _, _ = self.extract_text_with_language_detection(audio_path, output_name)
            return text_path
        except Exception as e:
            logger.error(f"❌ Lỗi chuyển đổi audio thành text: {str(e)}")
            raise
    
    def _retry_with_different_model(self, audio_path: str, output_name: str) -> str:
        """
        Thử lại với model khác nếu model đầu tiên thất bại
        """
        try:
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_transcript_retry.txt")
            
            logger.info("🔄 Thử lại với model khác...")
            
            with open(audio_path, 'rb') as audio_file:
                url = "https://api.deepgram.com/v1/listen"
                headers = {
                    "Authorization": f"Token {self.deepgram_api_key}",
                    "Content-Type": "audio/mpeg"
                }
                
                # Thử với model cũ hơn
                params = {
                    "model": "enhanced",
                    "language": "vi",
                    "punctuate": "true"
                }
                
                response = requests.post(url, headers=headers, params=params, data=audio_file, timeout=600)
                
                if response.status_code == 200:
                    result = response.json()
                    transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                    
                    if transcript and transcript.strip():
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(transcript)
                        
                        logger.info(f"✅ Thử lại thành công với model khác!")
                        logger.info(f"📝 Độ dài text: {len(transcript)} ký tự")
                        
                        return output_path
                    else:
                        raise Exception("Transcript vẫn rỗng")
                else:
                    raise Exception(f"Retry failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Thử lại cũng thất bại: {str(e)}")
            raise
    
    def rewrite_text(self, text_path: str, output_name: str) -> str:
        """
        Viết lại text bằng Gemini API dựa trên prompt từ Google Sheets
        
        Tạo nội dung MỚI HOÀN TOÀN dựa trên:
        1. Prompt template từ Google Sheets
        2. Nội dung gốc để tham khảo chủ đề
        3. Yêu cầu viết lại theo phong cách TikTok
        
        Args:
            text_path: Đường dẫn đến file text gốc
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file text đã viết lại (nội dung mới hoàn toàn)
        """
        try:
            # Tạo tên file output cho text đã viết lại
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_rewritten.txt")
            
            logger.info(f"🔄 Đang viết lại text (nội dung mới): {os.path.basename(text_path)}")
            
            # Đọc text gốc từ file
            with open(text_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
            
            # Chuẩn bị request đến Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_api_key}"
            
            # Đọc prompt template từ Google Sheets
            prompt_template = self.get_prompt_from_sheets()
            
            # Prompt để viết lại text theo yêu cầu từ Google Sheets với giọng văn miền Bắc
            prompt = f"""
            === HƯỚNG DẪN VIẾT LẠI NỘI DUNG MỚI ===
            
            Bạn là chuyên gia viết nội dung TikTok chuyên nghiệp. Nhiệm vụ: Viết lại nội dung MỚI HOÀN TOÀN nhưng BÁM CHẶT TIMELINE của nội dung gốc.
            
            === PROMPT TEMPLATE TỪ GOOGLE SHEETS (CẬP NHẬT MỚI) ===
            {prompt_template}
            
            === YÊU CẦU QUAN TRỌNG ===
            - TUYỆT ĐỐI TUÂN THỦ prompt template từ Google Sheets
            - Sử dụng đúng bố cục, phong cách, và yêu cầu từ prompt template
            - Không bỏ qua bất kỳ phần nào trong prompt template
            - Đảm bảo tiêu đề, caption, CTA theo đúng format từ prompt template
            
            === NỘI DUNG GỐC ĐỂ THAM KHẢO CHỦ ĐỀ ===
            {original_text}
            
            === YÊU CẦU QUAN TRỌNG ===
            
            🎯 **TẠO NỘI DUNG MỚI HOÀN TOÀN:**
            - KHÔNG copy nội dung gốc
            - Chỉ lấy ý tưởng chủ đề để viết mới
            - Tạo ra text hoàn toàn khác biệt, hấp dẫn hơn
            
            ⏰ **BÁM CHẶT TIMELINE - KHÔNG THAY ĐỔI:**
            - **TIMELINE PHẢI GIỮ NGUYÊN 100%:** Nếu gốc "(Giây 1-3) xin chào" thì mới phải "(Giây 1-3) [nội dung mới]"
            - **KHÔNG THAY ĐỔI THỜI GIAN:** Giữ nguyên số giây, không thêm/bớt
            - **KHÔNG THAY ĐỔI CẤU TRÚC:** Giữ nguyên format "(Giây X-Y) nội dung"
            - **CHỈ VIẾT LẠI NỘI DUNG:** Thay đổi nội dung bên trong timeline, không đụng đến timeline
            
           
            📝 **ÁP DỤNG PROMPT TEMPLATE:**
            - Tuân thủ đúng yêu cầu từ Google Sheets
            - Áp dụng bố cục và phong cách đã định nghĩa
            -Nội dung mới phải hay và có sự khác biệt với nội dung cũcũ
            - Sử dụng các mẫu CTA và caption gợi ý
            - Nội dung tiếng việt hoàn toàn không sưr dụng tiếng anh
            
            🎨 **PHONG CÁCH VIẾT - CHUYÊN NGHIỆP VÀ TỰ NHIÊN:**
            - **Văn phong chia sẻ trực tiếp:** Như đang tư vấn thật, không khô khan hay nhạt nhẽo
            - **Từ ngữ sinh động:** Dùng từ có cảm xúc, tạo hứng thú thay vì từ khô khan
            - **Không kể chuyện:** Tránh giọng điệu thuật lại, viết như đang tương tác trực tiếp
            - **Xưng hô thân thiện:** "em - bác" để tạo sự gần gũi, tin cậy
            - **Từ nối tự nhiên:** "mà", "đấy", "nè", "ạ", "nhỉ", "thế"
            - **Biểu cảm sinh động:** "hay ho", "tuyệt vời", "chắc chắn", "đảm bảo"
            - **CHUYÊN NGHIỆP:** Dùng từ ngữ chuyên ngành nội thất, kiến trúc
            - **TRÁNH TỪ SUỒNG SÃ:** Không dùng "xưa rồi diễm ơi", "hot hit", "quá đã"
            - **THAY THẾ BẰNG:** "hiện đại", "tiên tiến", "tối ưu", "chuyên nghiệp"
            
            🗣️ **ĐẶC ĐIỂM GIỌNG VĂN CHUYÊN NGHIỆP:**
            - Dùng "giải pháp tối ưu" thay vì "mẹo hay ho"
            - Dùng "đảm bảo hiệu quả" thay vì "chắc chắn sẽ"
            - Dùng "xuất sắc" thay vì "tuyệt vời"
            - Dùng "vượt trội" thay vì "khác hẳn"
            - Dùng "cam kết" thay vì "đảm bảo"
            - Dùng "tối ưu hóa" thay vì "cực kỳ hiệu quả"
            - Dùng "thiết kế hiện đại" thay vì "hot hit"
            - Dùng "phong cách tiên tiến" thay vì "xưa rồi diễm ơi"
            
            === QUY TẮC TIMELINE BẮT BUỘC ===
            1. **TÌM TIMELINE:** Xác định tất cả các đoạn có format "(Giây X-Y)"
            2. **GIỮ NGUYÊN:** Không thay đổi số giây, không thay đổi format
            3. **VIẾT LẠI NỘI DUNG:** Chỉ thay đổi nội dung bên trong timeline với giọng văn tự nhiên hay hơn
            4. **KIỂM TRA:** Đảm bảo số lượng timeline và thời gian giống hệt gốc
            
            === NGUYÊN TẮC VIẾT HAY HƠN ===
            🔥 **TRÁNH NHỮNG ĐIỀU NÀY:**
            - Văn nhạt nhẽo: "Điều này rất tốt" → "Cái này tuyệt vời luôn"
            - Văn kể chuyện: "Có một cách để..." → "Em sẽ chỉ bác cách..."
            - Từ khô khan: "phương pháp" → "mẹo hay ho"
            - Thiếu cảm xúc: "có thể làm" → "chắc chắn làm được"
            
            ✨ **ÁP DỤNG NHỮNG ĐIỀU NÀY:**
            - Dùng từ có năng lượng: "cực kỳ", "siêu", "tuyệt vời", "hay ho"
            - Tạo sự tự tin: "chắc chắn", "đảm bảo", "100%"
            - Gây tò mò: "mẹo này", "bí quyết", "chiêu hay"
            - Tương tác trực tiếp: "bác thử xem", "em chỉ bác"
            
            === CẤU TRÚC KẾT QUẢ YÊU CẦU ===
            
            GỢI Ý 5 TIÊU ĐỀ:
            BẮT BUỘC VIẾT 5 TIÊU ĐỀ CỤ THỂ, KHÔNG ĐỂ TRỐNG []. VÍ DỤ ĐA DẠNG (KHÔNG DÙNG "HACK"):
            1. "Sảnh vào nhà gọn gàng thế này thì ai cũng mê!"
            2. "Bố trí sảnh chuẩn, nhìn là muốn làm ngay!"
            3. "Ai cũng bỏ lỡ góc này khi thiết kế nhà!"
            4. "Sảnh nhỏ nhưng công năng gấp đôi, đây là bí quyết!"
            5. "Gọn – đẹp – tiện: Sảnh vào nhà kiểu mới!"
            
            HOẶC:
            1. "Thiết kế tủ giày âm tường: Giải pháp tối ưu cho không gian hiện đại!"
            2. "Tủ giày âm tường: Kết hợp hoàn hảo giữa thẩm mỹ và công năng!"
            3. "Thiết kế tủ giày thông minh: Tối ưu hóa không gian sống!"
            4. "Tủ giày âm tường đa năng: Giải pháp thiết kế tiên tiến!"
            5. "Tủ giày âm tường: Nâng tầm không gian sống với thiết kế chuyên nghiệp!"
            
            NỘI DUNG CHÍNH (GIỮ NGUYÊN TIMELINE):
            - Dẫn dắt tự nhiên: Viết 1-2 câu để dẫn vào nội dung
            - Nội dung chính: Chia đoạn rõ ràng, mượt mà
            [Nội dung với timeline đã viết lại - SÁNG TẠO HƠN, không cần sát nội dung cũ, chỉ cần đúng thời gian và ý chính]
            
            GỢI Ý 3 CAPTION TIKTOK:
            BẮT BUỘC VIẾT 3 CAPTION CỤ THỂ, KHÔNG ĐỂ TRỐNG []. VÍ DỤ CHUYÊN NGHIỆP:
            1. "Thiết kế tủ giày âm tường: Giải pháp tối ưu cho không gian hiện đại! #thietkenoithat #tugiayamtuong #khonggianhien dai"
            2. "Tủ giày âm tường: Kết hợp hoàn hảo giữa thẩm mỹ và công năng! #noithat #tugiay #thietkechuyennghiep"
            3. "Thiết kế tủ giày thông minh: Tối ưu hóa không gian sống! #tugiaythongminh #toiuuhoa #khonggiansong"
            
            CALL TO ACTION (CTA) - VIẾT MỚI DỰA TRÊN MẪU:
            BẮT BUỘC VIẾT 1 CTA CỤ THỂ, KHÔNG ĐỂ TRỐNG []. VÍ DỤ CHUYÊN NGHIỆP:
            "Thiết kế tủ giày âm tường này sẽ nâng tầm không gian sống của các bác! Lưu lại ngay để tham khảo, chia sẻ cho bạn bè cùng xem nhé!"
            
            === LƯU Ý ===
            - Text cải tiến sẽ được tách thành 2 phần riêng biệt
            - Phần 1: CHỈ nội dung chính có timeline (cột Text cải tiến)  
            - Phần 2: Tiêu đề + Caption + CTA (cột Gợi ý tiêu đề)
            
            === QUY TẮC QUAN TRỌNG ===
            - Timeline phải giống hệt gốc (số giây và format)
            - Nội dung bên trong timeline phải sinh động, hấp dẫn, không nhạt nhẽo
            - SÁNG TẠO HƠN: Không cần sát nội dung cũ, chỉ cần đúng thời gian và ý chính, viết theo prompt và các yêu cầucầu riêng
            - Sử dụng xưng hô "em - bác" tự nhiên
            - Đảm bảo hoàn chỉnh và cuốn hút
            - TUYỆT ĐỐI KHÔNG DÙNG ICON: Không được viết bất kỳ icon nào (📋, 📝, 📱, 🎯, 😍, ❤️, etc.)
            
            === HƯỚNG DẪN VIẾT TIÊU ĐỀ HAY ===
            🎯 **TIÊU ĐỀ PHẢI:**
            - Liên quan trực tiếp đến nội dung đã viết
            - Tạo cảm giác "phải xem ngay"
            - Dùng từ mạnh ĐA DẠNG: "bí quyết", "mẹo", "chiêu", "cách", "tuyệt chiêu", "bí kíp", "thủ thuật", "kỹ thuật", "phương pháp", "giải pháp"
            - Tạo tò mò: "99% người không biết", "chỉ 1% làm đúng", "bí mật", "ít ai biết", "chưa ai nghĩ đến"
            - Giải quyết vấn đề: "không còn lo", "dứt điểm", "xử lý triệt để", "giải quyết hoàn hảo"
            - PHÂN BIỆT RÕ: Nếu video về tủ giày thì viết "tủ giày", không viết "nhà kho"
            - CHUYÊN NGHIỆP: Dùng từ ngữ chuyên ngành nội thất, kiến trúc
            
            ❌ **TRÁNH TIÊU ĐỀ:**
            - Chung chung, không liên quan nội dung
            - Nhạt nhẽo, không gây tò mò
            - Copy từ nội dung một cách máy móc
            - Dùng sai từ: "tủ giày" thành "nhà kho"
            - LẠM DỤNG TỪ "HACK": Không dùng "hack" cho mọi thứ, thay bằng từ khác
            - TỪ SUỒNG SÃ: Không dùng "xưa rồi diễm ơi", "hot hit", "quá đã", "ghen tị"
            
            === HƯỚNG DẪN VIẾT CAPTION HAY ===
            🎯 **CAPTION PHẢI:**
            - Có hashtag phù hợp với chủ đề
            - Tạo cảm xúc mạnh: "wow", "không thể tin được", "tuyệt vời"
            - Khuyến khích tương tác: "bạn có làm được không?", "thử ngay đi"
            - Tạo giá trị: "tiết kiệm tiền", "tiết kiệm thời gian", "hiệu quả"
            
            ❌ **TRÁNH CAPTION:**
            - Nhạt nhẽo, không có cảm xúc
            - Không khuyến khích tương tác
            - Hashtag không liên quan
            
            === HƯỚNG DẪN VIẾT CTA MỚI ===
            🎯 **CTA PHẢI:**
            - Dựa trên phong cách mẫu CTA trong prompt template
            - Sáng tạo mới, không copy nguyên văn
            - Phù hợp với nội dung cụ thể này
            - Có yếu tố: lưu lại, chia sẻ, bình luận, kết nối, tư vấn
            - Giọng điệu thân thiện "em - bác"
            - ĐA DẠNG TỪ NGỮ: Không lạm dụng từ "hack", dùng "bí quyết", "mẹo", "cách", "phương pháp"
            
            ❌ **TRÁNH CTA:**
            - Copy nguyên văn từ mẫu
            - Không liên quan đến nội dung
            - Giọng điệu khô khan
            - LẠM DỤNG TỪ "HACK": Không dùng "hack" cho mọi thứ
            """
            
            # Tham số tối ưu cho việc viết lại
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.6,  # Sáng tạo vừa phải
                    "topP": 0.9,         # Đa dạng từ vựng
                    "topK": 60,          # Lựa chọn phong phú
                    "maxOutputTokens": 3000
                }
            }
            
            # Gửi request đến Gemini API
            logger.info("Đang gửi request đến Gemini API để viết lại nội dung...")
            response = requests.post(url, json=data, timeout=360)
            
            # Kiểm tra response
            if response.status_code == 200:
                result = response.json()
                
                # Lấy text đã viết lại từ kết quả Gemini
                rewritten_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Lưu text mới vào file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rewritten_text)
                
                logger.info(f"✅ Viết lại text thành công (nội dung mới)!")
                logger.info(f"📁 File: {output_path}")
                logger.info(f"📝 Độ dài text: {len(rewritten_text)} ký tự")
                logger.info(f"📄 Nội dung mới: {rewritten_text[:200]}...")
                
                return output_path
            else:
                # Nếu API trả về lỗi
                error_msg = f"Gemini API lỗi: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # Log chi tiết hơn để debug
                if response.status_code == 429:
                    logger.error("❌ QUOTA EXCEEDED - Đã vượt quá giới hạn API")
                elif response.status_code == 403:
                    logger.error("❌ FORBIDDEN - API key không hợp lệ hoặc bị disable")
                elif response.status_code == 400:
                    logger.error("❌ BAD REQUEST - Lỗi trong request format")
                
                logger.error(f"📄 Full response: {response.text}")
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ Lỗi viết lại text: {str(e)}")
            raise

    def get_prompt_from_sheets(self) -> str:
        """
        Đọc prompt template từ Google Sheets
        
        Returns:
            Nội dung prompt template từ sheet "Prompt"
        """
        try:
            logger.info("📊 Đang đọc prompt template từ Google Sheets (cập nhật mới)...")
            
            # Đọc dữ liệu từ sheet "Prompt" (dòng 1-200 để đảm bảo đọc hết prompt mới)
            # Thử với tên sheet khác nếu lỗi
            range_name = 'Prompt!A1:Z200'
            
            # Thực hiện request để đọc prompt
            try:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()
            except Exception as e:
                logger.warning(f"⚠️ Lỗi với tên sheet 'Prompt', thử với tên khác: {str(e)}")
                # Thử với tên sheet khác
                alternative_names = ['prompt', 'Prompt Template', 'PROMPT']
                for alt_name in alternative_names:
                    try:
                        range_name = f'{alt_name}!A1:Z200'
                        result = self.sheets_service.spreadsheets().values().get(
                            spreadsheetId=self.spreadsheet_id,
                            range=range_name
                        ).execute()
                        logger.info(f"✅ Thành công với tên sheet: {alt_name}")
                        break
                    except Exception as e2:
                        logger.warning(f"⚠️ Lỗi với tên sheet '{alt_name}': {str(e2)}")
                        continue
                else:
                    # Nếu tất cả đều lỗi, raise exception
                    raise e
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("⚠️ Không tìm thấy dữ liệu trong sheet Prompt")
                return self._get_fallback_prompt()
            
            # Ghép tất cả nội dung thành một chuỗi
            sheet_prompt = ""
            for row in values:
                if row:  # Kiểm tra row không rỗng
                    sheet_prompt += " ".join(row) + "\n"
            
            logger.info(f"✅ Đã đọc prompt template từ Google Sheets ({len(sheet_prompt)} ký tự)")
            logger.info(f"📄 Prompt preview: {sheet_prompt[:300]}...")
            
            # Kiểm tra xem prompt có đầy đủ không
            if len(sheet_prompt.strip()) < 100:
                logger.warning("⚠️ Prompt quá ngắn, có thể chưa đọc hết. Sử dụng fallback...")
                return self._get_fallback_prompt()
            
            # Kiểm tra xem có chứa các từ khóa quan trọng không
            important_keywords = ['tiêu đề', 'caption', 'cta', 'timeline', 'nội dung', 'gợi ý 5 tiêu đề', 'gợi ý 3 caption', 'nội dung chính']
            found_keywords = sum(1 for keyword in important_keywords if keyword in sheet_prompt.lower())
            
            if found_keywords < 3:
                logger.warning(f"⚠️ Prompt thiếu từ khóa quan trọng (chỉ có {found_keywords}/5). Sử dụng fallback...")
                return self._get_fallback_prompt()
            
            logger.info(f"✅ Prompt đầy đủ và hợp lệ ({found_keywords}/5 từ khóa quan trọng)")
            return sheet_prompt.strip()
            
        except Exception as e:
            logger.error(f"❌ Lỗi đọc prompt từ Google Sheets: {str(e)}")
            logger.info("🔄 Sử dụng prompt fallback...")
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """
        Prompt fallback khi không đọc được từ Google Sheets
        
        Returns:
            Prompt template mặc định
        """
        return """
        Bạn là một chuyên gia viết nội dung TikTok chuyên nghiệp. Nhiệm vụ của bạn là viết lại nội dung text từ video/audio gốc theo phong cách TikTok hấp dẫn.

        ## 📋 YÊU CẦU CHÍNH:

        ### 🎯 **BÁM CHẶT TIMELINE - KHÔNG THAY ĐỔI:**
        - **TIMELINE PHẢI GIỮ NGUYÊN 100%:** Nếu gốc "(Giây 1-3) xin chào" thì mới phải "(Giây 1-3) [nội dung mới]"
        - **KHÔNG THAY ĐỔI THỜI GIAN:** Giữ nguyên số giây, không thêm/bớt
        - **KHÔNG THAY ĐỔI CẤU TRÚC:** Giữ nguyên format "(Giây X-Y) nội dung"
        - **CHỈ VIẾT LẠI NỘI DUNG:** Thay đổi nội dung bên trong timeline, không đụng đến timeline
        - **Ý nghĩa tương đương:** Không tự sáng tạo quá đà, chỉ viết lại theo cách tự nhiên hơn

        ### 📝 **BỐ CỤC VIẾT LẠI:**

        #### **1. GỢI Ý 5 TIÊU ĐỀ** (ngắn, bắt tai, gợi tò mò)
        - Tiêu đề 1: [Tiêu đề ngắn gọn]
        - Tiêu đề 2: [Tiêu đề gợi tò mò]
        - Tiêu đề 3: [Tiêu đề bắt trend]
        - Tiêu đề 4: [Tiêu đề thực tế]
        - Tiêu đề 5: [Tiêu đề cảm xúc]

        #### **2. DẪN DẮT VÀO ĐỀ** (1-2 câu đầu mạch lạc, tự nhiên, cuốn hút)
        - Câu mở đầu tự nhiên, gần gũi
        - Tạo sự tò mò cho người xem

        #### **3. NỘI DUNG CHÍNH** (triển khai từng ý, có từ nối mượt mà)
        - Dẫn dắt tự nhiên: Viết 1-2 câu để dẫn vào nội dung
        - Nội dung chính: Chia thành 2-3 đoạn rõ ràng, mượt mà
        - Sử dụng từ nối: "Tiếp theo là...", "Vậy nên...", "Lúc này...", "Để xử lý phần đó...", "Kết lại là..."

        #### **4. CALL TO ACTION (CTA)** - Chọn 1 trong các mẫu sau:
        - "Lưu lại ngay kẻo quên, tránh mất tiền oan khi xây nhà nhé các bác!"
        - "Nhớ chia sẻ điều tuyệt vời này cho những người thân yêu của bạn nhé!"
        - "Các bác có thêm ý tưởng nào hay hơn không? Bình luận chia sẻ với em nhé!"
        - "còn chờ gì nữa mà k kỷ niệm e 1 tim nhỉ?"
        - "Hợp lý thế này rồi thì kỷ niệm e 1 tim chắc cũng hợp lý nhỉ?"
        - "Đấy nhìn qua thì mất có hơn phút mà mọi thứ có nơi có chỗ hết rồi! Thế nhưng mà làm thì không dễ thế đâu nhé! có gì không hiểu thì đừng ngần ngại kết nối! cứ để e gỡ rối cho!"
        - "có gì không hiểu thì đừng ngần ngại kết nối! cứ để e gỡ rối cho!"
        - "Còn nhiều ý tưởng thiết kế hay ho lắm, vào trang của em để xem thêm nhé!"
        - "Muốn nhà rộng thành chật hay nhà chật thành rộng thì các bác biết phải làm gì rồi đấy! E đã bao giờ thu phí tư vấn đâu!"
        - "chia sẻ tri thức tuyệt vời này cùng e nhé!"
        - "các bác có muốn em chia sẻ thêm mẹo tối ưu không gian thế này không? Kỷ niệm e 1 tim cho có động lực nhé!"
        - "Nhà nhỏ hay to không quan trọng, quan trọng là phải chọn đúng nơi, đến đúng chỗ, gặp đúng người các bác ạ!"
        - "Nếu thấy nội dung này ý nghĩa thì chia sẻ nó cùng e nhé!"
        - "Làm như này rồi thì chắc x2 chi phí thiết kế cũng đáng các bác nhỉ?"
        - "Bí quyết để có 1 ngôi nhà gọn gàng là cần phải tính toán để mọi thứ đều có nơi có chỗ của nó! - Bí kíp cả đấy các bác ạ! lưu ngay video này lại nhé! vì rất có thể nó sẽ không xuất hiện trước mắt các bác nữa đâu!"
        - "Cần câu cơm của em cả đấy các bác ạ! lưu ngay video này lại nhé!"
        - "Em khuyến cáo là đừng tự áp dụng có chỗ nào không hiểu cứ ới e!"
        - "Hợp lý như này rồi mà k kỷ niệm em 1 tim là hơi bị buồn đấy!"

        #### **5. CAPTION GỢI Ý 3 ĐĂNG TIKTOK** (có hashtag phù hợp, gợi cảm xúc, đúng xu hướng)

        ## 🔹 **QUY TẮC VIẾT NỘI DUNG:**

        ### **🎯 GIỮ VĂN PHONG TỰ NHIÊN HAY HƠN:**
        - Không viết kiểu "em làm cái này, em làm cái kia" 
        - Chuyển thành lối chia sẻ trực tiếp "em sẽ chỉ bác cách...", "bác thử xem..."
        - Dùng xưng hô thân thiện: "em - bác" để tạo sự gần gũi, tin cậy
        - Từ ngữ sinh động: "mẹo hay ho", "tuyệt vời", "chắc chắn", "cực kỳ hiệu quả"
        - Từ nối tự nhiên: "mà", "đấy", "nè", "ạ", "nhỉ", "thế"
        - Biểu cảm cuốn hút: "siêu tuyệt", "hay ho", "đảm bảo", "chắc chắn"

        ### **⏰ TIMELINE BẮT BUỘC GIỮ NGUYÊN:**
        - **TIMELINE PHẢI GIỮ NGUYÊN 100%:** Nếu gốc có "(Giây 1-3) xin chào" thì mới phải có "(Giây 1-3) [nội dung mới]"
        - **KHÔNG THAY ĐỔI THỜI GIAN:** Giữ nguyên số giây, không thêm/bớt
        - **KHÔNG THAY ĐỔI CẤU TRÚC:** Giữ nguyên format "(Giây X-Y) nội dung"
        - **CHỈ VIẾT LẠI NỘI DUNG:** Thay đổi nội dung bên trong timeline, không đụng đến timeline

        ### **📝 CÁCH VIẾT HAY HƠN:**
        - Chuyển đoạn bằng các từ nối tự nhiên: "Còn nữa nè bác", "Đặc biệt là...", "Quan trọng nhất là...", "Em chỉ thêm cho bác..."
        - Dùng từ sinh động thay từ khô khan: "mẹo hay ho" thay "phương pháp", "cực kỳ hiệu quả" thay "hiệu quả"
        - Chia nhỏ từng ý rõ ràng, tạo điểm nhấn bằng từ cảm xúc
        - Tránh giọng kể chuyện: viết như đang tư vấn trực tiếp
        - Tạo sự tự tin: "chắc chắn", "đảm bảo", "100%" thay vì "có thể", "chắc là"
        
        ### **🔥 TRÁNH VĂN NHẠT NHẼO:**
        - ❌ "Điều này tốt" → ✅ "Cái này tuyệt vời luôn bác ạ"
        - ❌ "Có thể áp dụng" → ✅ "Bác áp dụng chắc chắn hiệu quả"
        - ❌ "Phương pháp này" → ✅ "Mẹo hay ho này"
        - ❌ "Kết quả khá tốt" → ✅ "Kết quả siêu tuyệt vời"

        ## 📋 **HƯỚNG DẪN SỬ DỤNG:**

        1. **Đọc text gốc từ video/audio** (có timeline)
        2. **Phân tích timeline:** Xác định các đoạn thời gian và nội dung tương ứng
        3. **Viết lại theo timeline:** Mỗi đoạn thời gian phải có nội dung mới tương đương
        4. **Áp dụng bố cục:** MỞ ĐẦU - THÂN - KẾT
        5. **Kiểm tra:** Đảm bảo timeline chính xác và ý nghĩa tương đương

        ## ⚠️ **LƯU Ý QUAN TRỌNG:**

        - **KHÔNG tự sáng tạo quá đà:** Chỉ viết lại theo cách tự nhiên hay hơn
        - **BẮT BUỘC giữ timeline:** Timeline phải giống hệt gốc (số giây và format)
        - **CHỈ VIẾT LẠI NỘI DUNG:** Thay đổi nội dung bên trong timeline thành sinh động hơn
        - **KIỂM TRA:** Đảm bảo số lượng timeline và thời gian giống hệt gốc
        - **SINH ĐỘNG HƠN:** Dùng từ có cảm xúc, tạo sự cuốn hút thay vì nhạt nhẽo
        - **SÁNG TẠO HƠN:** Không cần sát nội dung cũ, chỉ cần đúng thời gian và ý chính, viết theo cách riêng
        - **TUYỆT ĐỐI KHÔNG DÙNG ICON:** Không được viết bất kỳ icon nào (📋, 📝, 📱, 🎯, 😍, ❤️, etc.)

        === CẤU TRÚC KẾT QUẢ YÊU CẦU ===
        
        GỢI Ý 5 TIÊU ĐỀ 
        1. [Tiêu đề ngắn gọn, bắt tai, phải liên quan trực tiếp đến nội dung đã viết]
        2. [Tiêu đề gợi tò mò, tạo cảm giác "phải xem ngay", dựa trên ý chính của nội dung]
        3. [Tiêu đề bắt trend, viral, nhưng phải đúng với chủ đề nội dung]
        4. [Tiêu đề thực tế, giải quyết vấn đề cụ thể từ nội dung]
        5. [Tiêu đề cảm xúc, tạo cảm xúc mạnh, dựa trên lợi ích từ nội dung]
        
        NỘI DUNG CHÍNH (GIỮ NGUYÊN TIMELINE):
        [Nội dung với timeline đã viết lại - giọng em-bác sinh động, SÁNG TẠO HƠN]
        
        GỢI Ý 3 CAPTION TIKTOK :
        1. [Caption với hashtag phù hợp, gợi cảm xúc mạnh, tạo sự tò mò về nội dung]
        2. [Caption bắt trend, viral, nhưng phải liên quan và thu hút người xem nội dung này]
        3. [Caption tương tác cao, khuyến khích comment, share, dựa trên giá trị từ nội dung]
        
        CALL TO ACTION (CTA) - VIẾT MỚI DỰA TRÊN MẪU:
        [Viết 1 câu CTA mới hoàn toàn, dựa trên phong cách và ý tưởng từ các mẫu CTA trong prompt template, nhưng KHÔNG copy nguyên văn, phải sáng tạo mới phù hợp với nội dung này]
        
        **Bây giờ hãy viết lại nội dung text gốc theo cấu trúc trên, đảm bảo giữ nguyên timeline và sinh động hơn.**
        """
    
    # def text_to_speech(self, text_path: str, output_name: str) -> str:
    #     """
    #     Chuyển đổi text đã viết lại thành speech bằng Deepgram TTS API - ĐÃ COMMENT
    #     
    #     Chức năng:
    #     - Đọc file text đã viết lại (rewritten text từ Gemini)
    #     - Loại bỏ phần timeline và chỉ giữ nội dung chính của text đã viết lại
    #     - Chuyển đổi thành giọng nói tiếng Việt
    #     - Lưu file audio MP3
    #     
    #     Args:
    #         text_path: Đường dẫn đến file text đã viết lại (rewritten text)
    #         output_name: Tên file output (không có extension)
    #         
    #     Returns:
    #         Đường dẫn đến file audio đã tạo
    #     """
    #     try:
    #         # Tạo tên file output cho audio
    #         base_name = os.path.splitext(output_name)[0]
    #         output_path = os.path.join(self.temp_dir, f"{base_name}_tts.mp3")
    #         
    #         logger.info(f"🎤 Bắt đầu chuyển đổi text thành speech: {os.path.basename(text_path)}")
    #         
    #         # Đọc text từ file
    #         with open(text_path, 'r', encoding='utf-8') as f:
    #             text_content = f.read()
    #         
    #         # Kiểm tra text có nội dung không
    #         if not text_content.strip():
    #             logger.warning("⚠️ Text rỗng, không thể chuyển thành speech")
    #             raise Exception("Text rỗng")
    #         
    #         # Kiểm tra text có ký tự đặc biệt không
    #         if len(text_content) > 5000:
    #             logger.warning("⚠️ Text quá dài, cắt bớt để tránh lỗi API")
    #             text_content = text_content[:5000]
    #         
    #         # Xử lý text: Loại bỏ timeline và chỉ giữ nội dung chính của text đã viết lại
    #         cleaned_text = self._extract_main_content(text_content)
    #         logger.info(f"🧹 Đã làm sạch text đã viết lại, loại bỏ timeline")
    #         logger.info(f"📝 Text gốc: {len(text_content)} ký tự")
    #         logger.info(f"📝 Text đã làm sạch: {len(cleaned_text)} ký tự")
    #         logger.info(f"📄 Text đã làm sạch (100 ký tự đầu): {cleaned_text[:100]}...")
    #         logger.info(f"📄 Text đã làm sạch (200 ký tự đầu): {cleaned_text[:200]}...")
    #         
    #         # Kiểm tra và làm sạch text cuối cùng
    #         if len(cleaned_text) > 4000:
    #             logger.warning("⚠️ Text đã làm sạch vẫn quá dài, cắt bớt")
    #             cleaned_text = cleaned_text[:4000]
    #         
    #         # Loại bỏ các ký tự đặc biệt có thể gây lỗi
    #         cleaned_text = re.sub(r'[^\w\s\.,!?;:()\-\'\"]', '', cleaned_text)
    #         cleaned_text = cleaned_text.strip()
    #         
    #         logger.info(f"📝 Text cuối cùng: {len(cleaned_text)} ký tự")
    #         logger.info(f"📄 Text cuối cùng (100 ký tự đầu): {cleaned_text[:100]}...")
    #         
    #         # Kiểm tra text cuối cùng có nội dung không
    #         if not cleaned_text or len(cleaned_text.strip()) < 10:
    #             logger.error("❌ Text cuối cùng quá ngắn hoặc rỗng")
    #             raise Exception("Text cuối cùng không đủ nội dung để chuyển thành speech")
    #         
    #         # Chuẩn bị request đến Deepgram TTS API
    #         url = "https://api.deepgram.com/v1/speak"
    #         headers = {
    #             "Authorization": f"Token {self.deepgram_tts_api_key}",
    #             "Content-Type": "application/json"
    #         }
    #         
    #         # Thêm query parameters cho model và voice
    #         params = {
    #             "model": "aura-asteria-en",
    #             "voice": "asteria"
    #         }
    #         
    #         # Tham số cho TTS (sử dụng voice tiếng Việt)
    #         data = {
    #             "text": cleaned_text
    #         }
    #         
    #         # Kiểm tra data trước khi gửi
    #         logger.info(f"📋 Data sẽ gửi: {data}")
    #         logger.info(f"📋 JSON data: {json.dumps(data, ensure_ascii=False)}")
    #         
    #         # Gửi request đến Deepgram TTS API
    #         logger.info("🔄 Đang gửi request đến Deepgram TTS API...")
    #         logger.info(f"📝 Text length: {len(cleaned_text)} ký tự")
    #         response = requests.post(url, headers=headers, params=params, json=data, timeout=120)
    #         
    #         # Kiểm tra response
    #         if response.status_code == 200:
    #             # Lưu audio vào file
    #             with open(output_path, 'wb') as f:
    #                 f.write(response.content)
    #             
    #             # Kiểm tra file đã tạo
    #             if os.path.exists(output_path):
    #                 file_size = os.path.getsize(output_path)
    #                 logger.info(f"✅ Chuyển đổi text thành speech thành công!")
    #                 logger.info(f"📁 File audio: {output_path}")
    #                 logger.info(f"📊 Kích thước: {file_size:,} bytes")
    #                 logger.info(f"📝 Text length: {len(cleaned_text)} ký tự")
    #                 
    #                 return output_path
    #             else:
    #                 raise Exception("Không thể tạo file audio")
    #         else:
    #             # Nếu API trả về lỗi
    #             error_msg = f"Deepgram TTS API lỗi: {response.status_code} - {response.text}"
    #             logger.error(error_msg)
    #             raise Exception(error_msg)
    #             
    #     except Exception as e:
    #         logger.error(f"❌ Lỗi chuyển đổi text thành speech: {str(e)}")
    #         raise
    
    def create_text_without_timeline(self, text_path: str, output_name: str) -> str:
        """
        Tạo văn bản không có timeline từ text gốc hoặc text đã viết lại
        
        Args:
            text_path: Đường dẫn đến file text (có thể có timeline)
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file text không có timeline
        """
        try:
            # Tạo tên file output cho text không có timeline
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_no_timeline.txt")
            
            logger.info(f"📝 Đang tạo text không có timeline: {os.path.basename(text_path)}")
            
            # Đọc text từ file
            with open(text_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
            
            # Tách text không có timeline
            text_no_timeline_body = self._format_text_no_timeline(original_text)
            lead_in = self._generate_lead_in_hook(text_no_timeline_body)
            formatted_no_timeline = []
            formatted_no_timeline.append("CÂU VÀO ĐỀ ->")
            formatted_no_timeline.append(lead_in if lead_in else "...")
            formatted_no_timeline.append("NỘI DUNG CHÍNH ->")
            formatted_no_timeline.append(text_no_timeline_body.strip())
            text_no_timeline = "\n".join(formatted_no_timeline).strip()
            
            # Lưu text không có timeline vào file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_no_timeline)
            
            logger.info(f"✅ Tạo text không timeline thành công!")
            logger.info(f"📁 File: {output_path}")
            logger.info(f"📝 Độ dài text: {len(text_no_timeline)} ký tự")
            logger.info(f"📄 Nội dung: {text_no_timeline[:200]}...")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo text không timeline: {str(e)}")
            raise

    def create_main_content_only(self, text_path: str, output_name: str) -> str:
        """
        Tạo file chỉ chứa nội dung chính có timeline (cho cột Text cải tiến)
        
        Args:
            text_path: Đường dẫn đến file text đã viết lại
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file chỉ có nội dung chính với timeline
        """
        try:
            # Tạo tên file output cho nội dung chính
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_main_content.txt")
            
            logger.info(f"📝 Đang tạo nội dung chính có timeline: {os.path.basename(text_path)}")
            
            # Đọc text từ file
            with open(text_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
            
            # Trích xuất chỉ nội dung chính có timeline
            main_content = self._extract_main_content_with_timeline(original_text)
            
            # Bọc theo format yêu cầu: Câu vào đề + Nội dung chính
            lead_in = self._generate_lead_in_hook(self._format_main_content_only(main_content))
            formatted = []
            formatted.append("CÂU VÀO ĐỀ ->")
            formatted.append(lead_in if lead_in else "...")
            formatted.append("NỘI DUNG CHÍNH ->")
            formatted.append(main_content.strip())

            # Lưu nội dung chính vào file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(formatted).strip())
            
            logger.info(f"✅ Tạo nội dung chính thành công!")
            logger.info(f"📁 File: {output_path}")
            logger.info(f"📝 Độ dài: {len(main_content)} ký tự")
            logger.info(f"📄 Nội dung: {main_content[:200]}...")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo nội dung chính: {str(e)}")
            raise

    def create_suggestions_content(self, text_path: str, output_name: str) -> str:
        """
        Tạo nội dung gợi ý (tiêu đề, captions, CTA) từ text đã viết lại
        
        Args:
            text_path: Đường dẫn đến file text đã viết lại
            output_name: Tên file output (không có extension)
            
        Returns:
            Đường dẫn đến file gợi ý
        """
        try:
            # Tạo tên file output cho gợi ý
            base_name = os.path.splitext(output_name)[0]
            output_path = os.path.join(self.temp_dir, f"{base_name}_suggestions.txt")
            
            logger.info(f"💡 Đang tạo gợi ý tiêu đề, captions, CTA: {os.path.basename(text_path)}")
            
            # Đọc text từ file
            with open(text_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
            
            # Tách gợi ý từ text đã viết lại
            suggestions_content = self._format_suggestions_content(original_text)
            
            # Lưu gợi ý vào file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(suggestions_content)
            
            logger.info(f"✅ Tạo gợi ý thành công!")
            logger.info(f"📁 File: {output_path}")
            logger.info(f"📝 Độ dài: {len(suggestions_content)} ký tự")
            logger.info(f"📄 Nội dung: {suggestions_content[:200]}...")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo gợi ý: {str(e)}")
            raise

    def _extract_main_content(self, text: str) -> str:
        """
        Trích xuất nội dung chính từ text đã viết lại, loại bỏ timeline
        
        Args:
            text: Text đã viết lại (rewritten text) có thể chứa timeline
            
        Returns:
            Text đã làm sạch, chỉ chứa nội dung chính của text đã viết lại
        """
        try:
            logger.info(f"🔍 Bắt đầu trích xuất nội dung chính từ text đã viết lại...")
            logger.info(f"📄 Text gốc (200 ký tự đầu): {text[:200]}...")
            
            # QUAN TRỌNG: Text đã viết lại thường không có phần "TRANSCRIPT GỐC"
            # Chỉ cần loại bỏ timeline và các phần không cần thiết
            
            # Nếu có phần "=== TRANSCRIPT VỚI TIMELINE ===", lấy phần sau đó
            if "=== TRANSCRIPT VỚI TIMELINE ===" in text:
                parts = text.split("=== TRANSCRIPT VỚI TIMELINE ===")
                if len(parts) > 1:
                    # Lấy phần sau "TRANSCRIPT VỚI TIMELINE"
                    content_after_timeline = parts[1].strip()
                    
                    # Nếu có phần "=== TRANSCRIPT GỐC ===", bỏ qua phần đó
                    if "=== TRANSCRIPT GỐC ===" in content_after_timeline:
                        parts2 = content_after_timeline.split("=== TRANSCRIPT GỐC ===")
                        if len(parts2) > 0:
                            main_content = parts2[0].strip()  # Lấy phần trước "TRANSCRIPT GỐC"
                            formatted_content = self._format_text_no_timeline(main_content)
                            logger.info("✅ Đã trích xuất và format phần text đã viết lại (trước TRANSCRIPT GỐC)")
                            logger.info(f"📄 Nội dung trích xuất (100 ký tự đầu): {formatted_content[:100]}...")
                            return formatted_content
                    else:
                        # Không có TRANSCRIPT GỐC, lấy toàn bộ phần sau timeline và format lại
                        formatted_content = self._format_text_no_timeline(content_after_timeline)
                        logger.info("✅ Đã trích xuất và format toàn bộ phần sau TRANSCRIPT VỚI TIMELINE")
                        logger.info(f"📄 Nội dung trích xuất (100 ký tự đầu): {formatted_content[:100]}...")
                        return formatted_content
            
            # Nếu không có cấu trúc đặc biệt, loại bỏ các dòng timeline
            lines = text.split('\n')
            cleaned_lines = []
            
            # Regex để phát hiện timeline pattern
            import re
            timeline_pattern = r'\(Giây\s+\d+-\d+\)'
            
            for line in lines:
                line = line.strip()
                # Bỏ qua các dòng trống và header
                if (line.startswith('===') or 
                    line == '' or
                    'TRANSCRIPT VỚI TIMELINE' in line or
                    'TRANSCRIPT GỐC' in line):
                    continue
                
                # Xử lý dòng có timeline: chỉ lấy nội dung sau timeline
                if re.search(timeline_pattern, line):
                    # Tìm vị trí kết thúc của pattern timeline
                    match = re.search(timeline_pattern, line)
                    if match:
                        # Lấy nội dung sau timeline pattern
                        content_after_timeline = line[match.end():].strip()
                        if content_after_timeline:
                            cleaned_lines.append(content_after_timeline)
                else:
                    # Nếu không có timeline, giữ nguyên dòng
                    if line:
                        cleaned_lines.append(line)
            
            # Thay vì nối thành 1 đoạn dài, chia thành các đoạn rõ ràng
            if cleaned_lines:
                # Nhóm các câu thành đoạn văn (mỗi 2-3 câu 1 đoạn)
                paragraphs = []
                current_paragraph = []
                
                for line in cleaned_lines:
                    current_paragraph.append(line)
                    # Tạo đoạn mới khi:
                    # 1. Đã có đủ 2-3 câu
                    # 2. Gặp từ kết thúc ý
                    # 3. Câu quá dài (>150 ký tự)
                    should_break = (
                        len(current_paragraph) >= 3 or
                        any(end_word in line.lower() for end_word in ['nên', 'rồi', 'đấy', 'nhé', 'ạ', 'thế', 'luôn', 'được']) or
                        len(' '.join(current_paragraph)) > 150
                    )
                    
                    if should_break:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                
                # Thêm đoạn cuối nếu còn
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                
                # Nối các đoạn bằng xuống dòng đôi để tạo cấu trúc rõ ràng
                cleaned_text = '\n\n'.join(paragraphs).strip()
            else:
                cleaned_text = ''
            
            logger.info("✅ Đã loại bỏ timeline và tạo cấu trúc rõ ràng")
            logger.info(f"📄 Nội dung đã làm sạch (100 ký tự đầu): {cleaned_text[:100]}...")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"❌ Lỗi trích xuất nội dung chính: {str(e)}")
            return text  # Trả về text gốc nếu có lỗi
    
    def _extract_main_content_with_timeline(self, text: str) -> str:
        """
        Trích xuất chỉ nội dung chính có timeline (không có tiêu đề, caption, CTA)
        
        Args:
            text: Text cần trích xuất (có cấu trúc đầy đủ)
            
        Returns:
            Chỉ nội dung chính có timeline
        """
        try:
            # Trích xuất nội dung chính (format mới có dấu, không icon)
            main_content = ""
            # Hỗ trợ cả "NỘI DUNG CHÍNH" và "Nội dung chính"
            if "NỘI DUNG CHÍNH" in text or "Nội dung chính" in text:
                start_markers = []
                if "NỘI DUNG CHÍNH" in text:
                    start_markers.append("NỘI DUNG CHÍNH")
                if "Nội dung chính" in text:
                    start_markers.append("Nội dung chính")

                # Các điểm kết thúc có thể có sau phần nội dung chính
                possible_end_markers = [
                    "GỢI Ý 3 CAPTION",
                    "Gợi ý 3 caption",
                    "**📱 GỢI Ý 3 CAPTION",
                    "CAPTION TIKTOK",
                    "CALL TO ACTION",
                    "CTA:",
                    "CTA"
                ]

                # Thử lần lượt với các start/end markers để lấy phần nội dung chính đầu tiên hợp lệ
                for start_marker in start_markers:
                    section = ""
                    for end_marker in possible_end_markers:
                        section = self._extract_section(text, start_marker, end_marker)
                        if section and len(section.strip()) > 10:
                            break
                    if not section:
                        # Nếu không tìm thấy end marker, lấy đến hết văn bản
                        section = self._extract_section(text, start_marker, None)
                    if section and len(section.strip()) > 10:
                        main_content = section
                        break
            # Fallback cho format cũ có icon
            elif "**📝 NỘI DUNG CHÍNH" in text:
                main_content = self._extract_section(text, "**📝 NỘI DUNG CHÍNH", "**📱 GỢI Ý")
            else:
                # Fallback: coi toàn bộ text như nội dung chính
                main_content = text
            
            # Làm sạch và format nội dung chính (giữ nguyên timeline)
            if main_content:
                # Loại bỏ các dòng trống thừa và format lại
                lines = main_content.strip().split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('**') and not line.startswith('==='):
                        # Loại bỏ đề mục "(GIỮ NGUYÊN TIMELINE):"
                        if "(GIỮ NGUYÊN TIMELINE)" in line or "(GIU NGUYEN TIMELINE)" in line:
                            continue
                        # Loại bỏ dấu ngoặc vuông nếu có
                        line = re.sub(r'^\[|\]$', '', line)
                        # Loại bỏ tất cả dấu ** thừa (đầu, cuối, giữa câu)
                        line = re.sub(r'\*\*', '', line).strip()
                        if line:
                            cleaned_lines.append(line)
                
                return '\n\n'.join(cleaned_lines).strip()
            
            return main_content.strip() if main_content else ""
            
        except Exception as e:
            logger.error(f"❌ Lỗi trích xuất nội dung chính có timeline: {str(e)}")
            return text

    def _extract_only_main_content_from_full_text(self, text: str) -> str:
        """
        Trích xuất chỉ nội dung chính từ toàn bộ text, loại bỏ tất cả gợi ý
        
        Args:
            text: Text đầy đủ có thể chứa gợi ý tiêu đề, caption, CTA
            
        Returns:
            Chỉ nội dung chính
        """
        try:
            lines = text.strip().split('\n')
            main_content_lines = []
            skip_section = False
            
            for line in lines:
                line_clean = line.strip()
                
                # Bỏ qua dòng trống
                if not line_clean:
                    continue
                
                # KIỂM TRA NGHIÊM NGẶT - Bỏ qua tất cả dòng chứa từ khóa gợi ý
                skip_keywords = [
                    "GỢI Ý", "GOI Y", "TIÊU ĐỀ", "TIEU DE", "CAPTION", "CALL TO ACTION", "CTA",
                    "TIKTOK", "HASHTAG", "PENTHOUSE", "MOTHAIT", "VIRAL", "MEOHAY",
                    "XAYNHA", "XAYDUNG", "KIENTHUC", "NHADEEP", "THIETKE"
                ]
                
                if any(keyword in line_clean.upper() for keyword in skip_keywords):
                    skip_section = True
                    continue
                
                # Bỏ qua các dòng bắt đầu bằng số (1., 2., 3., ...)
                if re.match(r'^\d+\.', line_clean):
                    continue
                    
                # Bỏ qua các dòng có icon, hashtag, hoặc ký tự đặc biệt
                if any(char in line_clean for char in ['📋', '📝', '📱', '🎯', '😍', '❤️', '#', '🏠', '🔥', '💡']):
                    continue
                
                # Bỏ qua dòng chỉ có dấu hoặc ký tự đặc biệt
                if line_clean in ['---', '===', '***'] or len(line_clean.replace(' ', '').replace('-', '').replace('=', '').replace('*', '')) < 3:
                    continue
                
                # Nếu dòng có (Giây ...) thì đây chắc chắn là nội dung chính
                if "(Giây" in line_clean or "(giây" in line_clean:
                    skip_section = False
                    main_content_lines.append(line_clean)
                    continue
                
                # Chỉ lấy nội dung thật sự - phải có ít nhất 15 ký tự và không trong section gợi ý
                if not skip_section and len(line_clean) > 15:
                    # Kiểm tra thêm - không được chứa các từ nghi ngờ
                    suspicious_words = ["hack", "mẹo", "bí quyết", "chiêu", "tip", "trick"]
                    if not any(word in line_clean.lower() for word in suspicious_words):
                        main_content_lines.append(line_clean)
                    elif "(Giây" in line_clean:  # Nếu có timeline thì vẫn lấy
                        main_content_lines.append(line_clean)
            
            return '\n'.join(main_content_lines).strip() if main_content_lines else ""
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract only main content: {str(e)}")
            return text

    def _filter_main_content_line_by_line(self, text: str) -> str:
        """
        Lọc từng dòng để chỉ lấy nội dung chính, loại bỏ hoàn toàn gợi ý
        
        Args:
            text: Text đầy đủ
            
        Returns:
            Chỉ nội dung chính
        """
        try:
            lines = text.split('\n')
            main_lines = []
            in_suggestion_section = False
            
            for line in lines:
                line_clean = line.strip()
                
                # Bỏ qua dòng trống
                if not line_clean:
                    continue
                
                # Kiểm tra xem có phải dòng bắt đầu section gợi ý không
                suggestion_starters = [
                    "GỢI Ý", "GOI Y", "TIÊU ĐỀ", "TIEU DE",
                    "Gợi ý", "Gợi ý 5 tiêu đề", "Gợi ý 3 caption",
                    "CAPTION", "CALL TO ACTION", "CTA"
                ]
                
                if any(starter in line_clean.upper() for starter in suggestion_starters):
                    in_suggestion_section = True
                    continue
                
                # Bỏ qua tất cả dòng trong section gợi ý
                if in_suggestion_section:
                    # Chỉ thoát khỏi suggestion section nếu gặp timeline mới
                    if "(Giây" in line_clean or "(giây" in line_clean:
                        in_suggestion_section = False
                        main_lines.append(line_clean)
                    continue
                
                # Bỏ qua dòng bắt đầu bằng số
                if re.match(r'^\d+\.', line_clean):
                    continue
                
                # Bỏ qua dòng có hashtag hoặc icon
                if '#' in line_clean or any(icon in line_clean for icon in ['📋', '📝', '📱', '🎯', '😍', '❤️']):
                    continue
                
                # Bỏ qua dòng tiêu đề "NỘI DUNG CHÍNH"
                if "NỘI DUNG CHÍNH" in line_clean.upper():
                    continue
                
                # Chỉ lấy dòng có nội dung thật sự
                if len(line_clean) > 10:
                    main_lines.append(line_clean)
            
            return '\n'.join(main_lines)
            
        except Exception as e:
            logger.error(f"❌ Lỗi filter main content line by line: {str(e)}")
            return text

    def _format_text_no_timeline(self, text: str) -> str:
        """
        Format chỉ nội dung thuần túy không có timeline, không có đề mục, không có gợi ý
        Sử dụng phương pháp lưu tạm và xóa để đảm bảo loại bỏ hoàn toàn gợi ý
        
        Args:
            text: Text cần format (có cấu trúc đầy đủ)
            
        Returns:
            Chỉ nội dung thuần túy không timeline
        """
        try:
            # Bước 1: Lưu text gốc vào bộ nhớ tạm
            temp_text = text
            
            # Bước 2: Loại bỏ tất cả section gợi ý bằng cách cắt text
            # Tìm vị trí bắt đầu của nội dung chính
            main_content_start = -1
            main_content_end = -1
            
            # Tìm điểm bắt đầu nội dung chính
            if "NỘI DUNG CHÍNH" in temp_text:
                main_content_start = temp_text.find("NỘI DUNG CHÍNH")
            elif "Nội dung chính" in temp_text:
                main_content_start = temp_text.find("Nội dung chính")
            elif "**📝 NỘI DUNG CHÍNH" in temp_text:
                main_content_start = temp_text.find("**📝 NỘI DUNG CHÍNH")
            
            if main_content_start != -1:
                # Tìm điểm kết thúc (trước khi bắt đầu gợi ý)
                end_markers = [
                    "GỢI Ý", "GOI Y", "Gợi ý", "Gợi ý 3 caption",
                    "CAPTION", "CALL TO ACTION", "CTA"
                ]
                
                for marker in end_markers:
                    marker_pos = temp_text.find(marker, main_content_start + 20)  # Tìm sau vị trí bắt đầu
                    if marker_pos != -1:
                        if main_content_end == -1 or marker_pos < main_content_end:
                            main_content_end = marker_pos
                
                # Cắt lấy chỉ phần nội dung chính
                if main_content_end != -1:
                    main_content = temp_text[main_content_start:main_content_end]
                else:
                    main_content = temp_text[main_content_start:]
            else:
                # Fallback: Lọc từng dòng
                main_content = self._filter_main_content_line_by_line(temp_text)
            
            # Bước 3: Xóa bộ nhớ tạm
            temp_text = None
            
            # Bước 4: Format nội dung chính và loại bỏ dòng tiêu đề
            if main_content:
                # Loại bỏ dòng tiêu đề "NỘI DUNG CHÍNH"/"Nội dung chính" nếu còn
                lines = main_content.split('\n')
                cleaned_lines = []
                for line in lines:
                    line_clean = line.strip()
                    if line_clean and ("NỘI DUNG CHÍNH" not in line_clean.upper()) and ("Nội dung chính" not in line_clean):
                        cleaned_lines.append(line)
                
                main_content_cleaned = '\n'.join(cleaned_lines)
                formatted_content = self._format_main_content_only(main_content_cleaned)
                return formatted_content.strip()
            
            return "(Không có nội dung)"
            
        except Exception as e:
            logger.error(f"❌ Lỗi format text no timeline: {str(e)}")
            return text
    
    def _format_suggestions_content(self, text: str) -> str:
        """
        Format chỉ 3 phần: Gợi ý tiêu đề + Caption + CTA (rõ ràng từng phần)
        
        Args:
            text: Text cần format (có cấu trúc đầy đủ)
            
        Returns:
            Text chứa 3 phần rõ ràng: tiêu đề + captions + CTA
        """
        try:
            formatted_parts = []
            
            # 1. GỢI Ý 5 TIÊU ĐỀ - CẢI THIỆN TÌM KIẾM
            titles_content = ""
            
            # Debug: Log để kiểm tra tiêu đề
            logger.info(f"🔍 Đang tìm tiêu đề trong text")
            
            # Thử nhiều cách tìm tiêu đề
            title_markers = [
                "GỢI Ý 5 TIÊU ĐỀ:",
                "**📋 GỢI Ý 5 TIÊU ĐỀ:**",
                "GỢI Ý 5 TIÊU ĐỀ",
                "Gợi ý 5 tiêu đề",
                "5 TIÊU ĐỀ"
            ]
            
            for marker in title_markers:
                if marker in text:
                    # Tìm end marker phù hợp - CHỈ LẤY ĐẾN CAPTION, KHÔNG LẤY NỘI DUNG CHÍNH
                    end_markers = [
                        "GỢI Ý 3 CAPTION",
                        "Gợi ý 3 caption",
                        "**📱 GỢI Ý 3 CAPTION",
                        "CAPTION TIKTOK",
                        "CALL TO ACTION",
                        "CTA:",
                        "CTA",
                        "==="
                    ]
                    titles_section = ""
                    
                    for end_marker in end_markers:
                        titles_section = self._extract_section(text, marker, end_marker)
                        if titles_section and len(titles_section.strip()) > 10:
                            break
                    
                    if titles_section:
                        titles_content = self._format_titles_section(titles_section)
                        logger.info(f"✅ Tìm thấy tiêu đề với marker: {marker}")
                        logger.info(f"✅ Titles content: {titles_content[:100]}...")
                        break
            
            if titles_content:
                formatted_parts.append("****Gợi ý 5 tiêu đề")
                formatted_parts.append(titles_content)
            else:
                logger.warning("⚠️ Không tìm thấy tiêu đề, tạo tiêu đề mặc định")
                default_titles = """1. "Thiết kế tủ giày âm tường: Giải pháp tối ưu cho không gian hiện đại!"
2. "Tủ giày âm tường: Kết hợp hoàn hảo giữa thẩm mỹ và công năng!"
3. "Thiết kế tủ giày thông minh: Tối ưu hóa không gian sống!"
4. "Tủ giày âm tường đa năng: Giải pháp thiết kế tiên tiến!"
5. "Tủ giày âm tường: Nâng tầm không gian sống với thiết kế chuyên nghiệp!" """
                formatted_parts.append("****Gợi ý 5 tiêu đề")
                formatted_parts.append(default_titles)
            
            # 2. GỢI Ý 3 CAPTION TIKTOK - CẢI THIỆN TÌM KIẾM
            captions_content = ""
            
            # Debug: Log để kiểm tra caption
            logger.info(f"🔍 Đang tìm caption trong text")
            
            # Thử nhiều cách tìm caption
            caption_markers = [
                "GỢI Ý 3 CAPTION TIKTOK:",
                "**📱 GỢI Ý 3 CAPTION TIKTOK:**",
                "GỢI Ý 3 CAPTION",
                "Gợi ý 3 caption",
                "CAPTION TIKTOK"
            ]
            
            for marker in caption_markers:
                if marker in text:
                    # Tìm end marker phù hợp - CHỈ LẤY ĐẾN CTA, KHÔNG LẤY NỘI DUNG CHÍNH
                    end_markers = [
                        "CALL TO ACTION",
                        "**🎯 CALL TO ACTION",
                        "CTA:",
                        "CTA",
                        "==="
                    ]
                    captions_section = ""
                    
                    for end_marker in end_markers:
                        captions_section = self._extract_section(text, marker, end_marker)
                        if captions_section and len(captions_section.strip()) > 10:
                            break
                    
                    if captions_section:
                        captions_content = self._format_captions_section(captions_section)
                        logger.info(f"✅ Tìm thấy caption với marker: {marker}")
                        logger.info(f"✅ Caption content: {captions_content[:100]}...")
                        break
            
            if captions_content:
                formatted_parts.append("****Gợi ý 3 caption")
                formatted_parts.append(captions_content)
            else:
                logger.warning("⚠️ Không tìm thấy caption, tạo caption mặc định")
                default_captions = """1. "Thiết kế tủ giày âm tường: Giải pháp tối ưu cho không gian hiện đại! #thietkenoithat #tugiayamtuong #khonggianhiendai"
2. "Tủ giày âm tường: Kết hợp hoàn hảo giữa thẩm mỹ và công năng! #noithat #tugiay #thietkechuyennghiep"
3. "Thiết kế tủ giày thông minh: Tối ưu hóa không gian sống! #tugiaythongminh #toiuuhoa #khonggiansong" """
                formatted_parts.append("****Gợi ý 3 caption")
                formatted_parts.append(default_captions)
            
            # 3. CALL TO ACTION - CẢI THIỆN TÌM KIẾM LINH HOẠT
            cta_content = ""
            
            # Debug: Log toàn bộ text để kiểm tra
            logger.info(f"🔍 Đang tìm CTA trong text ({len(text)} ký tự)")
            logger.info(f"🔍 Text preview: {text[:500]}...")
            
            # Thử nhiều cách tìm CTA
            cta_markers = [
                "CALL TO ACTION (CTA) - VIẾT MỚI DỰA TRÊN MẪU:",
                "CALL TO ACTION (CTA):",
                "CALL TO ACTION:",
                "**🎯 CALL TO ACTION**",
                "**🎯 CALL TO ACTION:**",
                "CTA:",
                "CTA",
                "Call to action:"
            ]
            
            for marker in cta_markers:
                if marker in text:
                    cta_section = self._extract_section(text, marker, None)
                    if cta_section:
                        cta_content = self._format_cta_section(cta_section)
                        logger.info(f"✅ Tìm thấy CTA với marker: {marker}")
                        logger.info(f"✅ CTA content: {cta_content[:100]}...")
                        break
            
            # Nếu không tìm thấy, thử tìm dòng có chứa CTA
            if not cta_content:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['call to action', 'cta', 'lưu lại', 'chia sẻ', 'bình luận']):
                        # Lấy dòng đó và vài dòng tiếp theo
                        cta_lines = []
                        for j in range(i, min(i + 3, len(lines))):
                            if lines[j].strip():
                                cta_lines.append(lines[j].strip())
                        if cta_lines:
                            cta_content = ' '.join(cta_lines)
                            logger.info(f"✅ Tìm thấy CTA trong dòng: {line[:50]}...")
                            break
            
            if cta_content:
                formatted_parts.append("****CTA")
                formatted_parts.append(cta_content)
            else:
                logger.warning("⚠️ Không tìm thấy CTA trong text")
                # Tạo CTA mặc định
                default_cta = "Thiết kế này sẽ nâng tầm không gian sống của các bác! Lưu lại ngay để tham khảo, chia sẻ cho bạn bè cùng xem nhé!"
                formatted_parts.append("****CTA")
                formatted_parts.append(default_cta)
            
            # Nối 3 phần với xuống dòng đôi để rõ ràng, loại bỏ khoảng trống đầu cuối
            result = '\n\n'.join(formatted_parts).strip()
            
            # KIỂM TRA CUỐI CÙNG: Đảm bảo không có nội dung chính nào bị lọt vào
            if ("NỘI DUNG CHÍNH" in result or "Nội dung chính" in result or "Giây" in result):
                logger.warning("⚠️ Phát hiện nội dung chính trong kết quả, đang lọc lại...")
                # Lọc lại từng dòng để loại bỏ nội dung chính
                lines = result.split('\n')
                filtered_lines = []
                for line in lines:
                    line_clean = line.strip()
                    if (line_clean and 
                        ("NỘI DUNG CHÍNH" not in line_clean.upper()) and ("Nội dung chính" not in line_clean) and
                        not line_clean.startswith("Giây") and
                        not "Giây" in line_clean):
                        filtered_lines.append(line)
                result = '\n'.join(filtered_lines).strip()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi format suggestions content: {str(e)}")
            return ""
    
    def _format_full_structure_with_newlines(self, text: str) -> str:
        """
        Format cấu trúc đầy đủ với xuống dòng đẹp - CHỈ BAO GỒM 3 PHẦN CHÍNH
        """
        try:
            formatted_parts = []
            
            # 1. Trích xuất và format 5 tiêu đề
            if "**📋 GỢI Ý 5 TIÊU ĐỀ:**" in text or "Gợi ý 5 tiêu đề" in text or "GỢI Ý 5 TIÊU ĐỀ" in text:
                if "**📋 GỢI Ý 5 TIÊU ĐỀ:**" in text:
                    titles_section = self._extract_section(text, "**📋 GỢI Ý 5 TIÊU ĐỀ:**", "**📱 GỢI Ý 3 CAPTION")
                elif "Gợi ý 5 tiêu đề" in text:
                    titles_section = self._extract_section(text, "Gợi ý 5 tiêu đề", "Gợi ý 3 caption")
                    if not titles_section:
                        titles_section = self._extract_section(text, "Gợi ý 5 tiêu đề", "GỢI Ý 3 CAPTION")
                else:
                    titles_section = self._extract_section(text, "GỢI Ý 5 TIÊU ĐỀ", "GỢI Ý 3 CAPTION")
                if titles_section:
                    formatted_titles = self._format_titles_section(titles_section)
                    if formatted_titles:
                        formatted_parts.append("*Gợi ý 5 tiêu đề")
                        formatted_parts.append(formatted_titles)
            
            # 2. Trích xuất và format captions
            if ("**📱 GỢI Ý 3 CAPTION TIKTOK:**" in text) or ("Gợi ý 3 caption" in text) or ("GỢI Ý 3 CAPTION" in text):
                if "**📱 GỢI Ý 3 CAPTION TIKTOK:**" in text:
                    captions_section = self._extract_section(text, "**📱 GỢI Ý 3 CAPTION TIKTOK:**", "**🎯 CALL TO ACTION")
                elif "Gợi ý 3 caption" in text:
                    captions_section = self._extract_section(text, "Gợi ý 3 caption", "CTA")
                    if not captions_section:
                        captions_section = self._extract_section(text, "Gợi ý 3 caption", "CALL TO ACTION")
                else:
                    captions_section = self._extract_section(text, "GỢI Ý 3 CAPTION", "CALL TO ACTION")
                if captions_section:
                    formatted_captions = self._format_captions_section(captions_section)
                    if formatted_captions:
                        formatted_parts.append("*Gợi ý 3 caption")
                        formatted_parts.append(formatted_captions)
            
            # 3. Trích xuất và format CTA
            if ("**🎯 CALL TO ACTION" in text) or ("CTA" in text):
                if "**🎯 CALL TO ACTION" in text:
                    cta_section = self._extract_section(text, "**🎯 CALL TO ACTION", None)
                else:
                    cta_section = self._extract_section(text, "CTA", None)
                if cta_section:
                    formatted_cta = self._format_cta_section(cta_section)
                    if formatted_cta:
                        formatted_parts.append("*CTA")
                        formatted_parts.append(formatted_cta)
            
            # Nối tất cả với xuống dòng đôi
            return '\n\n'.join(formatted_parts).strip()
            
        except Exception as e:
            logger.error(f"❌ Lỗi format full structure: {str(e)}")
            return text
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str = None) -> str:
        """Trích xuất một section từ text"""
        try:
            if start_marker not in text:
                return ""
            
            parts = text.split(start_marker)
            if len(parts) < 2:
                return ""
            
            content = parts[1]
            
            if end_marker and end_marker in content:
                content = content.split(end_marker)[0]
            
            return content.strip()
        except:
            return ""
    
    def _format_titles_section(self, titles_text: str) -> str:
        """Format section tiêu đề với số thứ tự rõ ràng"""
        try:
            lines = titles_text.split('\n')
            formatted_titles = []
            counter = 1
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('['):
                    # Loại bỏ số thứ tự cũ và thêm số thứ tự mới
                    if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                        title_content = line.split('.', 1)[1].strip()
                        if title_content and not title_content.startswith('['):
                            # Loại bỏ dấu ngoặc vuông nếu có
                            title_content = re.sub(r'^\[|\]$', '', title_content).strip()
                            formatted_titles.append(f"{counter}. {title_content}")
                            counter += 1
                    elif not line.startswith(('GỢI Ý', 'GOI Y')) and len(line) > 5:
                        # Dòng không có số thứ tự nhưng là tiêu đề
                        title_content = re.sub(r'^\[|\]$', '', line).strip()
                        if title_content:
                            formatted_titles.append(f"{counter}. {title_content}")
                            counter += 1
            
            return '\n'.join(formatted_titles).strip() if formatted_titles else ""
        except:
            return ""

    def _format_titles_section_no_diacritics(self, titles_text: str) -> str:
        """Format section tiêu đề không có dấu với xuống dòng đẹp"""
        try:
            lines = titles_text.split('\n')
            formatted_titles = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('['):
                    # Loại bỏ số thứ tự và format lại
                    if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                        title_content = line.split('.', 1)[1].strip()
                        if title_content and not title_content.startswith('['):
                            # Chuyển thành không dấu
                            no_diacritics = self._remove_diacritics(title_content)
                            formatted_titles.append(no_diacritics)
            
            return '\n'.join(formatted_titles) if formatted_titles else ""
        except:
            return ""
    
    def _format_captions_section(self, captions_text: str) -> str:
        """Format section captions với số thứ tự rõ ràng"""
        try:
            lines = captions_text.split('\n')
            formatted_captions = []
            counter = 1
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('['):
                    # Loại bỏ số thứ tự cũ và thêm số thứ tự mới
                    if line.startswith(('1.', '2.', '3.')):
                        caption_content = line.split('.', 1)[1].strip()
                        if caption_content and not caption_content.startswith('['):
                            # Loại bỏ dấu ngoặc vuông nếu có
                            caption_content = re.sub(r'^\[|\]$', '', caption_content).strip()
                            formatted_captions.append(f"{counter}. {caption_content}")
                            counter += 1
                    elif not line.startswith(('GỢI Ý', 'GOI Y')) and len(line) > 10:
                        # Dòng không có số thứ tự nhưng là caption
                        caption_content = re.sub(r'^\[|\]$', '', line).strip()
                        if caption_content:
                            formatted_captions.append(f"{counter}. {caption_content}")
                            counter += 1
            
            return '\n'.join(formatted_captions).strip() if formatted_captions else ""
        except:
            return ""

    def _format_captions_section_no_diacritics(self, captions_text: str) -> str:
        """Format section captions không có dấu với xuống dòng đẹp"""
        try:
            lines = captions_text.split('\n')
            formatted_captions = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('['):
                    # Loại bỏ số thứ tự và format lại
                    if line.startswith(('1.', '2.', '3.')):
                        caption_content = line.split('.', 1)[1].strip()
                        if caption_content and not caption_content.startswith('['):
                            # Chuyển thành không dấu
                            no_diacritics = self._remove_diacritics(caption_content)
                            formatted_captions.append(no_diacritics)
            
            return '\n'.join(formatted_captions) if formatted_captions else ""
        except:
            return ""
    
    def _format_cta_section(self, cta_text: str) -> str:
        """Format section CTA - CẢI THIỆN"""
        try:
            lines = cta_text.split('\n')
            cta_lines = []
            
            for line in lines:
                line = line.strip()
                # Bỏ qua dòng rỗng, marker, và dấu ngoặc vuông
                if (line and 
                    not line.startswith('**') and 
                    not line.startswith('[') and 
                    not line.startswith('===') and
                    not line.lower().startswith('call to action') and
                    not line.lower().startswith('cta')):
                    
                    # Loại bỏ dấu ngoặc kép nếu có
                    line = line.strip('"').strip("'").strip()
                    if line:
                        cta_lines.append(line)
            
            # Nếu có nhiều dòng, ghép lại
            if cta_lines:
                cta_result = ' '.join(cta_lines)
                logger.info(f"✅ Đã format CTA: {cta_result[:100]}...")
                return cta_result
            
            # Nếu không tìm thấy, tạo CTA mặc định
            logger.warning("⚠️ Không tìm thấy CTA hợp lệ, tạo CTA mặc định")
            return "Thiết kế này sẽ nâng tầm không gian sống của các bác! Lưu lại ngay để tham khảo, chia sẻ cho bạn bè cùng xem nhé!"
            
        except Exception as e:
            logger.error(f"❌ Lỗi format CTA: {str(e)}")
            return "Thiết kế này sẽ nâng tầm không gian sống của các bác! Lưu lại ngay để tham khảo, chia sẻ cho bạn bè cùng xem nhé!"

    def _format_cta_section_no_diacritics(self, cta_text: str) -> str:
        """Format section CTA không có dấu"""
        try:
            lines = cta_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('['):
                    # Chuyển thành không dấu
                    no_diacritics = self._remove_diacritics(line)
                    return no_diacritics
            return ""
        except:
            return ""
    
    def _remove_diacritics(self, text: str) -> str:
        """Chuyển tiếng Việt có dấu thành không dấu"""
        try:
            # Bảng chuyển đổi tiếng Việt
            vietnamese_map = {
                'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
                'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
                'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
                'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
                'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
                'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
                'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
                'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
                'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
                'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
                'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
                'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
                'đ': 'd',
                # Chữ hoa
                'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
                'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
                'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
                'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
                'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
                'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
                'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
                'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
                'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
                'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
                'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
                'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
                'Đ': 'D'
            }
            
            result = ""
            for char in text:
                result += vietnamese_map.get(char, char)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi remove diacritics: {str(e)}")
            return text

    def _extract_lead_in(self, text: str, max_sentences: int = 2) -> str:
        """Trích xuất 1-2 câu vào đề đầu tiên từ text đã làm sạch (không timeline)."""
        try:
            import re
            compact = re.sub(r"\s+", " ", text).strip()
            if not compact:
                return ""
            # Tách câu theo dấu kết thúc. Hỗ trợ ., !, ?, … và ...
            parts = re.split(r"(?<=[\.!\?…])\s+", compact)
            sentences = []
            for part in parts:
                p = part.strip()
                if p:
                    sentences.append(p)
                if len(sentences) >= max_sentences:
                    break
            return " ".join(sentences).strip()
        except Exception:
            return text.strip().split("\n")[0][:200]

    def _generate_lead_in_hook(self, text: str) -> str:
        """
        Tạo "Câu vào đề" hấp dẫn dựa trên nội dung chính (không dùng câu đầu tiên).
        Nguyên tắc: phân tích nội dung thực tế và tạo hook phù hợp với chủ đề cụ thể.
        """
        try:
            import re
            # Chuẩn hóa và rút gọn văn bản để phân tích nội dung
            normalized = re.sub(r"[\n\r]", " ", text)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            lower = normalized.lower()

            # Danh sách stopwords tiếng Việt
            stopwords = set([
                'là','và','của','cho','các','bác','em','anh','chị','nhé','ạ','thì','để','vì',
                'khi','này','đó','nên','không','rất','nhiều','một','cái','đi','làm','trong','ra',
                'vào','với','được','đến','nếu','vẫn','hay','đã','sẽ','có','nhưng','vậy','thế','rồi'
            ])

            # Tách từ và phân tích từ khóa chính
            tokens = re.findall(r"[a-zA-ZÀ-ỹÀ-Ỹ0-9_]+", lower)
            freq = {}
            for tok in tokens:
                if tok.isdigit():
                    continue
                if len(tok) < 4:
                    continue
                if tok in stopwords:
                    continue
                freq[tok] = freq.get(tok, 0) + 1

            # Sắp xếp từ khóa theo tần suất và độ dài
            sorted_keywords = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
            top_keywords = [w for w, _ in sorted_keywords[:8]]  # Lấy nhiều hơn để phân tích

            # Phân tích chủ đề chính dựa trên từ khóa
            construction_words = {'xây', 'nhà', 'thiết', 'kế', 'công', 'trình', 'thợ', 'xây dựng', 'kiến trúc'}
            furniture_words = {'tủ', 'giày', 'bàn', 'ghế', 'sofa', 'giường', 'kệ', 'nội thất'}
            space_words = {'không gian', 'phòng', 'sảnh', 'nhà bếp', 'phòng ngủ', 'phòng khách'}
            material_words = {'gỗ', 'sắt', 'thép', 'bê tông', 'gạch', 'xi măng', 'sơn'}
            problem_words = {'toang', 'hỏng', 'lỗi', 'sai', 'mất', 'thiệt', 'oan', 'trễ', 'nứt', 'rò', 'thấm'}
            solution_words = {'bí', 'quyết', 'mẹo', 'tối', 'ưu', 'giải', 'pháp', 'tiết', 'kiệm', 'hiệu', 'quả'}

            # Xác định chủ đề chính
            topic = "thiết kế"
            if any(w in construction_words for w in top_keywords):
                topic = "xây dựng"
            elif any(w in furniture_words for w in top_keywords):
                topic = "nội thất"
            elif any(w in space_words for w in top_keywords):
                topic = "không gian"
            elif any(w in material_words for w in top_keywords):
                topic = "vật liệu"

            # Kiểm tra có vấn đề/rủi ro không
            has_problem = any(w in problem_words for w in top_keywords)
            has_solution = any(w in solution_words for w in top_keywords)

            # Lấy 2-3 từ khóa chính để đưa vào hook
            main_keywords = top_keywords[:3] if len(top_keywords) >= 3 else top_keywords

            # Tạo hook dựa trên chủ đề và từ khóa thực tế
            if has_problem:
                # Hook cảnh báo về vấn đề
                kw1 = main_keywords[0] if main_keywords else 'chi tiết'
                kw2 = main_keywords[1] if len(main_keywords) > 1 else 'công trình'
                hook = f"Đừng để {kw1} {kw2} làm hỏng cả dự án. Xem tiếp để em chỉ bác cách tránh những lỗi này."
            elif has_solution:
                # Hook về giải pháp/lợi ích
                kw1 = main_keywords[0] if main_keywords else 'thiết kế'
                kw2 = main_keywords[1] if len(main_keywords) > 1 else 'không gian'
                hook = f"Bí quyết {kw1} {kw2} mà nhiều bác hay bỏ lỡ. Ở phần sau, em chỉ bác từng bước cụ thể."
            elif topic == "xây dựng":
                # Hook về xây dựng
                kw1 = main_keywords[0] if main_keywords else 'công trình'
                hook = f"Nhiều bác cứ nghĩ {kw1} là chuyện của thợ, nhưng đến khi có vấn đề thì mình mới là người sửa."
            elif topic == "nội thất":
                # Hook về nội thất
                kw1 = main_keywords[0] if main_keywords else 'thiết kế'
                hook = f"Bí quyết {kw1} không gian gọn gàng mà nhiều bác hay bỏ lỡ. Xem tiếp để nắm chuẩn từng bước."
            else:
                # Hook chung
                kw1 = main_keywords[0] if main_keywords else 'thiết kế'
                hook = f"Đừng bỏ lỡ {kw1} quan trọng này. Xem tiếp để em chỉ bác cách làm đúng ngay lần đầu."

            return hook
        except Exception:
            # Fallback an toàn
            return "Đừng bỏ lỡ những chi tiết quan trọng này. Xem tiếp để em chỉ bác cách làm đúng."

    def _format_main_content_only(self, text: str) -> str:
        """Format chỉ nội dung chính, loại bỏ timeline"""
        try:
            # Loại bỏ timeline patterns
            import re
            timeline_pattern = r'\(Giây\s+\d+-\d+\)'
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Xử lý dòng có timeline: chỉ lấy nội dung sau timeline
                if re.search(timeline_pattern, line):
                    match = re.search(timeline_pattern, line)
                    if match:
                        content_after_timeline = line[match.end():].strip()
                        if content_after_timeline:
                            cleaned_lines.append(content_after_timeline)
                else:
                    # Nếu không có timeline, giữ nguyên dòng
                    if line and not line.startswith('[') and not line.startswith('**'):
                        cleaned_lines.append(line)
            
            # Nhóm thành các đoạn (2-3 câu/đoạn)
            if cleaned_lines:
                paragraphs = []
                current_paragraph = []
                
                for line in cleaned_lines:
                    current_paragraph.append(line)
                    # Tạo đoạn mới khi đủ điều kiện
                    should_break = (
                        len(current_paragraph) >= 3 or
                        any(end_word in line.lower() for end_word in ['nên', 'rồi', 'đấy', 'nhé', 'ạ', 'thế', 'luôn', 'được']) or
                        len(' '.join(current_paragraph)) > 150
                    )
                    
                    if should_break:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                
                # Thêm đoạn cuối
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                
                # Nối các đoạn bằng xuống dòng đôi
                return '\n\n'.join(paragraphs).strip()
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ Lỗi format main content: {str(e)}")
            return text
    
    def upload_to_drive(self, file_path: str, folder_id: str) -> str:
        """
        Upload file lên Google Drive
        
        Args:
            file_path: Đường dẫn đến file cần upload
            folder_id: ID của folder trên Google Drive
            
        Returns:
            ID của file đã upload trên Google Drive
        """
        try:
            # Xác định MIME type dựa trên extension
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.txt':
                mime_type = 'text/plain'
            elif file_ext == '.mp3':
                mime_type = 'audio/mpeg'
            else:
                mime_type = 'application/octet-stream'
            
            # Chuẩn bị metadata cho file
            file_metadata = {
                'name': os.path.basename(file_path),
                'mimeType': mime_type,
                'parents': [folder_id]
            }
            
            # Tạo media upload object
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            logger.info(f"🔄 Đang upload: {os.path.basename(file_path)}")
            
            # Upload file lên Google Drive
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name'
            ).execute()
            
            # Lấy thông tin file đã upload
            file_id = file.get('id')
            file_name = file.get('name')
            logger.info(f"✅ Upload thành công! File: {file_name}, ID: {file_id}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Lỗi upload: {str(e)}")
            raise
    
    def process_all(self, input_folder_id: str, voice_folder_id: str, 
                   text_original_folder_id: str, text_rewritten_folder_id: str, 
                   # text_to_speech_folder_id: str,  # ĐÃ COMMENT
                   video_name: str = "video1.mp4") -> Dict:
        """
        Xử lý một video: Video -> Voice Only -> Text -> Rewrite -> Drive (TTS đã comment)
        
        Luồng xử lý hoàn chỉnh:
        1. Tìm video trong folder input
        2. Tải video từ Google Drive
        3. Tách voice từ video (loại bỏ background music)
        4. Upload voice only lên Google Drive
        5. Chuyển đổi voice thành text bằng Deepgram
        6. Upload text gốc lên Google Drive
        7. Viết lại text bằng Gemini
        8. Upload text đã viết lại lên Google Drive
        
        Args:
            input_folder_id: ID folder chứa video input
            voice_folder_id: ID folder để upload voice only
            text_original_folder_id: ID folder để upload text gốc
            text_rewritten_folder_id: ID folder để upload text đã viết lại
            video_name: Tên video cần xử lý
            
        Returns:
            Dict chứa kết quả xử lý
        """
        try:
            logger.info(f"🚀 === BẮT ĐẦU XỬ LÝ: {video_name} ===")
            
            # Bước 1: Tìm video trong folder input
            logger.info("📂 Bước 1: Tìm video trong folder...")
            video_info = self.find_video_in_folder(input_folder_id, video_name)
            if not video_info:
                return {
                    'status': 'error',
                    'video_name': video_name,
                    'error': f'Không tìm thấy video {video_name}'
                }
            
            file_id = video_info['id']
            
            # Bước 2: Tải video từ Google Drive
            logger.info("📥 Bước 2: Tải video từ Google Drive...")
            video_path = self.download_video(file_id, video_name)
            
            # Bước 3: Tách voice từ video (loại bỏ background music)
            logger.info("🎤 Bước 3: Tách voice từ video...")
            voice_path = self.extract_voice_only(video_path, video_name)
            
            # Bước 4: Upload voice only lên Google Drive
            logger.info("☁️ Bước 4: Upload voice only lên Google Drive...")
            voice_file_id = self.upload_to_drive(voice_path, voice_folder_id)
            
            # Bước 5: Chuyển đổi voice thành text bằng Deepgram
            logger.info("📝 Bước 5: Chuyển đổi voice thành text...")
            text_path, detected_language, is_chinese = self.extract_text_with_language_detection(voice_path, video_name)
            
            # Bước 6: Dịch tiếng Trung sang tiếng Việt nếu cần
            if is_chinese:
                logger.info("🌐 Bước 6: Dịch tiếng Trung sang tiếng Việt...")
                translated_text_path = self.translate_chinese_to_vietnamese(text_path, video_name)
                text_path = translated_text_path # Cập nhật đường dẫn file text gốc
            
            # Bước 7: Upload text gốc lên Google Drive
            logger.info("📄 Bước 7: Upload text gốc lên Google Drive...")
            text_file_id = self.upload_to_drive(text_path, text_original_folder_id)
            
            # Bước 8: Viết lại text bằng Gemini
            logger.info("✍️ Bước 8: Viết lại text bằng Gemini...")
            rewritten_text_path = self.rewrite_text(text_path, video_name)
            
            # Bước 9: Upload text đã viết lại lên Google Drive
            logger.info("📄 Bước 9: Upload text đã viết lại lên Google Drive...")
            rewritten_text_file_id = self.upload_to_drive(rewritten_text_path, text_rewritten_folder_id)
            
            # Bước 10: Tạo nội dung chính có timeline (cho cột Text cải tiến)
            logger.info("📝 Bước 10: Tạo nội dung chính có timeline...")
            main_content_path = self.create_main_content_only(rewritten_text_path, video_name)
            
            # Bước 11: Tạo text không có timeline (cho cột Text no timeline)
            logger.info("📄 Bước 11: Tạo text không có timeline...")
            text_no_timeline_path = self.create_text_without_timeline(rewritten_text_path, video_name)
            
            # Bước 12: Tạo gợi ý tiêu đề, captions, CTA (cho cột Gợi ý tiêu đề)
            logger.info("💡 Bước 12: Tạo gợi ý tiêu đề, captions, CTA...")
            suggestions_path = self.create_suggestions_content(rewritten_text_path, video_name)
            
            # Bước 11: Chuyển đổi text đã viết lại thành speech - ĐÃ COMMENT
            # logger.info("🎤 Bước 11: Chuyển đổi text thành speech...")
            # tts_audio_path = self.text_to_speech(rewritten_text_path, video_name)
            
            # Bước 12: Upload audio TTS lên Google Drive - ĐÃ COMMENT
            # logger.info("☁️ Bước 12: Upload audio TTS lên Google Drive...")
            # tts_file_id = self.upload_to_drive(tts_audio_path, text_to_speech_folder_id)
            
            logger.info("✅ === HOÀN THÀNH XỬ LÝ ===")
            
            return {
                'status': 'success',
                'video_name': video_name,
                'video_file_id': file_id,  # Thêm ID của file video MP4
                'voice_file_id': voice_file_id,
                'text_file_id': text_file_id,
                'rewritten_text_file_id': rewritten_text_file_id,
                # 'tts_file_id': tts_file_id,  # ĐÃ COMMENT
                'voice_path': voice_path,
                'text_path': text_path,
                'rewritten_text_path': rewritten_text_path,
                'main_content_path': main_content_path,
                'text_no_timeline_path': text_no_timeline_path,
                'suggestions_path': suggestions_path,
                # 'tts_audio_path': tts_audio_path  # ĐÃ COMMENT
            }
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong quá trình xử lý: {str(e)}")
            return {
                'status': 'error',
                'video_name': video_name,
                'error': str(e)
            }
    
    def process_all_videos(self, input_folder_id: str, voice_folder_id: str, 
                          text_original_folder_id: str, text_rewritten_folder_id: str,
                          # text_to_speech_folder_id: str  # ĐÃ COMMENT
                          ) -> List[Dict]:
        """
        Xử lý tất cả video trong folder: Video -> Voice Only -> Text -> Rewrite -> Drive (TTS đã comment)
        
        Args:
            input_folder_id: ID folder chứa video input
            voice_folder_id: ID folder để upload voice only
            text_original_folder_id: ID folder để upload text gốc
            text_rewritten_folder_id: ID folder để upload text đã viết lại
            
        Returns:
            List chứa kết quả xử lý tất cả video
        """
        try:
            logger.info(f"🚀 === BẮT ĐẦU XỬ LÝ TẤT CẢ VIDEO ===")
            
            # BƯỚC MỚI: Check video status trước khi xử lý
            logger.info("🔍 Bước 1: Kiểm tra trạng thái video...")
            
            if self.video_checker is None:
                logger.warning("⚠️ VideoStatusChecker không khả dụng, bỏ qua kiểm tra trạng thái")
                # Tạo video_status mặc định để tiếp tục xử lý
                video_status = {
                    'videos_to_process': [{'name': 'video1.mp4', 'id': 'default_id'}],
                    'videos_skipped': [],
                    'total_drive_videos': 1,
                    'total_sheet_videos': 0,
                    'check_timestamp': '2025-08-13T10:00:00'
                }
            else:
                try:
                    video_status = self.video_checker.check_video_status(input_folder_id)
                    
                    # Hiển thị summary của video checker
                    try:
                        summary = self.video_checker.get_check_summary(video_status)
                        logger.info(summary)
                    except Exception as e:
                        logger.warning(f"⚠️ Không thể hiển thị summary: {str(e)}")
                except Exception as e:
                    logger.error(f"❌ Lỗi kiểm tra trạng thái video: {str(e)}")
                    # Tạo video_status mặc định để tiếp tục xử lý
                    video_status = {
                        'videos_to_process': [{'name': 'video1.mp4', 'id': 'default_id'}],
                        'videos_skipped': [],
                        'total_drive_videos': 1,
                        'total_sheet_videos': 0,
                        'check_timestamp': '2025-08-13T10:00:00'
                    }
            
            if not video_status['videos_to_process']:
                logger.info("🎉 Tất cả video đã được xử lý! Không có gì để làm.")
                return []
            
            # Chỉ xử lý video mới
            videos_to_process = video_status['videos_to_process']
            logger.info(f" Bắt đầu xử lý {len(videos_to_process)} video mới...")
            
            # Hiển thị danh sách video sẽ xử lý
            logger.info("📋 DANH SÁCH VIDEO SẼ XỬ LÝ:")
            for i, video in enumerate(videos_to_process, 1):
                logger.info(f"  {i}. {video['name']}")
            
            # Bước 2: Xử lý từng video
            results = []
            total_videos = len(videos_to_process)
            
            for i, video_info in enumerate(videos_to_process, 1):
                video_name = video_info['name']
                file_id = video_info['id']
                
                logger.info(f"\n🎬 === XỬ LÝ VIDEO {i}/{total_videos}: {video_name} ===")
                
                try:
                    # Tải video từ Google Drive
                    logger.info("📥 Tải video từ Google Drive...")
                    video_path = self.download_video(file_id, video_name)
                    
                    # Tách voice từ video
                    logger.info("🎤 Tách voice từ video...")
                    voice_path = self.extract_voice_only(video_path, video_name)
                    
                    # Upload voice only
                    logger.info("☁️ Upload voice only...")
                    voice_file_id = self.upload_to_drive(voice_path, voice_folder_id)
                    
                    # Chuyển đổi voice thành text
                    logger.info("📝 Chuyển đổi voice thành text...")
                    text_path, detected_language, is_chinese = self.extract_text_with_language_detection(voice_path, video_name)
                    
                    # Dịch tiếng Trung sang tiếng Việt nếu cần
                    if is_chinese:
                        logger.info("🌐 Dịch tiếng Trung sang tiếng Việt...")
                        translated_text_path = self.translate_chinese_to_vietnamese(text_path, video_name)
                        text_path = translated_text_path # Cập nhật đường dẫn file text gốc
                    
                    # Upload text gốc
                    logger.info("📄 Upload text gốc...")
                    text_file_id = self.upload_to_drive(text_path, text_original_folder_id)
                    
                    # Viết lại text
                    logger.info("✍️ Viết lại text...")
                    rewritten_text_path = self.rewrite_text(text_path, video_name)
                    
                    # Upload text đã viết lại
                    logger.info("📄 Upload text đã viết lại...")
                    rewritten_text_file_id = self.upload_to_drive(rewritten_text_path, text_rewritten_folder_id)
                    
                    # Tạo nội dung chính có timeline (cho cột Text cải tiến)
                    logger.info("📝 Tạo nội dung chính có timeline...")
                    main_content_path = self.create_main_content_only(rewritten_text_path, video_name)
                    
                    # Tạo text không có timeline (cho cột Text no timeline)
                    logger.info("📄 Tạo text không có timeline...")
                    text_no_timeline_path = self.create_text_without_timeline(rewritten_text_path, video_name)
                    
                    # Tạo gợi ý tiêu đề, captions, CTA (cho cột Gợi ý tiêu đề)
                    logger.info("💡 Tạo gợi ý tiêu đề, captions, CTA...")
                    suggestions_path = self.create_suggestions_content(rewritten_text_path, video_name)
                    
                    # Chuyển đổi text thành speech - ĐÃ COMMENT
                    # logger.info("🎤 Chuyển đổi text thành speech...")
                    # tts_audio_path = self.text_to_speech(rewritten_text_path, video_name)
                    
                    # Upload audio TTS - ĐÃ COMMENT
                    # logger.info("☁️ Upload audio TTS...")
                    # tts_file_id = self.upload_to_drive(tts_audio_path, text_to_speech_folder_id)
                    
                    # Thêm kết quả thành công
                    results.append({
                        'status': 'success',
                        'video_name': video_name,
                        'video_file_id': file_id,  # Thêm ID của file video MP4
                        'voice_file_id': voice_file_id,
                        'text_file_id': text_file_id,
                        'rewritten_text_file_id': rewritten_text_file_id,
                        # 'tts_file_id': tts_file_id,  # ĐÃ COMMENT
                        'voice_path': voice_path,
                        'text_path': text_path,
                        'rewritten_text_path': rewritten_text_path,
                        'main_content_path': main_content_path,
                        'text_no_timeline_path': text_no_timeline_path,
                        'suggestions_path': suggestions_path,
                        # 'tts_audio_path': tts_audio_path  # ĐÃ COMMENT
                    })
                    
                    logger.info(f"✅ Hoàn thành video {i}/{total_videos}: {video_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Lỗi xử lý video {video_name}: {str(e)}")
                    results.append({
                        'status': 'error',
                        'video_name': video_name,
                        'error': str(e)
                    })
            
            logger.info(f"✅ === HOÀN THÀNH XỬ LÝ TẤT CẢ VIDEO ===")
            logger.info(f"📊 Tổng số video: {total_videos}")
            logger.info(f"✅ Thành công: {len([r for r in results if r['status'] == 'success'])}")
            logger.info(f"❌ Thất bại: {len([r for r in results if r['status'] == 'error'])}")
            
            # Bước cuối: Cập nhật Google Sheets
            if results:
                logger.info("📊 Bắt đầu cập nhật Google Sheets...")
                sheets_success = self.update_sheets_with_results(results)
                if sheets_success:
                    logger.info("✅ Cập nhật Google Sheets hoàn tất!")
                else:
                    logger.warning("⚠️ Cập nhật Google Sheets thất bại")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong quá trình xử lý tất cả video: {str(e)}")
            return []
    
    def get_next_empty_row(self) -> int:
        """
        Lấy số dòng trống tiếp theo trong Google Sheets
        
        Returns:
            Số dòng trống tiếp theo (bắt đầu từ 1)
        """
        try:
            # Lấy tất cả dữ liệu trong sheet sử dụng tên sheet
            # Thử với tên sheet khác nếu lỗi
            range_name = f'{self.sheet_name}!A:A'
            
            try:
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()
            except Exception as e:
                logger.warning(f"⚠️ Lỗi với tên sheet '{self.sheet_name}', thử với tên khác: {str(e)}")
                # Thử với tên sheet khác
                alternative_names = ['mp3 to text', 'Mp3 to text', 'MP3 to text', 'Sheet1']
                for alt_name in alternative_names:
                    try:
                        range_name = f'{alt_name}!A:A'
                        result = self.sheets_service.spreadsheets().values().get(
                            spreadsheetId=self.spreadsheet_id,
                            range=range_name
                        ).execute()
                        logger.info(f"✅ Thành công với tên sheet: {alt_name}")
                        break
                    except Exception as e2:
                        logger.warning(f"⚠️ Lỗi với tên sheet '{alt_name}': {str(e2)}")
                        continue
                else:
                    # Nếu tất cả đều lỗi, raise exception
                    raise e
            
            values = result.get('values', [])
            
            # Tìm dòng trống đầu tiên (bỏ qua header)
            for i, row in enumerate(values, 1):
                if not row or all(cell.strip() == '' for cell in row):
                    logger.info(f"✅ Dòng trống tiếp theo: {i}")
                    return i
            
            # Nếu không có dòng trống, trả về dòng tiếp theo
            next_row = len(values) + 1
            logger.info(f"✅ Dòng trống tiếp theo: {next_row}")
            return next_row
            
        except Exception as e:
            logger.error(f"❌ Lỗi lấy dòng trống: {str(e)}")
            return 2  # Mặc định bắt đầu từ dòng 2 (sau header)
    
    def read_text_file_content(self, file_path: str) -> str:
        """
        Đọc nội dung file text
        
        Args:
            file_path: Đường dẫn đến file text
            
        Returns:
            Nội dung file text
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                return content
            else:
                return "File không tồn tại"
        except Exception as e:
            logger.error(f"❌ Lỗi đọc file text: {str(e)}")
            return f"Lỗi đọc file: {str(e)}"
    
    def update_sheets_with_results(self, results: List[Dict]) -> bool:
        """
        Cập nhật Google Sheets với kết quả xử lý
        
        Args:
            results: Danh sách kết quả xử lý video
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("📊 Bắt đầu cập nhật Google Sheets...")
            
            # Chuẩn bị dữ liệu để cập nhật
            update_data = []
            
            for result in results:
                if result['status'] == 'success':
                    # Lấy thông tin file
                    video_name = result['video_name']
                    video_file_id = result['video_file_id']  # Thêm ID của file video MP4
                    voice_file_id = result['voice_file_id']
                    text_file_id = result['text_file_id']
                    rewritten_text_file_id = result['rewritten_text_file_id']
                    # tts_file_id = result.get('tts_file_id', '')  # ĐÃ COMMENT
                    
                    # Tạo link Google Drive
                    video_link = f"https://drive.google.com/file/d/{video_file_id}/view"  # Link MP4
                    voice_link = f"https://drive.google.com/file/d/{voice_file_id}/view"
                    text_link = f"https://drive.google.com/file/d/{text_file_id}/view"
                    rewritten_link = f"https://drive.google.com/file/d/{rewritten_text_file_id}/view"
                    # tts_link = f"https://drive.google.com/file/d/{tts_file_id}/view" if tts_file_id else ""  # ĐÃ COMMENT
                    
                    # Đọc nội dung text
                    original_text = self.read_text_file_content(result['text_path'])
                    
                    # Đọc nội dung text cải tiến (chỉ nội dung chính có timeline)
                    rewritten_text = ""
                    if 'main_content_path' in result:
                        rewritten_text = self.read_text_file_content(result['main_content_path'])
                    else:
                        # Fallback cho format cũ
                        rewritten_text = self.read_text_file_content(result['rewritten_text_path'])
                    
                    # Lấy tên video từ file MP4 (loại bỏ phần mở rộng)
                    video_name_clean = os.path.splitext(video_name)[0]
                    
                    # Đọc nội dung text không timeline
                    text_no_timeline = ""
                    if 'text_no_timeline_path' in result:
                        text_no_timeline = self.read_text_file_content(result['text_no_timeline_path'])
                    
                    # Đọc nội dung gợi ý tiêu đề
                    suggestions_content = ""
                    if 'suggestions_path' in result:
                        suggestions_content = self.read_text_file_content(result['suggestions_path'])
                    
                    # Thêm dữ liệu vào danh sách cập nhật
                    update_data.append([
                        video_link,           # Link mp4 (cột A)
                        video_name_clean,     # Tên Video (từ file MP4) (cột B)
                        voice_link,           # Link MP3 (cột C)
                        text_link,            # Link text gốc (cột D)
                        original_text,        # Text gốc MP3 (cột E)
                        rewritten_link,       # Link text cải tiến (cột F)
                        rewritten_text,       # Text cải tiến (cột G)
                        text_no_timeline,     # Text no timeline (chỉ nội dung chính) (cột H)
                        suggestions_content   # Gợi ý tiêu đề (tiêu đề + captions + CTA) (cột I)
                        # tts_link              # Link text to speech - ĐÃ COMMENT
                    ])
                    
                    logger.info(f"📝 Đã chuẩn bị dữ liệu cho video: {video_name}")
            
            if not update_data:
                logger.warning("⚠️ Không có dữ liệu để cập nhật")
                return False
            
            # Lấy dòng trống tiếp theo
            next_row = self.get_next_empty_row()
            range_name = f'{self.sheet_name}!A{next_row}:I{next_row + len(update_data) - 1}'  # A-I: Link mp4, Tên Video, Link MP3, Link text gốc, Text gốc, Link text cải tiến, Text cải tiến, Text no timeline, Gợi ý tiêu đề
            
            # Cập nhật Google Sheets
            body = {
                'values': update_data
            }
            
            try:
                result = self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            except Exception as e:
                logger.warning(f"⚠️ Lỗi update với tên sheet '{self.sheet_name}', thử với tên khác: {str(e)}")
                # Thử với tên sheet khác
                alternative_names = ['mp3 to text', 'Mp3 to text', 'MP3 to text', 'Sheet1']
                for alt_name in alternative_names:
                    try:
                        range_name = f'{alt_name}!A{next_row}:I{next_row + len(update_data) - 1}'
                        result = self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=self.spreadsheet_id,
                            range=range_name,
                            valueInputOption='RAW',
                            body=body
                        ).execute()
                        logger.info(f"✅ Update thành công với tên sheet: {alt_name}")
                        break
                    except Exception as e2:
                        logger.warning(f"⚠️ Lỗi update với tên sheet '{alt_name}': {str(e2)}")
                        continue
                else:
                    # Nếu tất cả đều lỗi, raise exception
                    raise e
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"✅ Cập nhật Google Sheets thành công!")
            logger.info(f"📊 Đã cập nhật {updated_cells} ô")
            logger.info(f"📄 Dòng bắt đầu: {next_row}")
            logger.info(f"📄 Dòng kết thúc: {next_row + len(update_data) - 1}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi cập nhật Google Sheets: {str(e)}")
            return False
    
    def cleanup(self):
        """
        Dọn dẹp file tạm sau khi xử lý xong
        
        Xóa thư mục tạm và tất cả file trong đó để tiết kiệm dung lượng
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("✅ Đã dọn dẹp file tạm")
            except Exception as e:
                logger.warning(f"⚠️ Không thể dọn dẹp file tạm: {str(e)}")


def main():
    """
    Hàm chính - Entry point của ứng dụng
    
    Chức năng:
    - Cấu hình các folder IDs
    - Khởi tạo processor
    - Chạy toàn bộ workflow với hỗ trợ tiếng Trung (TTS đã comment)
    - Hiển thị kết quả
    """
    print("🚀 === All-in-One: MP4 -> Voice Only -> Text (VI/CN) -> Translate -> Rewrite -> Drive ===")
    print("=" * 80)

    # CẤU HÌNH TẠI ĐÂY - Thay đổi các giá trị bên dưới
    # ===================================================
    
    # ID của folder chứa video (input) - Thay đổi nếu cần
    INPUT_FOLDER_ID = "17_ncdjiRI2K4c4OA-sp3Uyi4bskP0CIu"
    # INPUT_FOLDER_ID = "1scX8WQAPMw3zEojFFMlKZd3PmQ2sBsaF"

    
    # ID của folder để upload voice only - Thay đổi nếu cần
    VOICE_ONLY_FOLDER_ID = "1FUP92ha2uaxPmB3a680eOd7TAqH1SqGT"  # Sử dụng folder MP3 cũ cho voice
    
    # ID của folder để upload text gốc - Thay đổi nếu cần
    TEXT_ORIGINAL_FOLDER_ID = "1ZswATID5nLDRjap6yvDJYaa435Nrp8eo"
    
    # ID của folder để upload text đã viết lại - Thay đổi nếu cần
    TEXT_REWRITTEN_FOLDER_ID = "18XIdyGd-9ahPLHElJBBwXeATgcFanoQR"
    
    # ID của folder để upload text to speech - Thay đổi nếu cần - ĐÃ COMMENT
    # TEXT_TO_SPEECH_FOLDER_ID = "1UZkeCdbUk4CGQjwsnYKQ0dNm6g-2bt70"
    
    # Tên video cần xử lý - Thay đổi nếu cần
    VIDEO_NAME = "video1.mp4"
    
    # ===================================================

    try:
        # Khởi tạo processor
        print("🔧 Đang khởi tạo processor...")
        processor = AllInOneProcessor()

        # Hiển thị thông tin cấu hình
        print(f"\n📋 THÔNG TIN CẤU HÌNH:")
        print(f"🎬 Video: {VIDEO_NAME}")
        print(f"📁 Input folder: {INPUT_FOLDER_ID}")
        print(f"🎤 Voice only folder: {VOICE_ONLY_FOLDER_ID}")
        print(f"📄 Text original folder: {TEXT_ORIGINAL_FOLDER_ID}")
        print(f"✍️ Text rewritten folder: {TEXT_REWRITTEN_FOLDER_ID}")
        # print(f"🎤 Text to speech folder: {TEXT_TO_SPEECH_FOLDER_ID}")  # ĐÃ COMMENT
        print(f"🌐 Hỗ trợ ngôn ngữ: Tiếng Việt và Tiếng Trung")

        # Xử lý tất cả video
        print(f"\n🚀 BẮT ĐẦU XỬ LÝ TẤT CẢ VIDEO...")
        results = processor.process_all_videos(
            INPUT_FOLDER_ID, 
            VOICE_ONLY_FOLDER_ID,
            TEXT_ORIGINAL_FOLDER_ID,
            TEXT_REWRITTEN_FOLDER_ID
            # TEXT_TO_SPEECH_FOLDER_ID  # ĐÃ COMMENT
        )

        # Hiển thị kết quả
        print(f"\n" + "=" * 80)
        if results:
            success_count = len([r for r in results if r['status'] == 'success'])
            error_count = len([r for r in results if r['status'] == 'error'])
            
            print(f"🎉 === KẾT QUẢ XỬ LÝ ===")
            print(f"📊 Tổng số video: {len(results)}")
            print(f"✅ Thành công: {success_count}")
            print(f"❌ Thất bại: {error_count}")
            print(f"📊 Google Sheets đã được cập nhật tự động")
            
            if success_count > 0:
                print(f"\n📋 CHI TIẾT VIDEO THÀNH CÔNG:")
                for result in results:
                    if result['status'] == 'success':
                        print(f"  🎬 {result['video_name']}")
                        print(f"    🎤 Voice: {result['voice_file_id']}")
                        print(f"    📄 Text: {result['text_file_id']}")
                        print(f"    ✍️ Rewritten: {result['rewritten_text_file_id']}")
                        # print(f"    🎤 TTS: {result.get('tts_file_id', 'N/A')}")  # ĐÃ COMMENT
            
            if error_count > 0:
                print(f"\n❌ CHI TIẾT VIDEO THẤT BẠI:")
                for result in results:
                    if result['status'] == 'error':
                        print(f"  🎬 {result['video_name']}: {result.get('error', 'Unknown error')}")
            
            print(f"\n🔗 LINKS:")
            print(f"🎤 Voice Only Folder: https://drive.google.com/drive/folders/{VOICE_ONLY_FOLDER_ID}")
            print(f"📄 Text Original Folder: https://drive.google.com/drive/folders/{TEXT_ORIGINAL_FOLDER_ID}")
            print(f"✍️ Text Rewritten Folder: https://drive.google.com/drive/folders/{TEXT_REWRITTEN_FOLDER_ID}")
            # print(f"🎤 Text to Speech Folder: https://drive.google.com/drive/folders/{TEXT_TO_SPEECH_FOLDER_ID}")  # ĐÃ COMMENT
        else:
            print(f"❌ Không có video nào được xử lý")

    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        print("\n🔧 KIỂM TRA:")
        print("1. File client_secret đã có chưa?")
        print("2. FFmpeg đã cài đặt chưa?")
        print("3. Google Drive API đã bật chưa?")
        print("4. OAuth credentials có quyền truy cập folder không?")
        print("5. Deepgram API key có hợp lệ không?")
        print("6. Gemini API key có hợp lệ không?")
    finally:
        # Dọn dẹp
        if 'processor' in locals():
            processor.cleanup()


if __name__ == "__main__":
    main() 
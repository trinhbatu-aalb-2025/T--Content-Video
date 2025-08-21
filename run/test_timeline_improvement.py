#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Timeline Improvement
Kiểm tra cải thiện timeline extraction với các API đã có

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import logging
import sys
import os

# Thêm thư mục cha vào path để import all_in_one
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from all_in_one import AllInOneProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_timeline_improvement.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_timeline_improvement():
    """
    Test cải thiện timeline extraction
    """
    try:
        logger.info("🧪 Bắt đầu test cải thiện timeline extraction...")
        
        # Khởi tạo AllInOneProcessor
        logger.info("🔧 Đang khởi tạo AllInOneProcessor...")
        processor = AllInOneProcessor()
        
        logger.info("✅ AllInOneProcessor đã được khởi tạo thành công")
        
        # Test với một video có sẵn
        logger.info("🔍 Testing timeline extraction với video có sẵn...")
        
        # Sử dụng folder ID từ all_in_one.py
        input_folder_id = "1PkAFvo82TWaMK56qwdTJdfBdNkxTeNkL"
        
        # Lấy danh sách video
        videos = processor.get_all_videos_in_folder(input_folder_id)
        
        if not videos:
            logger.error("❌ Không tìm thấy video nào trong folder")
            return
        
        # Test với video đầu tiên
        test_video = videos[0]
        logger.info(f"🎬 Testing với video: {test_video['name']}")
        
        # Download video
        video_path = processor.download_video(test_video['id'], test_video['name'])
        logger.info(f"📥 Đã download video: {video_path}")
        
        # Extract voice only
        voice_path = processor.extract_voice_only(video_path, test_video['name'])
        logger.info(f"🎵 Đã extract voice: {voice_path}")
        
        # Test timeline extraction với tiếng Việt
        logger.info("🇻🇳 Testing timeline extraction với tiếng Việt...")
        transcript_vi, language_vi = processor._try_transcription(voice_path, "vi")
        
        logger.info("=" * 60)
        logger.info("📊 KẾT QUẢ TIMELINE TIẾNG VIỆT")
        logger.info("=" * 60)
        logger.info(f"🌐 Ngôn ngữ: {language_vi}")
        logger.info(f"📝 Độ dài transcript: {len(transcript_vi)} ký tự")
        logger.info(f"📄 Transcript: {transcript_vi[:500]}...")
        
        # Test timeline extraction với tiếng Trung
        logger.info("🇨🇳 Testing timeline extraction với tiếng Trung...")
        transcript_zh, language_zh = processor._try_transcription(voice_path, "zh")
        
        logger.info("=" * 60)
        logger.info("📊 KẾT QUẢ TIMELINE TIẾNG TRUNG")
        logger.info("=" * 60)
        logger.info(f"🌐 Ngôn ngữ: {language_zh}")
        logger.info(f"📝 Độ dài transcript: {len(transcript_zh)} ký tự")
        logger.info(f"📄 Transcript: {transcript_zh[:500]}...")
        
        # Phân tích kết quả
        logger.info("=" * 60)
        logger.info("🎯 PHÂN TÍCH KẾT QUẢ")
        logger.info("=" * 60)
        
        # Kiểm tra có timeline không
        has_timeline_vi = "(Giây" in transcript_vi
        has_timeline_zh = "(Giây" in transcript_zh
        
        logger.info(f"🇻🇳 Tiếng Việt có timeline: {has_timeline_vi}")
        logger.info(f"🇨🇳 Tiếng Trung có timeline: {has_timeline_zh}")
        
        # Kiểm tra có manual timeline không
        has_manual_timeline_vi = "THỦ CÔNG" in transcript_vi
        has_manual_timeline_zh = "THỦ CÔNG" in transcript_zh
        
        logger.info(f"🇻🇳 Tiếng Việt có manual timeline: {has_manual_timeline_vi}")
        logger.info(f"🇨🇳 Tiếng Trung có manual timeline: {has_manual_timeline_zh}")
        
        # Kết luận
        logger.info("=" * 60)
        logger.info("🎯 KẾT LUẬN")
        logger.info("=" * 60)
        
        if has_timeline_vi or has_timeline_zh:
            logger.info("✅ Timeline extraction hoạt động tốt!")
            if has_manual_timeline_vi or has_manual_timeline_zh:
                logger.info("✅ Manual timeline fallback hoạt động!")
            else:
                logger.info("✅ Deepgram timeline hoạt động trực tiếp!")
        else:
            logger.warning("⚠️ Timeline extraction chưa hoạt động tốt")
        
        # Cleanup
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"🧹 Đã xóa video test: {os.path.basename(video_path)}")
            if os.path.exists(voice_path):
                os.remove(voice_path)
                logger.info(f"🧹 Đã xóa voice test: {os.path.basename(voice_path)}")
        except Exception as e:
            logger.warning(f"⚠️ Không thể cleanup files: {str(e)}")
        
        logger.info("✅ Test timeline improvement hoàn tất!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi test timeline improvement: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_timeline_improvement()

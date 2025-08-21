#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FFmpeg Fix
Kiểm tra sửa lỗi FFmpeg không tìm thấy

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_ffmpeg_fix.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_ffmpeg_path():
    """
    Test tìm đường dẫn FFmpeg
    """
    try:
        logger.info("🧪 Bắt đầu test FFmpeg path...")
        
        # Test 1: Tìm FFmpeg trong thư mục tools
        tools_ffmpeg = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'ffmpeg.exe')
        logger.info(f"🔍 FFmpeg trong tools: {tools_ffmpeg}")
        logger.info(f"📁 Exists: {os.path.exists(tools_ffmpeg)}")
        
        # Test 2: Tìm FFmpeg trong PATH
        import shutil
        path_ffmpeg = shutil.which('ffmpeg')
        logger.info(f"🔍 FFmpeg trong PATH: {path_ffmpeg}")
        
        # Test 3: Test chạy FFmpeg
        if os.path.exists(tools_ffmpeg):
            logger.info("✅ FFmpeg trong tools tồn tại")
            
            # Test chạy FFmpeg
            import subprocess
            try:
                result = subprocess.run([tools_ffmpeg, '-version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info("✅ FFmpeg chạy thành công")
                    logger.info(f"📄 Version: {result.stdout[:100]}...")
                else:
                    logger.error(f"❌ FFmpeg lỗi: {result.stderr}")
            except Exception as e:
                logger.error(f"❌ Lỗi chạy FFmpeg: {str(e)}")
        else:
            logger.warning("⚠️ FFmpeg trong tools không tồn tại")
        
        # Test 4: Test audio preprocessing function
        logger.info("🔧 Testing audio preprocessing function...")
        
        # Import function từ all_in_one
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from all_in_one import AllInOneProcessor
        
        processor = AllInOneProcessor()
        
        # Tạo file audio test đơn giản
        test_audio_path = os.path.join(os.path.dirname(__file__), 'test_audio.mp3')
        
        # Tạo file audio test (1 giây silence)
        try:
            cmd = [
                tools_ffmpeg, '-y',
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-t', '1',
                test_audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("✅ Tạo file audio test thành công")
                
                # Test preprocessing
                processed_path = processor._preprocess_audio_for_timeline(test_audio_path)
                logger.info(f"✅ Audio preprocessing: {processed_path}")
                
                # Cleanup
                if os.path.exists(test_audio_path):
                    os.remove(test_audio_path)
                    logger.info("🧹 Đã xóa file audio test")
                if os.path.exists(processed_path) and processed_path != test_audio_path:
                    os.remove(processed_path)
                    logger.info("🧹 Đã xóa file audio đã xử lý")
                    
            else:
                logger.error(f"❌ Lỗi tạo file audio test: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Lỗi test audio preprocessing: {str(e)}")
        
        logger.info("✅ Test FFmpeg fix hoàn tất!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi test FFmpeg fix: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_ffmpeg_path()

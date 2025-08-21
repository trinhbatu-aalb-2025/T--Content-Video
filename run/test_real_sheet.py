#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Real Sheet
Kiểm tra với Google Sheets API thật để xem logic mapping có đúng không

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
        logging.FileHandler('test_real_sheet.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_real_sheet():
    """
    Test với Google Sheets API thật
    """
    try:
        logger.info("🧪 Bắt đầu test với Google Sheets API thật...")
        
        # Khởi tạo AllInOneProcessor (sẽ có VideoStatusChecker)
        logger.info("🔧 Đang khởi tạo AllInOneProcessor...")
        processor = AllInOneProcessor()
        
        logger.info("✅ AllInOneProcessor đã được khởi tạo thành công")
        
        # Test VideoStatusChecker với folder thật
        logger.info("🔍 Testing VideoStatusChecker với dữ liệu thật...")
        
        # Sử dụng folder ID từ all_in_one.py
        input_folder_id = "1PkAFvo82TWaMK56qwdTJdfBdNkxTeNkL"
        
        # Chạy check video status
        video_status = processor.video_checker.check_video_status(input_folder_id)
        
        # Hiển thị kết quả
        logger.info("=" * 60)
        logger.info("📊 KẾT QUẢ TEST THỰC TẾ")
        logger.info("=" * 60)
        
        summary = processor.video_checker.get_check_summary(video_status)
        logger.info(summary)
        
        # Hiển thị chi tiết
        logger.info("=" * 60)
        logger.info("📋 CHI TIẾT VIDEO CẦN XỬ LÝ:")
        if video_status['videos_to_process']:
            for i, video in enumerate(video_status['videos_to_process'], 1):
                logger.info(f"  {i}. {video['name']} (ID: {video['id']})")
        else:
            logger.info("  Không có video nào cần xử lý!")
        
        logger.info("=" * 60)
        logger.info("⏭️ CHI TIẾT VIDEO BỎ QUA:")
        if video_status['videos_skipped']:
            for i, video in enumerate(video_status['videos_skipped'], 1):
                logger.info(f"  {i}. {video['name']} (ID: {video['id']})")
        else:
            logger.info("  Không có video nào bị bỏ qua!")
        
        logger.info("=" * 60)
        logger.info("✅ Test với Google Sheets API thật hoàn tất!")
        
        # Kết luận
        total_drive = video_status.get('total_drive_videos', 0)
        total_sheet = video_status.get('total_sheet_videos', 0)
        to_process = len(video_status.get('videos_to_process', []))
        skipped = len(video_status.get('videos_skipped', []))
        
        logger.info("🎯 KẾT LUẬN:")
        logger.info(f"  📁 Tổng video trên Drive: {total_drive}")
        logger.info(f"  📊 Tổng video trong Sheet: {total_sheet}")
        logger.info(f"  ✅ Cần xử lý: {to_process}")
        logger.info(f"  ⏭️ Bỏ qua: {skipped}")
        
        if to_process == 0:
            logger.info("🎉 Tất cả video đã được xử lý! Logic mapping hoạt động đúng!")
        elif to_process < total_drive:
            logger.info("✅ Logic mapping hoạt động đúng! Chỉ xử lý video mới.")
        else:
            logger.warning("⚠️ Có thể có vấn đề với logic mapping!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi test với Google Sheets API thật: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_real_sheet()

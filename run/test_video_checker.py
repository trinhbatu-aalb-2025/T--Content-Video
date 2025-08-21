#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Video Status Checker
Kiểm tra chức năng của VideoStatusChecker

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import logging
from video_checker import VideoStatusChecker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_video_checker.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_video_checker():
    """
    Test function cho VideoStatusChecker
    """
    try:
        logger.info("🧪 Bắt đầu test VideoStatusChecker...")
        
        # Test data (mock)
        drive_service = None  # Sẽ được inject từ AllInOneProcessor
        sheets_service = None  # Sẽ được inject từ AllInOneProcessor
        spreadsheet_id = '1y4Gmc58DCRmnyO9qNlSBklkvebL5mY9gLlOqcP91Epg'
        sheet_name = 'Mp3 to text'
        
        # Khởi tạo VideoStatusChecker
        checker = VideoStatusChecker(
            drive_service, 
            sheets_service,
            spreadsheet_id,
            sheet_name
        )
        
        logger.info("✅ VideoStatusChecker đã được khởi tạo thành công")
        
        # Test các method
        logger.info("📋 Testing các method...")
        
        # Test get_check_summary với data mock
        mock_video_status = {
            'videos_to_process': [
                {'name': 'video1.mp4', 'id': '123'},
                {'name': 'video2.mp4', 'id': '456'}
            ],
            'videos_skipped': [
                {'name': 'video3.mp4', 'id': '789'}
            ],
            'total_drive_videos': 3,
            'total_sheet_videos': 1,
            'check_timestamp': '2024-01-01T00:00:00'
        }
        
        summary = checker.get_check_summary(mock_video_status)
        logger.info("📊 Test summary:")
        logger.info(summary)
        
        logger.info("✅ Test VideoStatusChecker hoàn tất!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi test VideoStatusChecker: {str(e)}")


if __name__ == "__main__":
    test_video_checker()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Sheet Mapping
Kiểm tra logic mapping với Sheet thực tế để debug vấn đề

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
        logging.FileHandler('debug_sheet_mapping.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def debug_sheet_mapping():
    """
    Debug function để kiểm tra logic mapping với Sheet thực tế
    """
    try:
        logger.info("🔍 Bắt đầu debug sheet mapping...")
        
        # Test data (mock services)
        drive_service = None
        sheets_service = None
        spreadsheet_id = '1y4Gmc58DCRmnyO9qNlSBklkvebL5mY9gLlOqcP91Epg'
        sheet_name = 'Mp3 to text'
        
        # Khởi tạo VideoStatusChecker
        checker = VideoStatusChecker(
            drive_service, 
            sheets_service,
            spreadsheet_id,
            sheet_name
        )
        
        logger.info("✅ VideoStatusChecker đã được khởi tạo")
        
        # Test logic mapping với data mock
        logger.info("📋 Testing logic mapping...")
        
        # Mock data từ Sheet (dựa trên cấu trúc thực tế)
        mock_sheet_data = [
            # Headers
            ['Tên video', 'Link MP4', 'Text gốc', 'Text cải tiến', 'Text no timeline', 'Gợi ý tiêu đề'],
            # Data rows
            ['video1.mp4', 'https://drive.google.com/file/d/123/view', 'text1', 'rewritten1', 'no_timeline1', 'suggestions1'],
            ['video2.mp4', 'https://drive.google.com/file/d/456/view', 'text2', 'rewritten2', 'no_timeline2', 'suggestions2'],
            ['video3.mp4', 'https://drive.google.com/file/d/789/view', 'text3', 'rewritten3', 'no_timeline3', 'suggestions3'],
            ['', '', '', '', '', ''],  # Empty row
            ['video4.mp4', 'https://drive.google.com/file/d/101/view', 'text4', 'rewritten4', 'no_timeline4', 'suggestions4'],
        ]
        
        # Test logic tìm cột
        logger.info("🔍 Testing column detection logic...")
        headers = mock_sheet_data[0]
        
        name_col_idx = None
        link_col_idx = None
        
        for i, header in enumerate(headers):
            if not header:
                continue
                
            header_lower = header.lower().strip()
            logger.info(f"🔍 Kiểm tra header {i}: '{header}' -> '{header_lower}'")
            
            # Tìm cột tên video
            if any(keyword in header_lower for keyword in [
                'tên', 'name', 'video', 'file', 'filename', 'tên video', 'tên file'
            ]):
                name_col_idx = i
                logger.info(f"✅ Tìm thấy cột tên video: '{header}' (index: {i})")
            
            # Tìm cột link
            elif any(keyword in header_lower for keyword in [
                'link', 'mp4', 'drive', 'url', 'đường dẫn', 'link mp4', 'drive link'
            ]):
                link_col_idx = i
                logger.info(f"✅ Tìm thấy cột link: '{header}' (index: {i})")
        
        logger.info(f"📊 Kết quả tìm kiếm cột:")
        logger.info(f"  - Cột tên video: {name_col_idx} ({headers[name_col_idx] if name_col_idx is not None else 'Không tìm thấy'})")
        logger.info(f"  - Cột link: {link_col_idx} ({headers[link_col_idx] if link_col_idx is not None else 'Không tìm thấy'})")
        
        # Test logic đọc dữ liệu
        logger.info("📋 Testing data reading logic...")
        sheet_videos = []
        
        for row_idx, row in enumerate(mock_sheet_data[1:], 1):
            if not row:  # Bỏ qua dòng trống
                continue
                
            video_info = {
                'row': row_idx,
                'name': '',
                'link': ''
            }
            
            # Lấy tên video
            if name_col_idx is not None and len(row) > name_col_idx:
                video_info['name'] = row[name_col_idx].strip() if row[name_col_idx] else ''
            
            # Lấy link
            if link_col_idx is not None and len(row) > link_col_idx:
                video_info['link'] = row[link_col_idx].strip() if row[link_col_idx] else ''
            
            # Chỉ thêm nếu có tên video
            if video_info['name']:
                sheet_videos.append(video_info)
                logger.info(f"📊 Thêm video từ Sheet: '{video_info['name']}' (row: {row_idx})")
            elif video_info['link']:
                # Nếu không có tên nhưng có link, thử extract tên từ link
                extracted_name = checker._extract_name_from_link(video_info['link'])
                if extracted_name:
                    video_info['name'] = extracted_name
                    sheet_videos.append(video_info)
                    logger.info(f"📊 Thêm video từ link: '{extracted_name}' (row: {row_idx})")
        
        logger.info(f"📊 Tìm thấy {len(sheet_videos)} video trong Sheet")
        
        # Test logic so sánh
        logger.info("🔍 Testing comparison logic...")
        mock_drive_videos = [
            {'name': 'video1.mp4', 'id': '123'},
            {'name': 'video2.mp4', 'id': '456'},
            {'name': 'video5.mp4', 'id': '999'},  # Video mới
            {'name': 'video6.mp4', 'id': '888'},  # Video mới
        ]
        
        # Test logic so sánh
        sheet_video_names = set()
        sheet_video_names_without_ext = set()
        
        for sheet_video in sheet_videos:
            if sheet_video.get('name'):
                normalized_name = sheet_video['name'].lower().strip()
                sheet_video_names.add(normalized_name)
                
                name_without_ext = checker._remove_extension(normalized_name)
                if name_without_ext:
                    sheet_video_names_without_ext.add(name_without_ext)
                
                logger.info(f"📊 Video trong Sheet: '{sheet_video['name']}' -> '{normalized_name}' (without ext: '{name_without_ext}')")
        
        logger.info(f"📊 Tổng số tên video trong Sheet: {len(sheet_video_names)}")
        logger.info(f"📊 Tổng số tên video (không extension): {len(sheet_video_names_without_ext)}")
        
        # So sánh từng video trên Drive
        videos_to_process = []
        videos_skipped = []
        
        for drive_video in mock_drive_videos:
            drive_name = drive_video.get('name', '').lower().strip()
            drive_name_without_ext = checker._remove_extension(drive_name)
            
            logger.info(f"🔍 Kiểm tra: '{drive_video['name']}' -> '{drive_name}' (without ext: '{drive_name_without_ext}')")
            
            exact_match = drive_name in sheet_video_names
            name_match = drive_name_without_ext in sheet_video_names_without_ext
            
            if exact_match or name_match:
                videos_skipped.append(drive_video)
                match_type = "exact" if exact_match else "name_only"
                logger.info(f"⏭️ Bỏ qua: '{drive_video['name']}' (đã có trong Sheet - {match_type} match)")
            else:
                videos_to_process.append(drive_video)
                logger.info(f"✅ Cần xử lý: '{drive_video['name']}'")
        
        logger.info(f"📊 Kết quả so sánh: {len(videos_to_process)} cần xử lý, {len(videos_skipped)} bỏ qua")
        
        logger.info("✅ Debug sheet mapping hoàn tất!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi debug sheet mapping: {str(e)}")


if __name__ == "__main__":
    debug_sheet_mapping()

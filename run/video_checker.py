#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Status Checker
Kiểm tra trạng thái video giữa Google Drive và Google Sheets
Tránh xử lý trùng lặp video đã có trong Sheet

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class VideoStatusChecker:
    """
    Class riêng để kiểm tra trạng thái video giữa Drive và Sheet
    Có thể tái sử dụng và dễ customize
    """
    
    def __init__(self, drive_service, sheets_service, spreadsheet_id, sheet_name):
        """
        Khởi tạo VideoStatusChecker
        
        Args:
            drive_service: Google Drive service
            sheets_service: Google Sheets service  
            spreadsheet_id: ID của Google Spreadsheet
            sheet_name: Tên sheet chứa dữ liệu video
        """
        self.drive_service = drive_service
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        
        logger.info("✅ VideoStatusChecker đã được khởi tạo")
    
    def check_video_status(self, input_folder_id: str) -> Dict:
        """
        Main function để check trạng thái video
        
        Args:
            input_folder_id: ID của folder chứa video trên Google Drive
            
        Returns:
            Dict chứa thông tin trạng thái video:
            {
                'videos_to_process': List[Dict],  # Video cần xử lý
                'videos_skipped': List[Dict],     # Video đã có, bỏ qua
                'total_drive_videos': int,        # Tổng số video trên Drive
                'total_sheet_videos': int,        # Tổng số video trong Sheet
                'check_timestamp': str            # Thời gian check
            }
        """
        try:
            logger.info("🔍 Bắt đầu kiểm tra trạng thái video...")
            logger.info(f"📁 Folder ID: {input_folder_id}")
            
            # 1. Lấy video từ Drive
            drive_videos = self.get_drive_videos(input_folder_id)
            logger.info(f"📁 Tìm thấy {len(drive_videos)} video trên Drive")
            
            # 2. Lấy video từ Sheet
            sheet_videos = self.get_sheet_videos()
            logger.info(f"📊 Tìm thấy {len(sheet_videos)} video trong Sheet")
            
            # 3. So sánh và phân loại
            result = self.compare_videos(drive_videos, sheet_videos)
            
            # 4. Thêm thông tin bổ sung
            result.update({
                'total_drive_videos': len(drive_videos),
                'total_sheet_videos': len(sheet_videos),
                'check_timestamp': datetime.now().isoformat()
            })
            
            # 5. Log kết quả chi tiết
            logger.info("=" * 50)
            logger.info("📊 KẾT QUẢ KIỂM TRA VIDEO")
            logger.info("=" * 50)
            logger.info(f"📁 Tổng video trên Drive: {len(drive_videos)}")
            logger.info(f"📊 Tổng video trong Sheet: {len(sheet_videos)}")
            logger.info(f"✅ Cần xử lý: {len(result['videos_to_process'])} video")
            logger.info(f"⏭️ Bỏ qua: {len(result['videos_skipped'])} video")
            logger.info("=" * 50)
            
            # 6. Hiển thị danh sách video cần xử lý
            if result['videos_to_process']:
                logger.info("📋 DANH SÁCH VIDEO CẦN XỬ LÝ:")
                for i, video in enumerate(result['videos_to_process'], 1):
                    logger.info(f"  {i}. {video['name']} (ID: {video['id']})")
            
            # 7. Hiển thị danh sách video bỏ qua
            if result['videos_skipped']:
                logger.info("⏭️ DANH SÁCH VIDEO BỎ QUA (đã có trong Sheet):")
                for i, video in enumerate(result['videos_skipped'], 1):
                    logger.info(f"  {i}. {video['name']} (ID: {video['id']})")
            
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi check video status: {str(e)}")
            raise
    
    def get_drive_videos(self, folder_id: str) -> List[Dict]:
        """
        Lấy tất cả video từ Google Drive folder
        
        Args:
            folder_id: ID của folder trên Google Drive
            
        Returns:
            List chứa thông tin tất cả video
        """
        try:
            logger.info(f"🔍 Đang tìm kiếm video trong folder ID: {folder_id}")
            
            # Tạo query để tìm tất cả file video trong folder
            query = f"'{folder_id}' in parents and (mimeType contains 'video/' or name contains '.mp4' or name contains '.avi' or name contains '.mov' or name contains '.mkv')"
            
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
            logger.error(f"❌ Lỗi lấy video từ Drive: {str(e)}")
            return []
    
    def get_sheet_videos(self) -> List[Dict]:
        """
        Lấy danh sách video đã có trong Google Sheet
        
        Returns:
            List chứa thông tin video từ Sheet
        """
        try:
            logger.info(f"📊 Đang đọc dữ liệu từ Sheet: {self.sheet_name}")
            
            # Đọc tất cả dữ liệu từ Sheet sử dụng tên sheet
            range_name = f'{self.sheet_name}!A:Z'
            
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
                        range_name = f'{alt_name}!A:Z'
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
                logger.warning("⚠️ Không tìm thấy dữ liệu trong Sheet")
                return []
            
            logger.info(f"📊 Tìm thấy {len(values)} dòng dữ liệu trong Sheet")
            
            # Tìm cột chứa tên video hoặc link MP4
            sheet_videos = []
            headers = values[0] if values else []
            
            # Tìm index của các cột quan trọng - CẢI THIỆN LOGIC TÌM KIẾM
            name_col_idx = None
            link_col_idx = None
            
            logger.info(f"📋 Headers: {headers}")
            
            # Logic tìm kiếm cải tiến - tìm chính xác hơn
            for i, header in enumerate(headers):
                if not header:
                    continue
                    
                header_lower = header.lower().strip()
                logger.info(f"🔍 Kiểm tra header {i}: '{header}' -> '{header_lower}'")
                
                # Tìm cột tên video - mở rộng từ khóa tìm kiếm
                if any(keyword in header_lower for keyword in [
                    'tên', 'name', 'video', 'file', 'filename', 'tên video', 'tên file'
                ]):
                    name_col_idx = i
                    logger.info(f"✅ Tìm thấy cột tên video: '{header}' (index: {i})")
                
                # Tìm cột link - mở rộng từ khóa tìm kiếm
                elif any(keyword in header_lower for keyword in [
                    'link', 'mp4', 'drive', 'url', 'đường dẫn', 'link mp4', 'drive link'
                ]):
                    link_col_idx = i
                    logger.info(f"✅ Tìm thấy cột link: '{header}' (index: {i})")
            
            # Fallback: nếu không tìm thấy cột tên, thử tìm cột đầu tiên có dữ liệu
            if name_col_idx is None:
                logger.warning("⚠️ Không tìm thấy cột tên video, thử cột đầu tiên...")
                # Kiểm tra cột đầu tiên có chứa tên file video không
                for row_idx, row in enumerate(values[1:], 1):
                    if row and len(row) > 0 and row[0]:
                        first_col_value = row[0].lower().strip()
                        if any(ext in first_col_value for ext in ['.mp4', '.avi', '.mov', '.mkv']):
                            name_col_idx = 0
                            logger.info(f"✅ Sử dụng cột đầu tiên làm cột tên video (index: 0)")
                            break
            
            logger.info(f"📊 Kết quả tìm kiếm cột:")
            logger.info(f"  - Cột tên video: {name_col_idx} ({headers[name_col_idx] if name_col_idx is not None else 'Không tìm thấy'})")
            logger.info(f"  - Cột link: {link_col_idx} ({headers[link_col_idx] if link_col_idx is not None else 'Không tìm thấy'})")
            
            # Đọc dữ liệu từ các cột
            for row_idx, row in enumerate(values[1:], 1):  # Bỏ qua header
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
                
                # Chỉ thêm nếu có tên video (ưu tiên tên hơn link)
                if video_info['name']:
                    sheet_videos.append(video_info)
                    logger.info(f"📊 Thêm video từ Sheet: '{video_info['name']}' (row: {row_idx})")
                elif video_info['link']:
                    # Nếu không có tên nhưng có link, thử extract tên từ link
                    extracted_name = self._extract_name_from_link(video_info['link'])
                    if extracted_name:
                        video_info['name'] = extracted_name
                        sheet_videos.append(video_info)
                        logger.info(f"📊 Thêm video từ link: '{extracted_name}' (row: {row_idx})")
            
            logger.info(f"📊 Tìm thấy {len(sheet_videos)} video trong Sheet")
            
            # Debug: hiển thị danh sách video tìm thấy
            if sheet_videos:
                logger.info("📋 DANH SÁCH VIDEO TÌM THẤY TRONG SHEET:")
                for i, video in enumerate(sheet_videos, 1):
                    logger.info(f"  {i}. '{video['name']}' (row: {video['row']})")
            
            return sheet_videos
            
        except Exception as e:
            logger.error(f"❌ Lỗi lấy video từ Sheet: {str(e)}")
            return []
    
    def _extract_name_from_link(self, link: str) -> str:
        """
        Trích xuất tên file từ link Google Drive
        
        Args:
            link: Link Google Drive
            
        Returns:
            Tên file nếu có thể trích xuất được
        """
        try:
            if not link:
                return ""
            
            # Tìm pattern /d/FILE_ID/ trong link
            import re
            patterns = [
                r'/d/([^/]+)/',  # /d/FILE_ID/
                r'id=([^&]+)',   # id=FILE_ID&
                r'/([^/]+\.(?:mp4|avi|mov|mkv))',  # /filename.mp4
            ]
            
            for pattern in patterns:
                match = re.search(pattern, link)
                if match:
                    file_id_or_name = match.group(1)
                    # Nếu là file ID, không thể lấy tên
                    if len(file_id_or_name) > 20:  # File ID thường dài
                        return ""
                    # Nếu có extension, có thể là tên file
                    if any(ext in file_id_or_name.lower() for ext in ['.mp4', '.avi', '.mov', '.mkv']):
                        return file_id_or_name
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract name from link: {str(e)}")
            return ""
    
    def compare_videos(self, drive_videos: List[Dict], sheet_videos: List[Dict]) -> Dict:
        """
        So sánh video giữa Drive và Sheet
        
        Args:
            drive_videos: Danh sách video từ Drive
            sheet_videos: Danh sách video từ Sheet
            
        Returns:
            Dict chứa kết quả so sánh
        """
        try:
            videos_to_process = []
            videos_skipped = []
            
            # Tạo set tên video từ Sheet để so sánh nhanh - CẢI THIỆN LOGIC
            sheet_video_names = set()
            sheet_video_names_without_ext = set()  # Tên không có extension
            
            for sheet_video in sheet_videos:
                if sheet_video.get('name'):
                    # Chuẩn hóa tên file (lowercase, strip whitespace)
                    normalized_name = sheet_video['name'].lower().strip()
                    sheet_video_names.add(normalized_name)
                    
                    # Thêm tên không có extension để so sánh linh hoạt hơn
                    name_without_ext = self._remove_extension(normalized_name)
                    if name_without_ext:
                        sheet_video_names_without_ext.add(name_without_ext)
                    
                    logger.info(f"📊 Video trong Sheet: '{sheet_video['name']}' -> '{normalized_name}' (without ext: '{name_without_ext}')")
            
            logger.info(f"📊 Tổng số tên video trong Sheet: {len(sheet_video_names)}")
            logger.info(f"📊 Tổng số tên video (không extension): {len(sheet_video_names_without_ext)}")
            
            # So sánh từng video trên Drive
            for drive_video in drive_videos:
                drive_name = drive_video.get('name', '').lower().strip()
                drive_name_without_ext = self._remove_extension(drive_name)
                
                logger.info(f"🔍 Kiểm tra: '{drive_video['name']}' -> '{drive_name}' (without ext: '{drive_name_without_ext}')")
                
                # Kiểm tra match chính xác
                exact_match = drive_name in sheet_video_names
                # Kiểm tra match không có extension
                name_match = drive_name_without_ext in sheet_video_names_without_ext
                
                if exact_match or name_match:
                    # Video đã có trong Sheet
                    videos_skipped.append(drive_video)
                    match_type = "exact" if exact_match else "name_only"
                    logger.info(f"⏭️ Bỏ qua: '{drive_video['name']}' (đã có trong Sheet - {match_type} match)")
                else:
                    # Video chưa có trong Sheet
                    videos_to_process.append(drive_video)
                    logger.info(f"✅ Cần xử lý: '{drive_video['name']}'")
            
            result = {
                'videos_to_process': videos_to_process,
                'videos_skipped': videos_skipped
            }
            
            logger.info(f"📊 Kết quả so sánh: {len(videos_to_process)} cần xử lý, {len(videos_skipped)} bỏ qua")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi so sánh video: {str(e)}")
            return {'videos_to_process': [], 'videos_skipped': []}
    
    def _remove_extension(self, filename: str) -> str:
        """
        Loại bỏ extension từ tên file
        
        Args:
            filename: Tên file
            
        Returns:
            Tên file không có extension
        """
        try:
            if not filename:
                return ""
            
            # Loại bỏ extension phổ biến
            extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
            for ext in extensions:
                if filename.lower().endswith(ext):
                    return filename[:-len(ext)]
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Lỗi remove extension: {str(e)}")
            return filename
    
    def get_check_summary(self, video_status: Dict) -> str:
        """
        Tạo summary của kết quả check
        
        Args:
            video_status: Kết quả từ check_video_status()
            
        Returns:
            String summary
        """
        try:
            summary = f"""
=== TÓM TẮT KIỂM TRA VIDEO ===
📁 Tổng video trên Drive: {video_status.get('total_drive_videos', 0)}
📊 Tổng video trong Sheet: {video_status.get('total_sheet_videos', 0)}
✅ Cần xử lý: {len(video_status.get('videos_to_process', []))} video
⏭️ Bỏ qua: {len(video_status.get('videos_skipped', []))} video
🕐 Thời gian check: {video_status.get('check_timestamp', 'Unknown')}
"""
            
            if video_status.get('videos_to_process'):
                summary += "\n📋 VIDEO CẦN XỬ LÝ:\n"
                for i, video in enumerate(video_status['videos_to_process'], 1):
                    summary += f"  {i}. {video['name']}\n"
            
            if video_status.get('videos_skipped'):
                summary += "\n⏭️ VIDEO BỎ QUA:\n"
                for i, video in enumerate(video_status['videos_skipped'], 1):
                    summary += f"  {i}. {video['name']}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo summary: {str(e)}")
            return "Không thể tạo summary"

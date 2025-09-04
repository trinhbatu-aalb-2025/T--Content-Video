#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Calculator Module
Tính toán và theo dõi token usage cho các API calls

Tính năng:
- Tính số token cho text input/output
- Ước tính chi phí API
- Theo dõi token usage tổng thể
- Log chi tiết token consumption
"""

import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TokenCalculator:
    """
    Class tính toán token usage cho các API
    """
    
    def __init__(self):
        # Pricing cho Gemini API (USD per 1M tokens)
        self.gemini_pricing = {
            'input': 0.075,   # $0.075 per 1M input tokens
            'output': 0.30    # $0.30 per 1M output tokens
        }
        
        # Pricing cho Deepgram API (USD per minute)
        self.deepgram_pricing = {
            'audio': 0.0043   # $0.0043 per minute
        }
        
        # Quota limits (có thể điều chỉnh)
        self.quota_limits = {
            'gemini_daily_tokens': 15000000,  # 15M tokens/day (Gemini Pro)
            'gemini_daily_cost': 10.0,        # $10/day limit
            'deepgram_daily_minutes': 1000,   # 1000 minutes/day
            'deepgram_daily_cost': 4.3        # $4.3/day limit
        }
        
        # Token usage tracking
        self.token_usage = []
        self.total_tokens = 0
        self.total_cost = 0.0
        
        # Daily tracking
        self.daily_usage = {
            'gemini_tokens': 0,
            'gemini_cost': 0.0,
            'deepgram_minutes': 0.0,
            'deepgram_cost': 0.0,
            'date': None
        }
        
        # Reset daily tracking nếu cần
        self._reset_daily_if_needed()
        
    def _reset_daily_if_needed(self):
        """
        Reset daily tracking nếu đã sang ngày mới
        """
        try:
            today = datetime.now().date()
            if self.daily_usage['date'] != today:
                self.daily_usage = {
                    'gemini_tokens': 0,
                    'gemini_cost': 0.0,
                    'deepgram_minutes': 0.0,
                    'deepgram_cost': 0.0,
                    'date': today
                }
                logger.info("🔄 Daily tracking reset for new day")
        except Exception as e:
            logger.error(f"❌ Lỗi reset daily tracking: {str(e)}")
        
    def calculate_tokens_gemini(self, text: str) -> Dict:
        """
        Tính số token cho Gemini API
        
        Args:
            text: Text cần tính token
            
        Returns:
            Dict chứa thông tin token
        """
        try:
            # Loại bỏ whitespace thừa
            cleaned_text = re.sub(r'\s+', ' ', text.strip())
            
            # Đếm ký tự
            char_count = len(cleaned_text)
            
            # Ước tính token dựa trên ngôn ngữ
            # Tiếng Việt: ~4 ký tự/token
            # Tiếng Trung: ~3 ký tự/token  
            # Tiếng Anh: ~4 ký tự/token
            
            # Phát hiện ngôn ngữ đơn giản
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            vietnamese_chars = len(re.findall(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', text, re.IGNORECASE))
            
            if chinese_chars > char_count * 0.3:
                # Chủ yếu tiếng Trung
                estimated_tokens = char_count // 3
                language = "Chinese"
            elif vietnamese_chars > char_count * 0.1:
                # Chủ yếu tiếng Việt
                estimated_tokens = char_count // 4
                language = "Vietnamese"
            else:
                # Tiếng Anh hoặc hỗn hợp
                estimated_tokens = char_count // 4
                language = "English/Mixed"
            
            # Tính chi phí
            input_cost = (estimated_tokens / 1_000_000) * self.gemini_pricing['input']
            output_cost = (estimated_tokens / 1_000_000) * self.gemini_pricing['output']
            total_cost = input_cost + output_cost
            
            result = {
                'characters': char_count,
                'estimated_tokens': estimated_tokens,
                'language': language,
                'input_cost_usd': input_cost,
                'output_cost_usd': output_cost,
                'total_cost_usd': total_cost,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi tính token: {str(e)}")
            return {
                'characters': len(text),
                'estimated_tokens': len(text) // 4,
                'language': 'Unknown',
                'input_cost_usd': 0.0,
                'output_cost_usd': 0.0,
                'total_cost_usd': 0.0,
                'timestamp': datetime.now().isoformat()
            }
    
    def calculate_tokens_deepgram(self, audio_duration_seconds: float) -> Dict:
        """
        Tính chi phí cho Deepgram API dựa trên thời lượng audio
        
        Args:
            audio_duration_seconds: Thời lượng audio (giây)
            
        Returns:
            Dict chứa thông tin chi phí
        """
        try:
            duration_minutes = audio_duration_seconds / 60.0
            cost = duration_minutes * self.deepgram_pricing['audio']
            
            result = {
                'duration_seconds': audio_duration_seconds,
                'duration_minutes': duration_minutes,
                'cost_usd': cost,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi tính chi phí Deepgram: {str(e)}")
            return {
                'duration_seconds': 0.0,
                'duration_minutes': 0.0,
                'cost_usd': 0.0,
                'timestamp': datetime.now().isoformat()
            }
    
    def track_api_call(self, operation: str, input_text: str = "", output_text: str = "", 
                      audio_duration: float = 0.0, api_type: str = "gemini") -> Dict:
        """
        Theo dõi một API call và tính token/chi phí
        
        Args:
            operation: Tên operation (translate, rewrite, etc.)
            input_text: Text input
            output_text: Text output
            audio_duration: Thời lượng audio (cho Deepgram)
            api_type: Loại API (gemini, deepgram)
            
        Returns:
            Dict chứa thông tin token usage
        """
        try:
            if api_type == "gemini":
                input_tokens = self.calculate_tokens_gemini(input_text) if input_text else {}
                output_tokens = self.calculate_tokens_gemini(output_text) if output_text else {}
                
                total_tokens = input_tokens.get('estimated_tokens', 0) + output_tokens.get('estimated_tokens', 0)
                total_cost = input_tokens.get('total_cost_usd', 0) + output_tokens.get('total_cost_usd', 0)
                
                usage_info = {
                    'operation': operation,
                    'api_type': api_type,
                    'input_tokens': input_tokens.get('estimated_tokens', 0),
                    'output_tokens': output_tokens.get('estimated_tokens', 0),
                    'total_tokens': total_tokens,
                    'cost_usd': total_cost,
                    'input_language': input_tokens.get('language', 'Unknown'),
                    'output_language': output_tokens.get('language', 'Unknown'),
                    'timestamp': datetime.now().isoformat()
                }
                
            elif api_type == "deepgram":
                deepgram_info = self.calculate_tokens_deepgram(audio_duration)
                
                usage_info = {
                    'operation': operation,
                    'api_type': api_type,
                    'audio_duration_seconds': audio_duration,
                    'cost_usd': deepgram_info['cost_usd'],
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                usage_info = {
                    'operation': operation,
                    'api_type': api_type,
                    'error': 'Unknown API type',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Lưu vào tracking
            self.token_usage.append(usage_info)
            self.total_tokens += usage_info.get('total_tokens', 0)
            self.total_cost += usage_info.get('cost_usd', 0)
            
            # Cập nhật daily tracking
            self._update_daily_usage(usage_info)
            
            # Log chi tiết
            self._log_operation(usage_info)
            
            return usage_info
            
        except Exception as e:
            logger.error(f"❌ Lỗi track API call: {str(e)}")
            return {
                'operation': operation,
                'api_type': api_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _log_operation(self, usage_info: Dict):
        """
        Log chi tiết cho một operation
        """
        try:
            operation = usage_info.get('operation', 'Unknown')
            api_type = usage_info.get('api_type', 'Unknown')
            
            if api_type == "gemini":
                input_tokens = usage_info.get('input_tokens', 0)
                output_tokens = usage_info.get('output_tokens', 0)
                total_tokens = usage_info.get('total_tokens', 0)
                cost = usage_info.get('cost_usd', 0)
                
                logger.info(f"📊 Token Usage - {operation}:")
                logger.info(f"  Input: {input_tokens:,} tokens")
                logger.info(f"  Output: {output_tokens:,} tokens")
                logger.info(f"  Total: {total_tokens:,} tokens")
                logger.info(f"  Cost: ${cost:.6f}")
                
            elif api_type == "deepgram":
                duration = usage_info.get('audio_duration_seconds', 0)
                cost = usage_info.get('cost_usd', 0)
                
                logger.info(f"🎤 Deepgram Usage - {operation}:")
                logger.info(f"  Duration: {duration:.1f}s")
                logger.info(f"  Cost: ${cost:.6f}")
                
        except Exception as e:
            logger.error(f"❌ Lỗi log operation: {str(e)}")
    
    def _update_daily_usage(self, usage_info: Dict):
        """
        Cập nhật daily usage tracking
        """
        try:
            # Reset daily nếu cần
            self._reset_daily_if_needed()
            
            api_type = usage_info.get('api_type', '')
            
            if api_type == "gemini":
                tokens = usage_info.get('total_tokens', 0)
                cost = usage_info.get('cost_usd', 0)
                self.daily_usage['gemini_tokens'] += tokens
                self.daily_usage['gemini_cost'] += cost
                
            elif api_type == "deepgram":
                duration = usage_info.get('audio_duration_seconds', 0)
                cost = usage_info.get('cost_usd', 0)
                self.daily_usage['deepgram_minutes'] += duration / 60.0
                self.daily_usage['deepgram_cost'] += cost
                
        except Exception as e:
            logger.error(f"❌ Lỗi cập nhật daily usage: {str(e)}")
    
    def get_summary(self) -> Dict:
        """
        Lấy tổng kết token usage
        """
        try:
            gemini_operations = [op for op in self.token_usage if op.get('api_type') == 'gemini']
            deepgram_operations = [op for op in self.token_usage if op.get('api_type') == 'deepgram']
            
            gemini_tokens = sum([op.get('total_tokens', 0) for op in gemini_operations])
            gemini_cost = sum([op.get('cost_usd', 0) for op in gemini_operations])
            
            deepgram_cost = sum([op.get('cost_usd', 0) for op in deepgram_operations])
            
            summary = {
                'total_operations': len(self.token_usage),
                'gemini_operations': len(gemini_operations),
                'deepgram_operations': len(deepgram_operations),
                'total_tokens': self.total_tokens,
                'total_cost_usd': self.total_cost,
                'gemini_tokens': gemini_tokens,
                'gemini_cost_usd': gemini_cost,
                'deepgram_cost_usd': deepgram_cost,
                'timestamp': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi tạo summary: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def log_summary(self):
        """
        Log tổng kết token usage và quota status
        """
        try:
            summary = self.get_summary()
            
            logger.info("=" * 70)
            logger.info("📊 TOKEN USAGE & QUOTA SUMMARY")
            logger.info("=" * 70)
            logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"🔄 Total Operations: {summary.get('total_operations', 0)}")
            logger.info(f"🔤 Gemini Operations: {summary.get('gemini_operations', 0)}")
            logger.info(f"🎤 Deepgram Operations: {summary.get('deepgram_operations', 0)}")
            logger.info("")
            
            # Gemini API Summary
            logger.info("🔤 GEMINI API:")
            gemini_tokens = summary.get('gemini_tokens', 0)
            gemini_cost = summary.get('gemini_cost_usd', 0)
            logger.info(f"  Total Tokens: {gemini_tokens:,}")
            logger.info(f"  Cost: ${gemini_cost:.6f}")
            
            # Quota status cho Gemini
            daily_tokens = self.daily_usage['gemini_tokens']
            daily_cost = self.daily_usage['gemini_cost']
            token_limit = self.quota_limits['gemini_daily_tokens']
            cost_limit = self.quota_limits['gemini_daily_cost']
            
            token_percent = (daily_tokens / token_limit) * 100
            cost_percent = (daily_cost / cost_limit) * 100
            
            logger.info(f"  Daily Tokens: {daily_tokens:,} / {token_limit:,} ({token_percent:.1f}%)")
            logger.info(f"  Daily Cost: ${daily_cost:.6f} / ${cost_limit:.2f} ({cost_percent:.1f}%)")
            
            if token_percent > 80:
                logger.warning(f"  ⚠️ Token usage approaching limit!")
            if cost_percent > 80:
                logger.warning(f"  ⚠️ Cost approaching daily limit!")
            
            logger.info("")
            
            # Deepgram API Summary
            logger.info("🎤 DEEPGRAM API:")
            deepgram_cost = summary.get('deepgram_cost_usd', 0)
            logger.info(f"  Total Cost: ${deepgram_cost:.6f}")
            
            # Quota status cho Deepgram
            daily_minutes = self.daily_usage['deepgram_minutes']
            daily_deepgram_cost = self.daily_usage['deepgram_cost']
            minutes_limit = self.quota_limits['deepgram_daily_minutes']
            deepgram_cost_limit = self.quota_limits['deepgram_daily_cost']
            
            minutes_percent = (daily_minutes / minutes_limit) * 100
            deepgram_cost_percent = (daily_deepgram_cost / deepgram_cost_limit) * 100
            
            logger.info(f"  Daily Minutes: {daily_minutes:.1f} / {minutes_limit:.1f} ({minutes_percent:.1f}%)")
            logger.info(f"  Daily Cost: ${daily_deepgram_cost:.6f} / ${deepgram_cost_limit:.2f} ({deepgram_cost_percent:.1f}%)")
            
            if minutes_percent > 80:
                logger.warning(f"  ⚠️ Audio duration approaching limit!")
            if deepgram_cost_percent > 80:
                logger.warning(f"  ⚠️ Cost approaching daily limit!")
            
            logger.info("")
            
            # Overall Summary
            total_cost = summary.get('total_cost_usd', 0)
            logger.info("💰 OVERALL SUMMARY:")
            logger.info(f"  Total Cost: ${total_cost:.6f}")
            logger.info(f"  Daily Total Cost: ${daily_cost + daily_deepgram_cost:.6f}")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Lỗi log summary: {str(e)}")
    
    def reset(self):
        """
        Reset tất cả tracking data
        """
        self.token_usage = []
        self.total_tokens = 0
        self.total_cost = 0.0
        logger.info("🔄 Token tracking đã được reset")
    
    def export_to_file(self, filepath: str):
        """
        Export token usage data ra file JSON
        """
        try:
            import json
            
            export_data = {
                'summary': self.get_summary(),
                'operations': self.token_usage,
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📁 Token usage data đã export: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi export data: {str(e)}")
    
    def check_quota_status(self) -> Dict:
        """
        Kiểm tra trạng thái quota hiện tại
        """
        try:
            self._reset_daily_if_needed()
            
            gemini_token_percent = (self.daily_usage['gemini_tokens'] / self.quota_limits['gemini_daily_tokens']) * 100
            gemini_cost_percent = (self.daily_usage['gemini_cost'] / self.quota_limits['gemini_daily_cost']) * 100
            deepgram_minutes_percent = (self.daily_usage['deepgram_minutes'] / self.quota_limits['deepgram_daily_minutes']) * 100
            deepgram_cost_percent = (self.daily_usage['deepgram_cost'] / self.quota_limits['deepgram_daily_cost']) * 100
            
            status = {
                'gemini': {
                    'tokens_used': self.daily_usage['gemini_tokens'],
                    'tokens_limit': self.quota_limits['gemini_daily_tokens'],
                    'tokens_percent': gemini_token_percent,
                    'cost_used': self.daily_usage['gemini_cost'],
                    'cost_limit': self.quota_limits['gemini_daily_cost'],
                    'cost_percent': gemini_cost_percent,
                    'status': 'OK' if gemini_token_percent < 80 and gemini_cost_percent < 80 else 'WARNING'
                },
                'deepgram': {
                    'minutes_used': self.daily_usage['deepgram_minutes'],
                    'minutes_limit': self.quota_limits['deepgram_daily_minutes'],
                    'minutes_percent': deepgram_minutes_percent,
                    'cost_used': self.daily_usage['deepgram_cost'],
                    'cost_limit': self.quota_limits['deepgram_daily_cost'],
                    'cost_percent': deepgram_cost_percent,
                    'status': 'OK' if deepgram_minutes_percent < 80 and deepgram_cost_percent < 80 else 'WARNING'
                },
                'overall': {
                    'total_daily_cost': self.daily_usage['gemini_cost'] + self.daily_usage['deepgram_cost'],
                    'date': self.daily_usage['date'].isoformat() if self.daily_usage['date'] else None
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Lỗi kiểm tra quota status: {str(e)}")
            return {'error': str(e)}
    
    def get_quota_warnings(self) -> List[str]:
        """
        Lấy danh sách cảnh báo quota
        """
        try:
            warnings = []
            status = self.check_quota_status()
            
            if status.get('gemini', {}).get('status') == 'WARNING':
                warnings.append("⚠️ Gemini API approaching daily limits")
            
            if status.get('deepgram', {}).get('status') == 'WARNING':
                warnings.append("⚠️ Deepgram API approaching daily limits")
            
            return warnings
            
        except Exception as e:
            logger.error(f"❌ Lỗi lấy quota warnings: {str(e)}")
            return [f"❌ Error: {str(e)}"]


# Test function
def test_token_calculator():
    """
    Test function để kiểm tra token calculator
    """
    # Setup logging để hiển thị trong test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('token_calculator_test.log', encoding='utf-8')
        ]
    )
    
    print("🧪 Testing Token Calculator...")
    
    calculator = TokenCalculator()
    
    # Test Gemini token calculation
    vietnamese_text = "Xin chào, đây là một đoạn văn bản tiếng Việt để test token calculator."
    chinese_text = "你好，这是一个中文文本来测试token计算器。"
    
    print("\n📊 Testing Vietnamese text:")
    result_vi = calculator.calculate_tokens_gemini(vietnamese_text)
    print(f"  Characters: {result_vi['characters']}")
    print(f"  Tokens: {result_vi['estimated_tokens']}")
    print(f"  Language: {result_vi['language']}")
    print(f"  Cost: ${result_vi['total_cost_usd']:.6f}")
    
    print("\n📊 Testing Chinese text:")
    result_cn = calculator.calculate_tokens_gemini(chinese_text)
    print(f"  Characters: {result_cn['characters']}")
    print(f"  Tokens: {result_cn['estimated_tokens']}")
    print(f"  Language: {result_cn['language']}")
    print(f"  Cost: ${result_cn['total_cost_usd']:.6f}")
    
    # Test tracking
    print("\n📊 Testing API call tracking:")
    calculator.track_api_call("translate", vietnamese_text, chinese_text, api_type="gemini")
    calculator.track_api_call("speech_to_text", audio_duration=120.5, api_type="deepgram")
    
    # Test summary
    print("\n📊 Testing summary:")
    calculator.log_summary()
    
    # Test quota status
    print("\n📊 Testing quota status:")
    quota_status = calculator.check_quota_status()
    print(f"  Gemini Status: {quota_status['gemini']['status']}")
    print(f"  Deepgram Status: {quota_status['deepgram']['status']}")
    
    # Test quota warnings
    print("\n📊 Testing quota warnings:")
    warnings = calculator.get_quota_warnings()
    for warning in warnings:
        print(f"  {warning}")
    
    print("\n✅ Token Calculator test completed!")


if __name__ == "__main__":
    test_token_calculator()

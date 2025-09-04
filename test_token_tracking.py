#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test đơn giản để kiểm tra token tracking
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Thêm path để import module
sys.path.append(os.path.join(os.path.dirname(__file__), 'run'))

def test_token_tracking():
    """Test token tracking"""
    try:
        from token_calculator import TokenCalculator
        
        print("🧪 Testing Token Tracking...")
        
        # Khởi tạo calculator
        tc = TokenCalculator()
        print("✅ TokenCalculator khởi tạo thành công")
        
        # Test tracking một số operations
        print("\n📊 Testing API call tracking...")
        
        # Simulate translation
        tc.track_api_call(
            operation="translate_chinese_to_vietnamese",
            input_text="小衣柜的正确做法顶部做储物区收纳大件被褥右边分三层上面挂",
            output_text="Cách làm đúng của tủ quần áo nhỏ là làm khu vực cất trữ ở phía trên để cất trữ chăn màn cỡ lớn, bên phải chia làm ba tầng, phía trên để treo đồ.",
            api_type="gemini"
        )
        
        # Simulate rewrite
        tc.track_api_call(
            operation="rewrite_text",
            input_text="Cách làm đúng của tủ quần áo nhỏ...",
            output_text="TIÊU ĐỀ GỢI Ý: 1. 🚀 Tủ quần áo nhỏ cũng hóa 'khổng lồ' với mẹo này!...",
            api_type="gemini"
        )
        
        # Simulate speech to text
        tc.track_api_call(
            operation="speech_to_text",
            audio_duration=35.7,  # 35.7 giây từ log của bạn
            api_type="deepgram"
        )
        
        # Show summary
        print("\n📊 Token Usage Summary:")
        tc.log_summary()
        
        print("\n✅ Token tracking test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_token_tracking()
    if success:
        print("\n🎯 Token Calculator đã sẵn sàng!")
    else:
        print("\n❌ Cần kiểm tra lại Token Calculator!")

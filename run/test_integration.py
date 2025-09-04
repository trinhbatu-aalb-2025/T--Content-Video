#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Integration
Kiểm tra tích hợp Token Calculator với all_in_one.py
"""

import logging
import sys
import os

# Thêm thư mục hiện tại vào path để import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_integration():
    """
    Test tích hợp Token Calculator
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("Testing Token Calculator Integration...")
    
    try:
        # Test import TokenCalculator
        from token_calculator import TokenCalculator
        print("✅ TokenCalculator import thành công")
        
        # Test import AllInOneProcessor
        from all_in_one import AllInOneProcessor
        print("✅ AllInOneProcessor import thành công")
        
        # Test khởi tạo TokenCalculator
        calc = TokenCalculator()
        print("✅ TokenCalculator khởi tạo thành công")
        
        # Test một số API calls
        print("\nTesting API calls...")
        
        calc.track_api_call("test_translate", "Hello world", "Xin chào thế giới", api_type="gemini")
        calc.track_api_call("test_speech", audio_duration=60.0, api_type="deepgram")
        
        # Test summary
        print("\nTesting summary...")
        calc.log_summary()
        
        print("\n✅ Integration test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_integration()
    if success:
        print("\n🎉 Tất cả tests đều thành công!")
    else:
        print("\n💥 Có lỗi xảy ra!")

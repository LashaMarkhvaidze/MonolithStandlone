#!/usr/bin/env python3
"""
Test script for AI Chat endpoints
Run this to verify the backend is working correctly
"""

import sys
import json
from dbhelper import dbhelper

def test_database():
    """Test database operations"""
    print("=" * 60)
    print("Testing Database Operations")
    print("=" * 60)
    
    db = dbhelper()
    
    # Test saving settings
    print("\n1. Testing SaveAISettings...")
    result = db.SaveAISettings('openai', 'test-api-key-123', 'gpt-4')
    result_data = json.loads(result)
    print(f"   Result: {result}")
    assert result_data['status'] == 'SUCCESS', "Failed to save settings"
    print("   ✓ Save settings successful")
    
    # Test getting active settings
    print("\n2. Testing GetActiveAISettings...")
    result = db.GetActiveAISettings()
    result_data = json.loads(result)
    print(f"   Result: {result}")
    assert result_data['status'] == 'SUCCESS', "Failed to get settings"
    assert result_data['provider'] == 'openai', "Provider mismatch"
    assert result_data['model'] == 'gpt-4', "Model mismatch"
    assert result_data['apikey'] == 'test-api-key-123', "API key mismatch"
    print("   ✓ Get active settings successful")
    
    # Test getting all settings
    print("\n3. Testing GetAllAISettings...")
    result = db.GetAllAISettings()
    result_data = json.loads(result)
    print(f"   Result: {result}")
    assert isinstance(result_data, list), "Should return a list"
    assert len(result_data) > 0, "Should have at least one setting"
    print(f"   ✓ Found {len(result_data)} setting(s)")
    
    # Test saving another setting (should deactivate previous)
    print("\n4. Testing multiple settings (deactivation)...")
    result = db.SaveAISettings('claude', 'test-claude-key', 'claude-3-5-sonnet-20241022')
    result_data = json.loads(result)
    assert result_data['status'] == 'SUCCESS', "Failed to save second settings"
    
    result = db.GetActiveAISettings()
    result_data = json.loads(result)
    assert result_data['provider'] == 'claude', "Should have switched to claude"
    print("   ✓ Multiple settings work correctly")
    
    print("\n" + "=" * 60)
    print("All database tests passed! ✓")
    print("=" * 60)

def test_json_format():
    """Test JSON formatting"""
    print("\n" + "=" * 60)
    print("Testing JSON Format")
    print("=" * 60)
    
    db = dbhelper()
    
    # Test each endpoint returns valid JSON
    endpoints = [
        ('SaveAISettings', lambda: db.SaveAISettings('openai', 'key', 'gpt-4')),
        ('GetActiveAISettings', lambda: db.GetActiveAISettings()),
        ('GetAllAISettings', lambda: db.GetAllAISettings()),
    ]
    
    for name, func in endpoints:
        print(f"\n{name}:")
        result = func()
        print(f"   Raw: {result}")
        try:
            parsed = json.loads(result)
            print(f"   Parsed: {parsed}")
            print(f"   ✓ Valid JSON")
        except json.JSONDecodeError as e:
            print(f"   ✗ Invalid JSON: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("All JSON format tests passed! ✓")
    print("=" * 60)

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "AI Chat Endpoints Test Suite" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        test_database()
        test_json_format()
        
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 15 + "ALL TESTS PASSED! ✓" + " " * 24 + "║")
        print("╚" + "=" * 58 + "╝")
        print("\nYou can now start the server with: ./start.sh")
        print("Then open: http://localhost:8000")
        print("\n")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

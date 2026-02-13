"""Test script for YouTube format detection using YouTubeService.

This script tests fetching available video formats and resolutions.
"""
import sys
from pathlib import Path

# Configuration - Use same URL as test_download.py
VIDEO_URL = "https://www.youtube.com/watch?v=RQDCbgn2vDM"

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))



from src.services.youtube_service import YouTubeService
import json


def test_format_detection():
    """Test fetching available formats for a YouTube video."""
    
    print("\n" + "=" * 70)
    print("YouTube Format Detection Test")
    print("=" * 70)
    print(f"Video URL: {VIDEO_URL}\n")
    
    # Extract video ID
    print("Step 1: Extracting video ID...")
    video_id = YouTubeService.parse_video_id_from_url(VIDEO_URL)
    
    if not video_id:
        print("❌ Failed to extract video ID from URL")
        return False
    
    print(f"✅ Video ID: {video_id}\n")
    
    # Get available formats
    print("Step 2: Fetching available formats...")
    print("(This may take 10-30 seconds...)\n")
    
    formats_info = YouTubeService.get_available_formats(video_id)
    
    if not formats_info:
        print("❌ Failed to fetch available formats")
        return False
    
    print("✅ Successfully fetched formats!\n")
    
    # Display results
    print("=" * 70)
    print("Available High-Quality Resolutions (720p+)")
    print("=" * 70)
    
    if formats_info:
        print(f"\n📹 Available Resolutions: {formats_info}")
        print(f"\n   Total: {len(formats_info)} resolution(s)")
    else:
        print("\n  No high-quality formats available")
    
    print("\n" + "=" * 70)
    print("✅ Format Detection Test PASSED")
    print("=" * 70)
    
    return True


def test_parse_video_id():
    """Test video ID extraction from various URL formats."""
    
    print("\n" + "=" * 70)
    print("Video ID Parsing Test")
    print("=" * 70)
    
    test_urls = [
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "jNQXAC9IVRw"),
        ("https://youtu.be/jNQXAC9IVRw", "jNQXAC9IVRw"),
        ("https://www.youtube.com/watch?v=jNQXAC9IVRw&t=30s", "jNQXAC9IVRw"),
        ("https://m.youtube.com/watch?v=jNQXAC9IVRw", "jNQXAC9IVRw"),
    ]
    
    all_passed = True
    
    for url, expected_id in test_urls:
        video_id = YouTubeService.parse_video_id_from_url(url)
        status = "✅" if video_id == expected_id else "❌"
        print(f"{status} {url[:50]}... → {video_id}")
        
        if video_id != expected_id:
            all_passed = False
            print(f"   Expected: {expected_id}, Got: {video_id}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ Video ID Parsing Test PASSED")
    else:
        print("❌ Video ID Parsing Test FAILED")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    print("\n🧪 Starting YouTube Service Tests\n")
    
    # Test 1: Parse video ID
    test1_passed = test_parse_video_id()
    
    # Test 2: Format detection
    test2_passed = test_format_detection()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Video ID Parsing: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Format Detection: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 70)
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed!\n")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed\n")
        sys.exit(1)

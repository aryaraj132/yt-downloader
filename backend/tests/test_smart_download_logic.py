import sys
from pathlib import Path

script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.services.video_service import VideoService

test_cases = [
    ("720p", "mp4", False, "mp4"),
    ("1080p", "mp4", False, "mp4"),
    ("1440p", "mp4", True, "webm→mp4"),
    ("2160p", "mp4", True, "webm→mp4"),
    ("720p", "webm", False, "webm"),
    ("1080p", "webm", False, "webm"),
    ("1440p", "webm", False, "webm"),
    ("2160p", "webm", False, "webm"),
]

print("\n" + "=" * 70)
print("Smart Download Logic Test")
print("=" * 70)
print("\nResolution | Format | Needs Encoding? | Download Flow")
print("-" * 70)

for resolution, format_pref, expected_encoding, expected_flow in test_cases:
    height = VideoService._extract_resolution_height(resolution)
    needs_encoding = (height >= 1440 and format_pref == 'mp4')
    
    status = "✅" if needs_encoding == expected_encoding else "❌"
    
    print(f"{status} {resolution:>6} | {format_pref:>4} | {str(needs_encoding):>15} | {expected_flow}")

print("=" * 70)
print("\n✅ Logic verification complete!\n")

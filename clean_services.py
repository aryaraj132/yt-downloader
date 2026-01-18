import os
import re

services_dir = "d:/yt-downloader/src/services"

files_to_clean = [
    "__init__.py",
    "cache_service.py",
    "cleanup_service.py",
    "db_service.py",
    "encoding_service.py",
    "ffmpeg_utils_service.py",
    "firebase_service.py",
    "progress_cache.py",
    "video_service.py",
    "youtube_service.py"
]

for filename in files_to_clean:
    filepath = os.path.join(services_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove all docstrings (""")
    # Remove triple quotes with anything between them
    content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
    
    # Remove empty lines that were left
    lines = content.split('\n')
    cleaned_lines = []
    prev_empty = False
    
    for line in lines:
        stripped = line.strip()
        is_empty = not stripped
        
        # Keep line if not empty, or if it's the first empty line in a sequence
        if not is_empty or not prev_empty:
            cleaned_lines.append(line)
        
        prev_empty = is_empty
    
    content = '\n'.join(cleaned_lines)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Cleaned {filename}")

print("\n✅ All service files cleaned!")

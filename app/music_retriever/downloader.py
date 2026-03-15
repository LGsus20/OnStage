import os
import yt_dlp
from typing import Dict, Any
from app.constants import MUSIC_FILES_DIR, AUDIO_FORMAT, AUDIO_QUALITY

def download_video(url: str, username: str, output_path: str = MUSIC_FILES_DIR) -> Dict[str, Any]:
    
    # Ensure output directory exists (absolute path is safer)
    abs_output_path = os.path.abspath(output_path)
    os.makedirs(abs_output_path, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': AUDIO_FORMAT,
            'preferredquality': AUDIO_QUALITY,
        }],
        'outtmpl': os.path.join(abs_output_path, '%(artist)s - %(title)s - ' + username + '.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
        # ADDED: Fake user agent and client
        # Force Android client
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }



    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract info without downloading to check metadata
            info = ydl.extract_info(url, download=False)
            
            # 2. Check for missing or overly verbose artist string
            artist = info.get('artist')
            title = info.get('title')
            uploader = info.get('uploader')
            
            # Heuristic: If artist is missing, super long, or seems to be a list of credits
            is_suspicious_artist = not artist or len(artist) > 50 or artist.count(',') > 2
            
            if is_suspicious_artist:
                 # Fallback to uploader if available and reasonable, else 'Unknown Artist'
                 if uploader and len(uploader) < 50 and uploader.count(',') < 3:
                     safe_artist = uploader
                 else:
                     safe_artist = 'Unknown Artist'
                     
                 # Sanitize safe_artist for filename safety (basic)
                 safe_artist = "".join([c if c.isalnum() or c in " ._-" else "_" for c in safe_artist])

                 # If title already looks like "Artist - Song", use that directly
                 if title and " - " in title:
                     new_template = '%(title)s - ' + username + '.%(ext)s'
                 else:
                     # Use our safe_artist instead of %(artist)s
                     new_template = f'{safe_artist} - %(title)s - ' + username + '.%(ext)s'
                 
                 ydl.params['outtmpl']['default'] = os.path.join(abs_output_path, new_template)

            # 3. Download
            error_code = ydl.download([url])
            
            # Since we downloaded, we need to find out what the filename actually became
            # prepare_filename uses the info dict. 
            # Note: prepare_filename returns the original extension (e.g. webm), 
            # but ffmpeg converts it to mp3. We need to account for that.

            # Re-run prepare_filename logic roughly
            original_filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(original_filename)
            final_filename = base + "." + AUDIO_FORMAT
            
            return {
                "success": True,
                "title": info.get('title'),
                "filename": os.path.basename(final_filename)
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

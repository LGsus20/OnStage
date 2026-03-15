import os

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "Set_This_Using_the_bash_script")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

# Admin Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_PLAIN = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USERNAME or not ADMIN_PASSWORD_PLAIN:
    raise ValueError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set")

# Cookie Security
COOKIE_SECURE = False # Set to True in production with HTTPS

# Music Download Configuration
MUSIC_FILES_DIR = "music_files"
AUDIO_FORMAT = "mp3"
AUDIO_QUALITY = "192" # kbps

# Playback Configuration
SYNC_DEVIATION_SECONDS = 3

# Server Configuration
RELOAD_SERVER = True

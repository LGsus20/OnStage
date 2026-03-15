from typing import Optional
from datetime import datetime

class MusicState:
    def __init__(self):
        self.current_song: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.pause_start_time: Optional[datetime] = None
        self.queue: list[dict] = []  # List of {filename: str, requested_by: str}
        self.history: list[dict] = []  # List of {filename: str, timestamp: datetime}

# Global instance
music_state = MusicState()

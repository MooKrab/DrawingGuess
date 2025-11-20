import os
import random
import pygame
from libs.utils.pylog import Logger

logger = Logger("MusicManager")

class MusicManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MusicManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Path configuration: src/assets/common/static
        # We use os.path.join to ensure cross-platform compatibility
        self.music_dir = os.path.abspath(os.path.join('src', 'assets', 'music'))
        self.tracks = []
        
        self._load_tracks()

    def _load_tracks(self):
        """Scans the directory for supported audio files."""
        if not os.path.exists(self.music_dir):
            logger.warning(f"Music directory not found: {self.music_dir}")
            # Optional: Create directory if it doesn't exist to prevent future warnings
            # os.makedirs(self.music_dir, exist_ok=True)
            return

        for f in os.listdir(self.music_dir):
            # Supports .mp3, standard .ogg, and the specific .org extension requested
            if f.lower().endswith(('.mp3', '.ogg', '.org')):
                full_path = os.path.join(self.music_dir, f)
                self.tracks.append(full_path)
        
        logger.info(f"Found {len(self.tracks)} music tracks.")

    def update(self, is_enabled: bool):
        """
        Updates playback based on the settings boolean.
        If enabled: plays a track (if not already playing) or unpauses.
        If disabled: pauses the music.
        """
        # Ensure mixer is initialized
        if not pygame.mixer.get_init():
            return

        if is_enabled:
            if not self.tracks:
                return

            if not pygame.mixer.music.get_busy():
                self.play_random()
            else:
                # If music is paused, unpause it.
                # Note: get_busy() returns False if paused in some pygame versions, 
                # so we might just need to Play if not busy.
                # But to be safe for pause/unpause logic:
                try:
                    pygame.mixer.music.unpause()
                    # If it wasn't paused but stopped, unpause does nothing, so check busy again
                    if not pygame.mixer.music.get_busy():
                        self.play_random()
                except Exception as e:
                    logger.error(f"Error unpausing music: {e}")
        else:
            pygame.mixer.music.pause()

    def play_random(self):
        """Plays a random track from the loaded list on loop."""
        if not self.tracks:
            return
        
        track = random.choice(self.tracks)
        try:
            logger.info(f"Playing music: {os.path.basename(track)}")
            pygame.mixer.music.load(track)
            pygame.mixer.music.play(-1) # Loop indefinitely
        except Exception as e:
            logger.error(f"Error playing music track {track}: {e}")

# Singleton Accessor
_manager = MusicManager()
def get_music_manager() -> MusicManager:
    return _manager
"""
Streamlit Video Player

A Streamlit component for video playback with time/frame tracking
and bidirectional control.
"""

from streamlit_video_state_player.video_player import VideoState, video_player

__all__ = ["video_player", "VideoState"]
__version__ = "0.1.0"

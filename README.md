# Streamlit Video State Player

A Streamlit component for video playback with time/frame tracking and bidirectional control.

## Installation

```bash
pip install streamlit-video-state-player
```

## Usage

```python
from streamlit_video_state_player import video_player

state = video_player("video.mp4", key="my_video")

# Access playback state
print(f"Time: {state.current_time}s, Frame: {state.frame_number}")
```

## Features

- Reports current time and frame number to Python
- Seek video from Python (for plot sync)
- Auto-detects FPS
- Works with local files

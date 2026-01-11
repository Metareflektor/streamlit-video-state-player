"""
Streamlit Video Player Component

A custom Streamlit component that provides video playback with time/frame tracking
and bidirectional control (seek from Python).
"""

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import streamlit as st

# HTML template for the video player
_HTML = """
<div class="video-container" id="container">
    <video id="video" controls></video>
    <div class="video-info" id="info"></div>
</div>
"""

# CSS for the video player
_CSS = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

.video-container {
    width: 100%;
    position: relative;
    background: #000;
}

video {
    width: 100%;
    display: block;
}

.video-info {
    position: absolute;
    bottom: 50px;
    left: 10px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s;
}

.video-container:hover .video-info {
    opacity: 1;
}
"""

# JavaScript for the video player
_JS = """
export default function(component) {
    const { data, setStateValue, parentElement } = component;

    const video = parentElement.querySelector('#video');
    const container = parentElement.querySelector('#container');
    const info = parentElement.querySelector('#info');

    // State tracking
    let detectedFps = 30; // Default fallback
    let fpsDetectionComplete = false;
    let lastUpdateTime = 0;
    const UPDATE_THROTTLE_MS = 250; // 4 Hz updates to Python
    let lastSeekTo = null;

    // Apply configuration from Python
    if (data) {
        // Set video source
        if (data.video_src && video.src !== data.video_src) {
            video.src = data.video_src;
        }

        // Set height
        if (data.height) {
            container.style.height = data.height + 'px';
            video.style.maxHeight = data.height + 'px';
        }

        // Autoplay
        if (data.autoplay) {
            video.autoplay = true;
        }

        // Loop
        if (data.loop) {
            video.loop = true;
        }

        // Handle seek command from Python
        if (data.seek_to !== null && data.seek_to !== undefined && data.seek_to !== lastSeekTo) {
            lastSeekTo = data.seek_to;
            if (video.readyState >= 1) {
                video.currentTime = data.seek_to;
            } else {
                video.addEventListener('loadedmetadata', () => {
                    video.currentTime = data.seek_to;
                }, { once: true });
            }
        }
    }

    /**
     * Detect FPS using requestVideoFrameCallback API
     * Falls back to 30 fps if not supported
     */
    function detectFps() {
        if (!('requestVideoFrameCallback' in HTMLVideoElement.prototype)) {
            console.log('requestVideoFrameCallback not supported, using fallback FPS');
            return;
        }

        let frameCount = 0;
        let startTime = null;
        const SAMPLE_DURATION_MS = 1000;

        function countFrame(now, metadata) {
            if (startTime === null) {
                startTime = now;
                frameCount = 0;
            }

            frameCount++;

            if (now - startTime >= SAMPLE_DURATION_MS) {
                detectedFps = Math.round(frameCount / ((now - startTime) / 1000));
                fpsDetectionComplete = true;
                console.log('Detected FPS: ' + detectedFps);
                updateState(true); // Force update with new FPS
            } else {
                video.requestVideoFrameCallback(countFrame);
            }
        }

        // Start detection when video plays
        video.addEventListener('play', function startDetection() {
            if (!fpsDetectionComplete) {
                video.requestVideoFrameCallback(countFrame);
            }
        }, { once: true });
    }

    /**
     * Calculate current frame number from time and FPS
     */
    function getCurrentFrame() {
        return Math.floor(video.currentTime * detectedFps);
    }

    /**
     * Update state sent to Python
     */
    function updateState(force) {
        force = force || false;
        const now = Date.now();

        // Throttle updates unless forced
        if (!force && now - lastUpdateTime < UPDATE_THROTTLE_MS) {
            return;
        }
        lastUpdateTime = now;

        const state = {
            current_time: video.currentTime || 0,
            frame_number: getCurrentFrame(),
            duration: video.duration || 0,
            fps: detectedFps,
            is_playing: !video.paused && !video.ended
        };

        setStateValue('state', state);

        // Update info overlay
        info.textContent = state.current_time.toFixed(2) + 's | Frame ' + state.frame_number + ' | ' + detectedFps + ' fps';
    }

    /**
     * Set up continuous updates during playback using requestAnimationFrame
     * This provides smoother updates than relying solely on timeupdate event
     */
    function startPlaybackUpdates() {
        function tick() {
            if (!video.paused && !video.ended) {
                updateState();
                requestAnimationFrame(tick);
            }
        }
        requestAnimationFrame(tick);
    }

    // Event listeners
    video.addEventListener('loadedmetadata', function() {
        updateState(true);
    });

    video.addEventListener('play', function() {
        startPlaybackUpdates();
        updateState(true);
    });

    video.addEventListener('pause', function() {
        updateState(true);
    });

    video.addEventListener('seeked', function() {
        updateState(true);
    });

    video.addEventListener('ended', function() {
        updateState(true);
    });

    video.addEventListener('timeupdate', function() {
        updateState();
    });

    // Initialize FPS detection
    detectFps();

    // Initial state update
    updateState(true);

    // Cleanup function
    return function() {
        // No specific cleanup needed
    };
}
"""


@dataclass
class VideoState:
    """State returned by the video player component."""

    current_time: float = 0.0
    """Current playback time in seconds."""

    frame_number: int = 0
    """Current frame number (calculated from time and detected FPS)."""

    duration: float = 0.0
    """Total video duration in seconds."""

    fps: float = 30.0
    """Detected or default frames per second."""

    is_playing: bool = False
    """Whether the video is currently playing."""


# Register the component using v2 API
_component = st.components.v2.component(
    name="streamlit_video_state_player",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def _get_mime_type(file_path: str) -> str:
    """Get MIME type for a video file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "video/mp4"


def _prepare_video_source(source: Union[str, bytes, Path]) -> str:
    """
    Prepare video source for the component.

    Converts local files to base64 data URLs.
    """
    if isinstance(source, bytes):
        # Raw bytes - encode as base64
        b64 = base64.b64encode(source).decode()
        return f"data:video/mp4;base64,{b64}"

    if isinstance(source, Path):
        source = str(source)

    if isinstance(source, str):
        # Check if it's already a data URL or remote URL
        if source.startswith(("data:", "http://", "https://", "blob:")):
            return source

        # Local file path - read and encode
        path = Path(source)
        if path.exists():
            mime_type = _get_mime_type(source)
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"data:{mime_type};base64,{b64}"
        else:
            raise FileNotFoundError(f"Video file not found: {source}")

    raise TypeError(f"Unsupported source type: {type(source)}")


def video_player(
    source: Union[str, bytes, Path],
    *,
    key: str = None,
    seek_to: float = None,
    height: int = 400,
    autoplay: bool = False,
    loop: bool = False,
) -> VideoState:
    """
    Display a video player with time/frame tracking.

    This component provides bidirectional communication:
    - Returns current playback state (time, frame, fps, etc.)
    - Accepts seek commands via the `seek_to` parameter

    Parameters
    ----------
    source : str, bytes, or Path
        Video source. Can be:
        - Path to a local video file
        - Raw video bytes
        - URL (http/https)
        - Data URL

    key : str, optional
        Unique key for the component instance.

    seek_to : float, optional
        Time in seconds to seek to. When changed, the video will
        seek to this position.

    height : int, default 400
        Player height in pixels.

    autoplay : bool, default False
        Whether to auto-start playback.

    loop : bool, default False
        Whether to loop the video.

    Returns
    -------
    VideoState
        Current state of the video player:
        - current_time: float - Current playback time in seconds
        - frame_number: int - Current frame number
        - duration: float - Total duration in seconds
        - fps: float - Detected frames per second
        - is_playing: bool - Whether video is playing

    Examples
    --------
    Basic usage:

    >>> state = video_player("video.mp4", key="my_video")
    >>> st.write(f"Current time: {state.current_time:.2f}s")

    Seeking from Python (e.g., from plot click):

    >>> if st.button("Jump to 10 seconds"):
    ...     st.session_state.seek_target = 10.0
    >>> state = video_player(
    ...     "video.mp4",
    ...     key="my_video",
    ...     seek_to=st.session_state.get("seek_target")
    ... )
    """
    # Prepare the video source
    video_src = _prepare_video_source(source)

    # Default state
    default_state = {
        "current_time": 0.0,
        "frame_number": 0,
        "duration": 0.0,
        "fps": 30.0,
        "is_playing": False,
    }

    # Call the component with on_state_change callback
    result = _component(
        data={
            "video_src": video_src,
            "seek_to": seek_to,
            "height": height,
            "autoplay": autoplay,
            "loop": loop,
        },
        key=key,
        default={"state": default_state},
        on_state_change=lambda: None,  # Required callback for state updates
    )

    # Convert result to VideoState
    if result is None:
        return VideoState()

    # Access the nested state dict
    state_dict = getattr(result, "state", None)
    if state_dict is None:
        state_dict = result.get("state", default_state) if isinstance(result, dict) else default_state

    if isinstance(state_dict, dict):
        return VideoState(
            current_time=state_dict.get("current_time", 0.0),
            frame_number=state_dict.get("frame_number", 0),
            duration=state_dict.get("duration", 0.0),
            fps=state_dict.get("fps", 30.0),
            is_playing=state_dict.get("is_playing", False),
        )

    return VideoState()

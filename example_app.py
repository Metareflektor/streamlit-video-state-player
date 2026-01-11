"""
Minimal example: Video Player with State
"""

import streamlit as st

from streamlit_video_state_player import video_player

st.set_page_config(page_title="Video State Demo")

st.title("Video Player with State")

state = video_player(
    "https://www.w3schools.com/html/mov_bbb.mp4",
    key="demo_video",
    height=400,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Time", f"{state.current_time:.2f}s")
col2.metric("Frame", state.frame_number)
col3.metric("FPS", f"{state.fps:.0f}")
col4.metric("Playing", "Yes" if state.is_playing else "No")

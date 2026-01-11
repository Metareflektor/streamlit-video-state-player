"""
Example: Video Player with Synced Timeline Plot
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from streamlit_video_state_player import video_player

st.set_page_config(page_title="Video + Plot Sync Demo", layout="wide")

st.title("Video Player with Synced Timeline Plot")

SAMPLE_VIDEO_URL = "https://www.w3schools.com/html/mov_bbb.mp4"

# Generate sample time-series data (10 seconds to match video)
VIDEO_DURATION = 10.0
time_points = np.linspace(0, VIDEO_DURATION, 300)
signal_1 = np.sin(2 * np.pi * 0.5 * time_points) + 0.5 * np.sin(2 * np.pi * 2 * time_points)
signal_2 = np.cos(2 * np.pi * 0.3 * time_points) * np.exp(-time_points / 10)

df = pd.DataFrame({
    "time": time_points,
    "Signal A": signal_1 + np.random.normal(0, 0.1, len(time_points)),
    "Signal B": signal_2 + np.random.normal(0, 0.05, len(time_points)),
})


@st.fragment(run_every=0.25)  # Auto-refresh every 250ms to sync with video
def video_with_plot():
    col1, col2 = st.columns([3, 1])

    with col1:
        state = video_player(
            SAMPLE_VIDEO_URL,
            key="demo_video",
            height=300,
        )

    with col2:
        st.metric("Time", f"{state.current_time:.2f}s")
        st.metric("Frame", state.frame_number)
        st.metric("FPS", f"{state.fps:.0f}")

    # Plot with time indicator (inside col1 to match video width)
    with col1:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["time"], y=df["Signal A"],
            mode="lines", name="Signal A",
            line=dict(color="#1f77b4", width=1.5),
        ))

        fig.add_trace(go.Scatter(
            x=df["time"], y=df["Signal B"],
            mode="lines", name="Signal B",
            line=dict(color="#ff7f0e", width=1.5),
        ))

        # Red vertical line at current video position
        fig.add_vline(
            x=state.current_time,
            line=dict(color="red", width=2),
            annotation=dict(text=f"{state.current_time:.1f}s", font=dict(color="red")),
        )

        fig.update_layout(
            xaxis_title="Time (s)",
            yaxis_title="Value",
            height=250,
            margin=dict(l=40, r=20, t=20, b=40),
        )

        st.plotly_chart(fig, width="stretch")


video_with_plot()

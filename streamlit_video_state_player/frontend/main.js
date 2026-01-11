/**
 * Streamlit Video Player Component
 *
 * Provides bidirectional communication between HTML5 video element and Python:
 * - Reports: current_time, frame_number, duration, fps, is_playing
 * - Accepts: seek_to commands from Python
 */

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
                console.log(`Detected FPS: ${detectedFps}`);
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
    function updateState(force = false) {
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

        setStateValue(state);

        // Update info overlay
        info.textContent = `${state.current_time.toFixed(2)}s | Frame ${state.frame_number} | ${detectedFps} fps`;
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
    video.addEventListener('loadedmetadata', () => {
        updateState(true);
    });

    video.addEventListener('play', () => {
        startPlaybackUpdates();
        updateState(true);
    });

    video.addEventListener('pause', () => {
        updateState(true);
    });

    video.addEventListener('seeked', () => {
        updateState(true);
    });

    video.addEventListener('ended', () => {
        updateState(true);
    });

    video.addEventListener('timeupdate', () => {
        updateState();
    });

    // Initialize FPS detection
    detectFps();

    // Initial state update
    updateState(true);

    // Cleanup function
    return () => {
        // No specific cleanup needed, event listeners are on the video element
        // which will be removed when the component unmounts
    };
}

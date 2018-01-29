"""Redis keys used throughout the entire application (Flask, etc.)."""

# GitLab Tools throttling.
POLL_SIMPLE_THROTTLE = 'gitlab-tools:poll_simple_throttle'  # Lock.

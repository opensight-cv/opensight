from collections import deque
from time import monotonic

get_time = monotonic  # in case it needs to be changed later


# Rolling average framerate
class FPS:
    __slots__ = ("times", "fps")
    ROLLING_AVERAGE_SIZE = 20

    def __init__(self):
        self.times = deque((get_time(),), self.ROLLING_AVERAGE_SIZE)
        self.fps = 0

    def update(self):
        self.times.append(get_time())
        self.fps = self.ROLLING_AVERAGE_SIZE / (self.times[-1] - self.times[0])

    def reset(self):
        self.times.clear()
        self.times.append(get_time())
        self.fps = 0

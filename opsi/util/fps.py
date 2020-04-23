from collections import deque
from time import perf_counter

get_time = perf_counter  # in case it needs to be changed later
# monotonic is too low-res on windows, and causes division by zero issues

# Rolling average framerate
class FPS:
    __slots__ = ("times", "fps")
    ROLLING_AVERAGE_SIZE = 20

    def __init__(self):
        self.times = deque((get_time(),), self.ROLLING_AVERAGE_SIZE)
        self.fps = 0

    def update(self):
        self.times.append(get_time())
        self.fps = self.ROLLING_AVERAGE_SIZE / max(1e-4, self.times[-1] - self.times[0])

    def reset(self):
        self.times.clear()
        self.times.append(get_time())
        self.fps = 0

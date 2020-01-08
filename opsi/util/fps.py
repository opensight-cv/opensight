from time import time


# This is instant framerate: 1 / delta_time
# TODO: Might be too noisy, etermine if we want rolling average
class FPS:
    __slots__ = ("time", "fps")

    def __init__(self):
        self.time = time()
        self.fps = 0

    def update(self):
        new_time = time()
        self.fps = 1 / (new_time - self.time)
        self.time = new_time

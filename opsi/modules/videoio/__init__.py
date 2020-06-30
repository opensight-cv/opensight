from dataclasses import dataclass
from threading import Event, Thread

from opsi.manager.manager_schema import Function
from opsi.util.cv import Mat
from opsi.util.unduplicator import Unduplicator

from .camhook import CamHook
from .h264 import ENGINE_AVAIL, EngineManager, H264CameraServer
from .input import create_capture, get_settings, parse_cammode
from .mjpeg import MjpegCameraServer

__package__ = "opsi.videoio"
__version__ = "0.123"

UndupeInstance = Unduplicator()
HookInstance = CamHook()
if ENGINE_AVAIL:
    EngineInstance = EngineManager(HookInstance)
    HookInstance.add_listener("pipeline_update", EngineInstance.restart_engine)
    HookInstance.add_listener("shutdown", EngineInstance.shutdown)


class CameraInput(Function):
    require_restart = True

    def on_start(self):
        camNum = parse_cammode(self.settings.mode)[0]
        if not UndupeInstance.add(camNum):
            raise ValueError(f"Camera {camNum} already in use")
        self.cap = create_capture(self.settings)
        ret, frame = self.cap.read()  # test for errors
        try:
            Mat(frame)
        except Exception:
            raise ValueError(f"Unable to read picture from Camera {camNum}")

        self.latest_frame = None
        self.stop_event = Event()
        self.cap_thread = self.start_capture_thread(self.pipeline)

    Settings = get_settings()

    @dataclass
    class Outputs:
        img: Mat

    # TODO Somehow this needs to timeout, otherwise it could cause opsi to hang when trying to dispose the function
    #  object 
    def grab_frame_blocking(self):
        ret, self.latest_frame = self.cap.read()

    def frame_thread(self, pipeline):
        while not self.stop_event.is_set():
            self.grab_frame_blocking()
            pipeline.frame_ready_queue.put(self)

    def start_capture_thread(self, pipeline):
        # Minor rant: One thing that really irks me about python is that (foo) isn't a tuple but (foo,) is.
        # The fact that a trailing comma makes that difference is an enormous minor inconvenience.
        capture_thread = Thread(target=self.frame_thread, args=(pipeline,), daemon=True)
        capture_thread.start()
        return capture_thread

    def run(self, inputs):
        frame = None
        if self.cap:
            # If the camera has captured a frame since last call, return that frame.
            # Otherwise return the latest frame (which is likely a duplicate).
            if self.latest_frame is not None:
                frame = self.latest_frame
            else:
                ret, frame = self.cap.read()

            self.latest_frame = None

            frame = Mat(frame)
        return self.Outputs(img=frame)

    def dispose(self):
        # Stops the frame capturing thread
        self.stop_event.set()
        self.cap_thread.join()

        camNum = parse_cammode(self.settings.mode)[0]
        UndupeInstance.remove(camNum)


BACKEND_STRINGS = (
    ("MJPEG", "H.264 (30 FPS)", "H.264 (60 FPS)") if ENGINE_AVAIL else ("MJPEG",)
)


class CameraServer(Function):
    has_sideeffect = True
    always_restart = False
    require_restart = True

    @classmethod
    def validate_settings(cls, settings):
        settings.name = settings.name.strip()
        return settings

    def on_start(self):
        if self.settings.backend == "MJPEG":
            HookInstance.register(self)
            self.always_restart = False
            self.src = MjpegCameraServer()
        elif self.settings.backend == "H.264 (30 FPS)":
            self.always_restart = True
            self.src = H264CameraServer(self.settings.name, 30)
        elif self.settings.backend == "H.264 (60 FPS)":
            self.always_restart = True
            self.src = H264CameraServer(self.settings.name, 60)

    @dataclass
    class Settings:
        name: str = "camera"
        backend: BACKEND_STRINGS = "MJPEG"

    @dataclass
    class Inputs:
        img: Mat

    def run(self, inputs):
        self.src.run(inputs)
        if "H.264" in self.settings.backend:
            self.src.register(EngineInstance)
        return self.Outputs()

    def dispose(self):
        if self.settings.backend == "MJPEG":
            HookInstance.unregister(self)
        elif "H.264" in self.settings.backend:
            self.src.unregister(EngineInstance)
        self.src.dispose()

    # Returns a unique string for each CameraServer instance
    @property
    def id(self):
        return self.settings.name

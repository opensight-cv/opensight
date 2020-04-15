import asyncio
import logging
import threading
import time

try:
    import uvloop
except ImportError:
    pass
else:
    uvloop.install()

LOGGER = logging.getLogger(__name__)


class FifoLock:
    def __init__(self, queue):
        # if queue is None:
        #     queue = program.queue
        self.queue = queue
        self.condition = threading.Condition()

    # blocks until run() is called
    def __enter__(self):
        # equivalent to .acquire() ?
        self.condition.__enter__()

        self.queue.put(self)
        self.condition.wait()

    def __exit__(self, *exc_info):
        self.condition.notify_all()

        # equivalent to .release() ?
        self.condition.__exit__(*exc_info)

    # releases self from __enter__()
    # blocks until __exit__()
    def run(self):
        with self.condition:
            self.condition.notify_all()
            self.condition.wait()


class ThreadBase:
    def __init__(self, target, args=(), name="(unnamed)", autostart=False, **kwargs):
        self.name = name
        self.event = threading.Event()
        self._terminate = False
        self.thread = self.__make_thread__(target, args, **kwargs)
        if name:
            self.thread.__name__ = name
        if autostart:
            self.thread.start()

    def start(self):
        self.thread.start()

    def __make_thread__(self, target, args, **kwargs):
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.daemon = True
        return thread


class ShutdownThread(ThreadBase):
    def __init__(self, target, args=(), timeout=5, **kwargs):
        self.timeout = timeout
        super().__init__(target, args, **kwargs)

    def __make_thread__(self, target, args, **kwargs):
        kwargs["shutdown"] = self.event
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.daemon = True
        return thread

    def terminate(self):
        self._terminate = True

    def __stop__(self):
        timer = threading.Timer(self.timeout, self.terminate)
        timer.start()
        while self.event.is_set():
            time.sleep(0.05)
            if self._terminate:
                LOGGER.error("Failed to gracefully stop thread %s", self.name)
                return
        timer.cancel()

    def shutdown(self):
        self.event.set()
        self.__stop__()
        self.thread.join(timeout=self.timeout)
        LOGGER.debug("Closed thread %s", self.name)


class AsyncThread(ShutdownThread):
    def __init__(self, coroutine=None, **kwargs):
        self.loop = asyncio.new_event_loop()
        super().__init__(self.loop.run_forever, autostart=True, **kwargs)
        if coroutine:
            self.run_coro(coroutine)

    def __make_thread__(self, target, args):
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        return thread

    def run_coro(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def wait_for_task(self, task, timeout=3):
        start = time.monotonic()
        while True:
            if (time.monotonic() - start) >= timeout:
                return False
            if task.done() or task.cancelled():
                return True
            time.sleep(0.01)

    def __stop__(self):
        timer = threading.Timer(self.timeout, self.terminate)
        timer.start()
        for task in asyncio.all_tasks(loop=self.loop):
            if not (task.done() or task.cancelled()):
                self.wait_for_task(task)
                task.cancel()
            if self._terminate:
                LOGGER.error("Failed to gracefully stop async thread %s", self.name)
                return
        timer.cancel()

    def shutdown(self):
        self.event.set()
        self.__stop__()
        self.loop.stop()
        self.thread.join(timeout=self.timeout)
        LOGGER.debug("Closed thread %s", self.name)

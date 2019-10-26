import asyncio
import logging
import threading
import time

try:
    import uvloop
except ImportError:
    import asyncio as uvloop

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


class Snippet:
    def __init__(self):
        self.__start__ = asyncio.Event()
        self.__end__ = asyncio.Event()

    async def run(self):
        self.__start__.set()
        await self.__end__.wait()
        self.__end__.clear()

    async def start(self):
        await self.__start__.wait()
        self.__start__.clear()

    def run_abandon(self):
        self.__start__.set()

    def done(self):
        self.__end__.set()


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
    def __init__(self, target, args=(), timeout=3, **kwargs):
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
        self.loop = uvloop.new_event_loop()
        self.coros = []
        super().__init__(self.loop.run_forever, autostart=True, **kwargs)
        if coroutine:
            self.run_coro(coroutine)

    def __make_thread__(self, target, args):
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        return thread

    async def __monitor_coro__(self, coro):
        self.coros.append(coro)
        await coro
        self.coros.remove(coro)

    def run_coro(self, coro):
        asyncio.run_coroutine_threadsafe(self.__monitor_coro__(coro), self.loop)

    def __stop__(self):
        timer = threading.Timer(self.timeout, self.terminate)
        timer.start()
        # hoping that the coroutines stop themselves properly since we don't give them an event
        while self.coros:
            time.sleep(0.05)
            if self._terminate:
                LOGGER.error("Failed to gracefully stop thread %s", self.name)
                return
        timer.cancel()

    def shutdown(self):
        self.event.set()
        self.__stop__()
        self.loop.stop()
        self.thread.join(timeout=self.timeout)
        LOGGER.debug("Closed thread %s", self.name)

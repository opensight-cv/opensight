import threading


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

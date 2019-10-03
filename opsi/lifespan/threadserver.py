import logging
import threading
import asyncio
import uvicorn

LOGGER = logging.getLogger(__name__)


class ThreadedWebserver:
    def __init__(self, event, app, **kwargs):
        self.config = uvicorn.Config(app, **kwargs)
        self.server = uvicorn.Server(config=self.config)
        self.event = threading.Event()
        self.parent_event = event

        self.config.load()

    async def __run_server__(self):
        self.server.logger = self.config.logger_instance
        self.server.lifespan = self.config.lifespan_class(self.config)

        self.server.logger.info("Started server process")
        await self.server.startup()
        await self.server.main_loop()
        await self.server.shutdown()
        self.event.set()
        self.server.logger.info("Finished server process")

    async def run(self):
        # run webserver until shutdown event
        asyncio.run_coroutine_threadsafe(
            self.__run_server__(), asyncio.get_event_loop()
        )
        while not self.parent_event.is_set():
            await asyncio.sleep(0.1)

        # wait until server stops gracefully before stopping loop
        self.server.should_exit = True
        while not self.event.is_set():
            await asyncio.sleep(0.1)
        asyncio.get_event_loop().stop()

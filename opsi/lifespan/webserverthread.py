import asyncio
import logging
import threading

import uvicorn
from uvicorn.main import logger

from opsi.util.concurrency import AsyncThread

LOGGER = logging.getLogger(__name__)


class WebserverThread(AsyncThread):
    def __init__(self, app, **kwargs):
        self.event = threading.Event()
        self.config = uvicorn.Config(app, **kwargs)
        self.server = uvicorn.Server(config=self.config)
        self.config.load()

        super().__init__(coroutine=self.run(), name="Webserver thread")

    async def __run_server__(self):
        self.server.lifespan = self.config.lifespan_class(self.config)

        logger.info("Started server process")
        await self.server.startup()
        await self.server.main_loop()

    async def run(self):
        # run webserver until shutdown event
        asyncio.run_coroutine_threadsafe(
            self.__run_server__(), asyncio.get_event_loop()
        )
        while not self.event.is_set():
            await asyncio.sleep(0.1)

        # semi-gracefully shut down server
        # close all connections, however make sure that everything like lifespan is gracefully shutdown
        self.server.should_exit = True
        self.server.force_exit = True
        await self.server.shutdown()
        await self.server.lifespan.shutdown()
        asyncio.get_event_loop().stop()

        self.event.clear()

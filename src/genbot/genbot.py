import discord
from discord.ext import commands
from typing import Optional
from genbot.feed_queue import FeedQueue
from multiprocessing import Process
import asyncio

class Genbot(discord.Bot):
    def __init__(self, 
                 intents: Optional[discord.Intents] = None,
                 ):

        super().__init__(intents=intents)
        self._feed_queue = FeedQueue()
        self._processes = []


    def worker(self):
        pass

    def consume(self, min_size=1, max_size=1):
        return self._feed_queue.consume(min_size=min_size,
                                        max_size=max_size)

    async def enqueue(self, data_callback):
        return await self._feed_queue.enqueue(data_callback)

    async def on_message(self, message: discord.Message):
        pass

    def run(self, *args, workers=1, **kwargs):
        self._processes = []
        for _ in range(workers):
            p = Process(target=self.worker)
            p.start()
            self._processes.append(p)

        super().run(*args, **kwargs)

    async def close(self):
        for p in self._processes:
            p.terminate()

        await asyncio.sleep(3)

        for p in self._processes:
            if p.is_alive():
                p.kill()

        self._processes = []

        await super().close()

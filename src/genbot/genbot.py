import discord
from discord.ext import commands
from typing import Optional
from genbot.feed_queue import FeedQueue
from multiprocessing import Process

class Genbot(discord.Bot):
    def __init__(self, 
                 intents: Optional[discord.Intents] = None,
                 ):

        super().__init__(intents=intents)
        self._feed_queue = FeedQueue()
        self._processes = None


    def worker(self):
        pass

    def consume(self, min_size=1, max_size=1):
        return self._feed_queue.consume(min_size=min_size,
                                        max_size=max_size)

    async def enqueue(self, data_callback):
        async for response in self._feed_queue.enqueue(data_callback):
            yield response

    async def on_message(self, message: discord.Message):
        pass

    def run(self, *args, workers=1, **kwargs):
        self._processes = []
        for _ in range(workers):
            p = Process(target=self.worker)
            p.start()
            self._processes.append(p)

        super().run(*args, **kwargs)

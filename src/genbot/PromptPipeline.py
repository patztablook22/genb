import multiprocessing
import threading
import time
from queue import Queue
from typing import Any
import asyncio
import discord

class PromptPipeline:
    def __init__(self, 
                 batch_size_min: int = 1, 
                 batch_size_max: int = 0,
                 ):
        self._input_queue = []
        self._output_queue = []
        self._input_id_counter = 0
        self._output_id_counter = 0
        self.batch_size_min = batch_size_min
        self.batch_size_max = batch_size_max
        self._loop = True
        self._worker_thread = threading.Thread(target=self._worker)
        self._worker_thread.start()

    async def __call__(self,
                       channel: discord.TextChannel,
                       user: discord.User):
        prompt = await self.create_prompt(channel, user)
        if prompt is None:
            return

        async with channel.typing():
            output = await self.to_process(prompt)
            if output is None:
                return
            postprocessed = await self.postprocess(channel, user, prompt, output)
            if postprocessed is None:
                return
            await channel.send(postprocessed)

    async def create_prompt(self,
                            channel: discord.TextChannel,
                            user: discord.User):
        raise NotImplementedError

    def process(self, prompts: list) -> list:
        raise NotImplementedError

    async def postprocess(self, channel, user, prompt, output) -> str:
        raise NotImplementedError

    def __del__(self):
        self._loop = False
        while self._worker_thread.is_alive():
            self._worker_thread.join(5)

    def _worker(self):
        while self._loop:
            time.sleep(0.1)
            if len(self._input_queue) < self.batch_size_min:
                continue

            bsize = self.batch_size_max if self.batch_size_max > 0 else len(self._input_queue)
            inputs =  self._input_queue[:bsize]
            self._input_queue = self._input_queue[bsize:]

            try:
                outputs = list(self.process(inputs))
                if len(outputs) != len(inputs):
                    raise ValueError("batch size of output is not equal to input")
                self._output_queue += outputs
                # print("outputs", self._output_queue)
            except Exception as e:
                print(e)
                self._output_queue += [None] * len(inputs)

    def _enqueue(self, feed):
        self._input_queue.append(feed)
        id = self._input_id_counter
        self._input_id_counter += 1
        return id

    async def to_process(self, feed):
        id = self._enqueue(feed)
        while True:
            await asyncio.sleep(0.2)
            if self._output_queue and self._output_id_counter == id:
                break
            if not self._worker_thread.is_alive():
                raise RuntimeError("Batch worker is dead.")

        output = self._output_queue.pop(0)
        self._output_id_counter += 1
        return output


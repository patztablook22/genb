import discord
import asyncio
from queue import Queue
from genbot.JobWindow import JobWindow


class JobContext:

    def __init__(self, job_name: str, job_id: int, app_context: discord.ApplicationContext):
        self.app_context = app_context
        self.job_name = job_name
        self.job_id = job_id
        self.windows = []
        self._finished = False
        self._await_queue = Queue()

    async def _setup(self):
        await self.app_context.respond('Starting new job...')

    async def _update(self):
        while not self._await_queue.empty():
            awaitable, callback = self._await_queue.get()
            output = await awaitable
            if callback is not None:
                callback(output)

        for w in self.windows:
            await w._update()

    async def _update_loop(self):
        while not self._finished:
            await self._update()
            await asyncio.sleep(1)
        await self._update()

    def _close(self):
        for w in self.windows:
            w.close()

        self._finished = True

    def window(self, min_lines=0, frozen=False):
        w = JobWindow(app_context=self.app_context,
                      job_name=self.job_name,
                      job_id=self.job_id,
                      min_lines=min_lines,
                      frozen=frozen)
        self.windows.append(w)
        return w

    def async_call(self, awaitable, callback = None):
        self._await_queue.put((awaitable, callback))


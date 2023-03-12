import discord
import asyncio
from genbot.JobWindow import JobWindow


class JobContext:

    def __init__(self, job_name: str, job_id: str, application_context: discord.ApplicationContext):
        self.application_context = application_context
        self.job_name = job_name
        self.job_id = job_id
        self.windows = []
        self._finished = False

    async def _setup(self):
        await self.application_context.respond('Starting new job...')

    async def _update(self):
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
        w = JobWindow(application_context=self.application_context,
                      job_name=self.job_name,
                      job_id=self.job_id,
                      min_lines=min_lines,
                      frozen=frozen)
        self.windows.append(w)
        return w


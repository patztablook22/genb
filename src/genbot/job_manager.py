from genbot.base_unit_manager import BaseUnitManager, BaseUnit, BaseUnitBuilder, RecursiveBaseUnitBuilder
from types import ModuleType
from typing import Any, Callable, Optional, Awaitable
from dataclasses import dataclass
import discord
import warnings
import inspect
from genbot.JobContext import JobContext
import threading
import asyncio
import importlib

@dataclass
class JobUnit(BaseUnit):
    function: Callable

class RecursiveJobUnitBuilder(RecursiveBaseUnitBuilder):

    def from_module(self, module, units, level):
        importlib.reload(module)
        for objname in dir(module):
            obj = getattr(module, objname)
            if isinstance(obj, JobUnit):
                assert obj.name
                if obj.name in units:
                    warnings.warn(f'redefinition of job {obj.name}')
                units[obj.name] = obj

    def from_dict(self, d, units, level):
        function = d['payload']
        name = d.get('name', function.__name__)
        description = d.get('description', function.__doc__)
        default = d.get('default', False)
        if not description:
            description = ''

        if name in units:
            warnings.warn(f'redefinition of job {name}')

        units[name] = JobUnit(name=name,
                              description=description,
                              function=function)

    def from_payload(self, payload, units, level):
        if payload is None:
            return

        if isinstance(payload, JobUnit):
            if payload.name in units:
                warnings.warn(f'redefinition of job {payload.name}')
            units[payload.name] = payload
            return

        name = payload.__name__
        description = payload.__doc__
        if not description:
            description = ''

        if name in units:
            warnings.warn(f'redefinition of job {name}')

        units[name] = JobUnit(name=name,
                              description=description,
                              function=function)


class JobManager(BaseUnitManager):
    def __init__(self, jobs: Any):
        super().__init__(source=jobs,
                         builder=RecursiveJobUnitBuilder())
        self.active_jobs = []
        self.id_counter = 0

    async def start(self, 
                    function: Callable,
                    job_name: str,
                    app_context: Optional[discord.ApplicationContext]):

        job_id = self.id_counter
        self.id_counter += 1
        ctx = JobContext(job_name=job_name,
                         job_id=job_id,
                         app_context=app_context)

        await ctx._setup()

        def worker():
            nonlocal function, ctx
            function(ctx)
            ctx._close()

        thread = threading.Thread(target=worker)
        thread.start()
        await ctx._update_loop()

    async def list_job(self, ctx):
        assert self._genbot

        def worker(ctx):
            nonlocal self
            w = ctx.window(frozen=True)

            if not self.units:
                w.write('No plugged jobs found.')
                return

            self.reload()
            for unit in self.units.values():
                w.write(unit.name)
                formatted = '\n'.join(
                        [line.strip() for line in unit.description.splitlines()])
                w.write(formatted, prefix='   | ')
                w.write()

        await self._genbot.jobs.start(function=worker,
                                      job_name='List plugged jobs',
                                      app_context=ctx)

    async def status_job(self, ctx):
        assert self._genbot

        def worker(ctx):
            nonlocal self

            w = ctx.window()
            w.write('jbos idk')

        await self._genbot.jobs.start(function=worker,
                                      job_name='Job status',
                                      app_context=ctx)

    def setup(self, genbot):
        self._genbot = genbot
        group = genbot.create_group('job', 'Controls jobs')

        @group.command(description='Starts a new job')
        async def start(ctx, name: str, id: Optional[str] = None):
            if name not in self.units:
                await ctx.respond(f'No such job: {name}')
                return

            unit = self.units[name]
            assert isinstance(unit, JobUnit)
            await self.start(function=unit.function,
                             job_name=unit.name,
                             app_context=ctx)

        @group.command(description='Stops a job')
        async def stop(ctx, id: str):
            return

        @group.command(description='Sends a text input to a jobs')
        async def input(ctx, id: str, input: str):
            return

        @group.command(description='Shows job status')
        async def status(ctx, id: Optional[str]):
            await self.status_job(ctx)

        @group.command(description='Reloads jobs')
        async def reload(ctx, id: Optional[str]):
            await ctx.respond('Reloading jobs...')
            try:
                self.reload()
                await ctx.send_followup('Done.')
            except:
                await ctx.send_followup('Failed.')

        @group.command(description='Lists available jobs')
        async def list(ctx):
            await self.list_job(ctx)

        @group.error
        async def on_error(ctx, error):
            await ctx.respond('Permission not granted.')

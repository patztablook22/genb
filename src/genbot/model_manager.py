from genbot.base_unit_manager import BaseUnitManager, BaseUnit, BaseUnitBuilder, RecursiveBaseUnitBuilder
from types import ModuleType
from typing import Any, Callable, Optional, Awaitable
from dataclasses import dataclass
from genbot.JobContext import JobContext
import discord
import warnings
import inspect
import importlib

@dataclass
class ModelUnit(BaseUnit):
    constructor: Callable
    default: bool

class RecursiveModelUnitBuilder(RecursiveBaseUnitBuilder):

    def from_module(self, module, units, level):
        importlib.reload(module)
        for objname in dir(module):
            obj = getattr(module, objname)
            if isinstance(obj, ModelUnit):
                assert obj.name
                if obj.name in units:
                    warnings.warn(f'redefinition of model {obj.name}')
                units[obj.name] = obj

    def from_dict(self, d, units, level):
        constructor = d['payload']
        name = d.get('name', constructor.__name__)
        description = d.get('description', constructor.__doc__)
        default = d.get('default', False)
        if not description:
            description = ''

        if name in units:
            warnings.warn(f'redefinition of model {name}')

        units[name] = ModelUnit(name=name,
                                description=description,
                                default=default,
                                constructor=constructor)
    def from_payload(self, payload, units, level):
        if payload is None:
            return

        if isinstance(payload, ModelUnit):
            if payload.name in units:
                warnings.warn(f'redefinition of model {payload.name}')
            units[payload.name] = payload
            return

        name = payload.__name__
        description = payload.__doc__
        if not description:
            description = ''

        if name in units:
            warnings.warn(f'redefinition of model {name}')

        if level == 0:
            def payload_intermediate():
                return payload

            units[name] = ModelUnit(name=name,
                                    description=description,
                                    default=True,
                                    constructor=payload_intermediate)
        else:
            units[name] = ModelUnit(name=name,
                                    description=description,
                                    default=False,
                                    constructor=payload)


class ModelManager(BaseUnitManager):
    def __init__(self, models: Any):
        super().__init__(source=models, 
                         builder=RecursiveModelUnitBuilder())

        self._active_unit = None
        self._active_pipeline = None
        self._genbot = None

    async def __call__(self, message: discord.Message):
        a = message.channel
        assert self._genbot
        if self.active_pipeline:
            output = self.active_pipeline(message.channel, self._genbot.user)
            if output is not None and inspect.isawaitable(output):
                output = await output
            if output is not None:
                await message.channel.send(str(output))

    @property
    def active_unit(self):
        return self._active_unit

    @property
    def active_pipeline(self):
        return self._active_pipeline

    def unload(self):
        assert self._genbot

        if not self.active_unit:
            raise RuntimeError("No module is currently loaded.")

        del self._active_pipeline
        self._active_pipeline = None
        self._active_unit = None

    def load(self, unit: ModelUnit):
        assert self._genbot

        if self.active_unit:
            self.unload()

        pipeline = unit.constructor()

        if not pipeline:
            raise ValueError("Constructed pipeline is None.")

        self._active_unit = unit
        self._active_pipeline = pipeline

    async def load_job(self, ctx, name):
        assert self._genbot

        def worker(ctx):
            nonlocal self, name
            self.reload()

            w = ctx.window()
            if name not in self.units:
                w.error('Model not found:', name)
                return

            unit = self.units[name]
            assert isinstance(unit, ModelUnit)

            try:
                if self.active_unit:
                    w.write('Unloading', self.active_unit.name, ...)
                    self.unload()

                ctx.async_call(self._genbot.change_presence(
                    activity=None,
                    status=None
                ))

                w.write('Loading', name, ...)

                self.load(unit)

                w.write('Done.', prefix='+')

                if isinstance(self._source , list) or \
                        isinstance(self._source, dict) or \
                        isinstance(self._source, ModuleType) or \
                        isinstance(self._source, ModelUnit) or \
                        isinstance(self._source, ModelManager):
                    game_name = name
                else:
                    game_name = 'with language'

                ctx.async_call(self._genbot.change_presence(
                    activity=discord.Game(name=game_name),
                    status=discord.Status.online
                ))

            except Exception as e:
                w.error(str(e))

        await self._genbot.jobs.start(function=worker,
                                      job_name='Load model',
                                      app_context=ctx)

    async def unload_job(self, ctx):
        assert self._genbot

        def worker(ctx):
            nonlocal self

            w = ctx.window()
            if not self.active_unit:
                w.error('No model loaded.')
                return

            w.write('Unloading', self.active_unit.name, ...)

            try:
                self.unload()

                w.write('Done.', prefix='+')

                ctx.async_call(self._genbot.change_presence(
                    activity=None,
                    status=None
                ))
            except Exception as e:
                w.error(str(e))


        await self._genbot.jobs.start(function=worker,
                                      job_name='Unload model',
                                      app_context=ctx)

    async def list_job(self, ctx):
        assert self._genbot

        def worker(ctx):
            nonlocal self
            w = ctx.window(frozen=True)

            self.reload()

            if not self.units:
                w.write('No models found.')
                return

            for unit in self.units.values():
                w.write(unit.name)
                formatted = '\n'.join(
                        [line.strip() for line in unit.description.splitlines()])
                w.write(formatted, prefix='   | ')
                w.write()

        await self._genbot.jobs.start(function=worker,
                                      job_name='List models',
                                      app_context=ctx)

    async def status_job(self, ctx):
        assert self._genbot

        def worker(ctx):
            nonlocal self

            w = ctx.window()
            if not self.active_unit:
                w.write('No model is currently loaded.')
                return

            w.write('Serving', self.active_unit.name)
            w.write(self.active_unit.description, prefix='  - ')

        await self._genbot.jobs.start(function=worker,
                                      job_name='Model status',
                                      app_context=ctx)

    @property
    def default_unit(self) -> Optional[ModelUnit]:
        default = None
        for unit in self._units.values():
            assert isinstance(unit, ModelUnit)
            if unit.default:
                if default:
                    raise RuntimeWarning('multiple model units are declared as default')
                default = unit

        return default

    async def on_ready(self):
        if not self.default_unit:
            return

        await self.load_job(None, self.default_unit.name)

    def setup(self, genbot):
        self._genbot = genbot

        group = genbot.create_group('model', 'Controls the underlying language model')

        @group.command(description='Loads given model')
        async def load(ctx, name: str):
            await self.load_job(ctx, name)

        @group.command(description='Reloads current model')
        async def reload(ctx):
            if not self.active_unit:
                await ctx.respond("No model is currently loaded.")
                return
            await self.load_job(ctx, self.active_unit.name)

        @group.command(description='Unloads the model')
        async def unload(ctx):
            await self.unload_job(ctx)

        @group.command(description='Shows model information')
        async def status(ctx):
            await self.status_job(ctx)

        @group.command(description='Lists available models')
        async def list(ctx):
            await self.list_job(ctx)

        @group.error
        async def on_error(ctx, error):
            await ctx.respond('Permission not granted.')

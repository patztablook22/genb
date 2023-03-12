from genbot.base_unit_manager import BaseUnitManager, BaseUnit, BaseUnitBuilder, RecursiveBaseUnitBuilder
from types import ModuleType
from typing import Any, Callable, Optional, Awaitable
from dataclasses import dataclass
import discord
import warnings
import inspect

@dataclass
class ModelUnit(BaseUnit):
    constructor: Callable
    default: bool

class RecursiveModelUnitBuilder(RecursiveBaseUnitBuilder):

    def from_module(self, module, units, level):
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
        if self.active_pipeline:
            output = self.active_pipeline(message)
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

    async def unload(self):
        assert self._genbot

        if not self.active_unit:
            return False

        del self._active_pipeline
        self._active_pipeline = None
        self._active_unit = None

        await self._genbot.change_presence(activity=None, status=None)
        return True

    async def load(self, unit: ModelUnit) -> bool:
        assert self._genbot

        if self.active_unit:
            if not self.unload():
                return False

        try:
            pipeline = unit.constructor()
        except:
            return False

        if not pipeline:
            return False

        self._active_unit = unit
        self._active_pipeline = pipeline

        await self._genbot.change_presence(
            activity=discord.Game(name=self._active_unit.name), 
            status=discord.Status.online
        )
        return True

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
        if self.default_unit:
            await self.load(self.default_unit)

    def setup(self, genbot):
        self._genbot = genbot

        group = genbot.create_group('model', 'Controls the underlying language model')

        @group.command(description='Loads given model')
        async def load(ctx, name: str):
            try:
                self.reload()
            except:
                await ctx.respond(f'Failed to reload the module.')
                return

            if name not in self.units:
                await ctx.respond(f'No such model: {name}')
                return

            if self.active_unit:
                await ctx.respond(f'Unloading {self.active_unit.name}...')
                if not await self.unload():
                    await ctx.send_followup('Failed.')
                await ctx.send_followup(f'Loading model {name}...')
            else:
                await ctx.respond(f'Loading model {name}...')

            if not await self.load(self.units[name]):
                await ctx.send_followup(f'Failed.')
                return

            await ctx.send_followup(f'Loaded.')

        @group.command(description='Unloads the model')
        async def unload(ctx):
            if not self.active_unit:
                await ctx.respond('No model is loaded.')
                return

            await ctx.respond(f'Unloading {self.active_unit.name}')
            if not await self.unload():
                await ctx.send_followup('Failed.')
                return

            await ctx.send_followup('Model unloaded.')

        @group.command(description='Shows model information')
        async def status(ctx):
            if self.active_unit:
                embed = discord.Embed(color=discord.Color.green(),
                                      title=f'Serving model {self.active_unit.name}',
                                      description=self.active_unit.description)
            else:
                embed = discord.Embed(color=discord.Color.red(),
                                      title='No model loaded')
            await ctx.respond(embed=embed)

        @group.command(description='Lists available models')
        async def list(ctx):
            self.reload()

            if not self.units:
                embed = discord.Embed(title='Available models',
                                      description='No models have been found.')
                await ctx.respond(embed=embed)
                return

            embed = discord.Embed(title='Available models')

            for unit in self.units.values():
                embed.add_field(
                    name=unit.name + \
                        (' (default)' if unit == self.default_unit else ''),
                    value=unit.description
                )

            await ctx.respond(embed=embed)

        @group.error
        async def on_error(ctx, error):
            await ctx.respond('Permission not granted.')

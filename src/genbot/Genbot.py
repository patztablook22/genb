import discord
from discord.ext import commands
from typing import Optional, Literal, Callable, Coroutine, Awaitable, Any
from types import ModuleType
from genbot.model_manager import ModelManager
from genbot.Permissions import Permissions
from genbot.TimedPresence import TimedPresence
from genbot.job_manager import JobManager
import inspect


class Genbot(discord.Bot):
    def __init__(self,
                 models: Any,
                 permissions: Callable[[discord.ApplicationContext], bool] | Permissions | dict[str, list[int]] | None = None,
                 presence: Optional[Callable[[discord.Message], bool]] = None,
                 jobs: Any = None,
                 intents: Optional[discord.Intents] = None
                 ):

        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True

        if permissions is None:
            self.permissions = Permissions([], [])
        elif isinstance(permissions, dict):
            self.permissions = Permissions(
                mods=list(permissions.get('mods', [])),
                admins=list(permissions.get('admins', []))
            )
        else:
            self.permissions = permissions

        if presence is None:
            self.presence = TimedPresence()
        else:
            self.presence = presence

        self.models = ModelManager(models)
        self.jobs = JobManager(jobs)

        super().__init__(intents=intents)

        group = self.create_group('bot', 'Controls the bot service')

        @group.command(description='Stops the bot')
        async def stop(ctx):
            await ctx.respond('Stopping...')
            await self.close()

        @group.command(description='Shows status')
        async def status(ctx):
            pass

        @group.error
        async def error_fn(ctx, error):
            await ctx.respond('Permission not granted.')

        try:
            self.permissions.setup(self)
        except AttributeError:
            pass

        try:
            self.presence.setup(self)
        except AttributeError:
            pass

        try:
            self.models.setup(self)
        except AttributeError:
            pass

        try:
            self.jobs.setup(self)
        except AttributeError:
            pass

        self.check(self.permissions)

    async def on_ready(self):
        try:
            await self.permissions.on_ready()
        except AttributeError:
            pass

        try:
            await self.presence.on_ready()
        except AttributeError:
            pass

        try:
            await self.models.on_ready()
        except AttributeError:
            pass

    async def on_message(self, message: discord.Message):
        if not self.presence(message):
            return

        await self.models(message)


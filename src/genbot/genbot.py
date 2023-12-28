import discord
from typing import Optional, Any, Union
from genbot.idlist import IdList
from genbot.context import Context


class PermissionError(discord.errors.CheckFailure): 
    def __init__(self):
        super().__init__("Permission denied.")

CommandError = discord.errors.ApplicationCommandError

MessageableChannel = Union[discord.TextChannel,
                           discord.Thread,
                           discord.DMChannel,
                           discord.GroupChannel,
                           discord.PartialMessageable]

class Genbot(discord.Bot):
    def __init__(self, 
                 admins: Optional[list | dict] = None,
                 roles: Optional[list | dict] = None,
                 users: Optional[list | dict] = None,
                 intents: Optional[discord.Intents] = None,
                 ):

        super().__init__(intents=intents)
        self.set(admins=admins,
                 roles=roles,
                 users=users)

        @self.slash_command(description="Shuts the bot down.")
        async def shutdown(ctx):
            if ctx.author.id not in self.admins: raise PermissionError()
            await ctx.respond("Bye!", ephemeral=True)
            await self.close()

        @self.slash_command(description="Pings the bot.")
        async def ping(ctx):
            await ctx.respond("Pong.", ephemeral=True)

        @self.slash_command(description="Restarts the bot.")
        async def restart(ctx):
            if ctx.author.id not in self.admins: raise PermissionError()
            await ctx.respond("Restarting...", ephemeral=True)
            #self.restart = True
            await self.close()

        @self.slash_command(description="Creates a new chatbot thread.")
        async def thread(ctx, name: str):
            if not self.can_chat(ctx.author, ctx.channel):
                raise PermissionError()

            interaction = await ctx.respond("Creating thread...")
            msg = await interaction.original_response()
            try:
                await msg.create_thread(name=name)
            except Exception as e:
                #await interaction.delete()
                raise CommandError("Could not create a thread here.")

        @self.slash_command()
        async def reset(ctx):
            if not ctx.author.id not in self.admins: raise PermissionError()
            await ctx.respond("Done.")

        permissions = self.create_group(name='permissions')


    def set(self, **kwargs):
        if 'admins' in kwargs:
            self.admins = IdList(kwargs['admins'])
        if 'roles' in kwargs:
            self.roles = IdList(kwargs['roles'])
        if 'users' in kwargs:
            self.dms = IdList(kwargs['users'])

    def is_active(self, channel: MessageableChannel):
        if isinstance(channel, (discord.Thread,
                                discord.DMChannel,
                                discord.GroupChannel)):
            return True
        return False

    def can_chat(self, user: discord.User | discord.Member, channel: MessageableChannel):
        if user.id in self.admins: return True
        if user.id in self.users: return True
        if isinstance(user, discord.Member):
            if self.roles.any([i.id for i in user.roles if i]): return True
        return False

    def has_ignore_flag(self, message: discord.Message):
        return message.content.startswith('!')

    def is_visible(self, message: discord.Message):
        assert message.author and message.channel
        return self.can_chat(message.author, message.channel) and not self.has_ignore_flag(message)

    def is_control(self, message: discord.Message):
        return self.is_reset(message)

    def is_reset(self, message: discord.Message):
        if message.author != self.user: return False
        if not hasattr(message, 'interaction') or not message.interaction: return False
        appcmd = 2 # discord.InteractionType.application_command
        if message.interaction.type != appcmd: return False
        return message.interaction.name == 'reset'

    def context(self,
                channel: Optional[MessageableChannel] = None, 
                oldest: Optional[discord.Message] = None,
                #newest: Optional[discord.Message] = None,
                limit=None):

        return Context(channel=channel,
                       #newest=newest,
                       genbot=self)

    async def attend(self, channel):
        pass

    async def on_message(self, message: discord.Message):
        if not self.is_active(message.channel) or not self.is_visible(message): return
        await self.attend(message.channel)

    async def on_application_command_error(self, ctx, error):
        await ctx.respond(str(error), ephemeral=True)

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)

    async def close(self):
        await super().close()


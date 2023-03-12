import discord
from typing import Literal

class TimedPresence:
    def __init__(self, 
                 timeout = 2*60,
                 whitelist: list[int] = [],
                 blacklist: list[int] = []): 

        self.timeout = timeout
        self.whitelist = set(whitelist)
        self.blacklist = set(blacklist)
        self._genbot = None
        self._timed_channels = {}

    def __call__(self, message: discord.Message):
        assert self._genbot
        if message.author.name == self._genbot.user: return False
        if message.author.id in self.blacklist: return False
        if message.author.id not in self.whitelist: return False

        if message.channel.type in [discord.ChannelType.private,
                                    discord.ChannelType.group]:
            return True

        channel = message.channel
        time = message.created_at

        if self._genbot.user.mention in message.content.split():
            self._timed_channels[channel] = time
            return True
        else:
            if channel not in self._timed_channels:
                return False

            seconds = (time - self._timed_channels[channel]).total_seconds()

            if seconds > self.timeout:
                del self._timed_channels[channel]
                return False

        self._timed_channels[channel] = time
        return True

    def setup(self, genbot):
        self._genbot = genbot

        group = genbot.create_group('presence', 'Controls the general model involvement')

        @group.command(description='Sets presence timeout')
        async def timeout(ctx, seconds: int):
            self.timeout = seconds
            await ctx.respond(f'Presence timeout set to {seconds} seconds.')

        @group.command(name='whitelist-add', 
                       description='Whitelists a user for presence activation')
        async def whitelist_add(ctx, user: discord.User):
            if user.id in self.whitelist:
                await ctx.respond(f'{user.name}#{user.discriminator} is already whitelisted..')
            else:
                self.whitelist.add(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} added to the whitelist.')

        @group.command(name='whitelist-remove', 
                       description='Removes a user from the whitelists for presence activation')
        async def whitelist_remove(ctx, user: discord.User):
            if user.id not in self.whitelist:
                await ctx.respond(f'{user.name}#{user.discriminator} is not whitelisted.')
            else:
                self.whitelist.remove(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} removed from the whitelist.')

        @group.command(name='blacklist-add', 
                       description='Blacklists a user for chatting activation')
        async def blacklist_add(ctx, user: discord.User):
            if user.id in self.blacklist:
                await ctx.respond(f'{user.name}#{user.discriminator} is already blacklisted.')
            else:
                self.blacklist.add(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} added to the blacklist.')
            pass

        @group.command(name='blacklist-remove', 
                       description='Removes a user from the blacklist for presence activation')
        async def blacklist_remove(ctx, user: discord.User):
            if user.id not in self.blacklist:
                await ctx.respond(f'{user.name}#{user.discriminator} is not blacklisted.')
            else:
                self.blacklist.remove(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} removed from the blacklist.')

        @group.error
        async def error_fn(ctx, error):
            await ctx.respond('Permission not granted.')




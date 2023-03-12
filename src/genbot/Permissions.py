import discord

class Permissions:
    def __init__(self,
                 mods = list[int],
                 admins = list[int]):

        self.mods = set(mods)
        self.admins = set(admins)

    def __call__(self, ctx):
        command = str(ctx.command)
        uid = ctx.author.id

        if uid in self.admins:
            return True

        admin_only = ['bot', 'permissions', 'job']
        if uid in self.mods and command not in admin_only:
            return True

        return False

    def setup(self, genbot):
        group = genbot.create_group('permissions', 'Manages command permissions')

        @group.command(description='Gives moderation permissions')
        async def promote(ctx, user: discord.User):
            if user.id in self.admins:
                await ctx.respond(f'{user.name}#{user.discriminator} is an admin.')
                return
            elif user.id in self.mods:
                await ctx.respond(f'{user.name}#{user.discriminator} is already a mod.')
                return
            else:
                self.mods.add(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} is now a mod.')

        @group.command(description='Takes away moderation permissions')
        async def demote(ctx, user: discord.User):
            if user.id in self.admins:
                await ctx.respond(f'{user.name}#{user.discriminator} is an admin.')
                return
            elif user.id not in self.mods:
                await ctx.respond(f'{user.name}#{user.discriminator} is not a mod.')
                return
            else:
                self.mods.remove(user.id)
                await ctx.respond(f'{user.name}#{user.discriminator} is no longer a mod.')

        @group.error
        async def error_fn(ctx, error):
            await ctx.respond('Permission not granted.')

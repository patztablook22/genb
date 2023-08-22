import discord

class TimedNotificationAttention:
    def __init__(self, timeout=0):
        self.timeout = timeout
        self._timed_channels = {}

    def __call__(self, genbot, message: discord.Message):
        channel = message.channel
        time = message.created_at

        if channel.type in [discord.ChannelType.private,
                            discord.ChannelType.group]:
            return True

        if genbot.user.mention in message.content.split():
            self._timed_channels[channel] = time
        else:
            if channel not in self._timed_channels:
                return False

            seconds = (time - self._timed_channels[channel]).total_seconds()

            if seconds > self.timeout:
                del self._timed_channels[channel]
                return False

        self._timed_channels[channel] = time
        return True


import discord

class Context:
    def __init__(self,
                 genbot,
                 channel = None, 
                 oldest = None,
                 #newest: Optional[discord.Message] = None,
                 limit=None,
                ):
        self._genbot = genbot
        self._cache = None
        self._iterator = None
        self._limit = limit
        self._n = 0

        if oldest is not None:
            if channel is not None: assert oldest.channel == channel
            channel = oldest.channel

        newest = None
        if newest is not None:
            if channel is not None: assert newest.channel == channel
            channel = newest.channel

        if channel is None:
            raise ValueError("No argument with a discord.Channel provided.")

        self._channel = channel

    def __nonzero__(self):
        return True if self._cache else False

    def can_chat(self, user):
        return self._genbot.can_chat(user, self._channel)

    def __getitem__(self, idx):
        if self._cache is None: raise RuntimeError("Context not invoked yet.")
        return self._cache[idx]

    def __aiter__(self):
        self._iterator = self._channel.history() \
                                      .filter(self.is_relevant)
        self._cache = []
        self._n = 0
        return self

    async def __anext__(self):
        if self._cache is None: raise RuntimeError("Context not invoked yet.")
        assert self._iterator is not None and self._n is not None
        self._n += 1
        if self._limit is not None and self._n >= self._limit: raise StopAsyncIteration
        m = await self._iterator.__anext__()
        if self.is_reset(m): raise StopAsyncIteration
        self._cache.append(m)
        return m

    def is_reset(self, message: discord.Message):
        return self._genbot.is_reset(message)

    def is_control(self, message: discord.Message):
        return self._genbot.is_control(message)

    def is_visible(self, message: discord.Message):
        return self._genbot.is_visible(message)

    def is_relevant(self, message: discord.Message):
        return self._genbot.is_visible(message) or self._genbot.is_control(message)

    async def current(self):
        if self._cache is None: raise RuntimeError("Context not invoked yet.")
        history = self._channel.history() \
                               .filter(self.is_relevant)
        async for m in history:
            if self.is_reset(m): return True
            if len(self._cache) == 0 or m.id != self._cache[0].id: return False
            return True

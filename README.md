# Genbot

Generative LM deployment for Discord.
 
## Installation

In shell, run:
```sh
pip install git+https://github.com/patztablook22/genbot
```

Alternatively, specify the package in `requirements.txt` simply as:
```txt
git+https://github.com/patztablook22/genbot
```

## Documentation

The focal point is the `genbot.Genbot` class. To implement how the chatbot reacts to messages, you should override its async `attend(channel)` method:

```py
import genbot

class MyBot(discord.Genbot):
  async def attend(self, channel):
    await channel.send("Hello World!")

token = ...
bot = MyBot()
bot.run(token)
```

The bot will then automatically detect new messages in channels that should be attended to and invokes the function. 

This can be configured by specifying `users` and `roles` (by their unique IDs). A person can then chat with the bot anywhere 
if he is in `users` or in selected servers where he has some satisfying role in `roles`. Both of these parameters can be specified either as 
- `list` - the whitelist
- `dict` - keys `whitelist` and `blacklist`

By default, all users and roles are allowed.

The same format can be used to specify `admins` (empty by default), i.e. users who can manage the bot runtime (e.g. shut it down):

```py
# will be interpreted as a whitelist - users that can chat with the bot anywhere, even DMs
users = [4567898765678987, 5678987656789, 67897678329876]

# this time, let's just create some blacklisted roles
roles = {'blacklist': [12345678987653, 98765678987112]}

# we don't want many people shutting our bot down, so let's whitelist just one
admins = [09876789656789]

bot = MyBot(users=users, roles=roles, admins=admins)
```

### Streaming

In practice, the process of generating the response will be very complicated and may be quite slow. For this reason, you may want to move it from the `attend` method to some other place, possibly running in a different process. Otherwise it may be very unreliable and the bot may stop responding altogether, since the attend function would be blocking the entire async thread.

Streaming is an elegant way of asynchronously batching inputs to a central worker and distributing the outputs back to the asynchronous callers:

```py
stremaer = ...

class MyBot(genbot.Genbot):
  async def attend(self, channel):
    with streamer.stream() as stream:    # waits in queue for a free stream slot
      inputs = "some input data"         # now that it is our turn, we create the inputs
      for outputs in stream(inputs):
        await channel.send(outputs)      # and collect the outputs in real time
```

To create a streamer, either subclass `genbot.Streamer` by overriding its `worker` method. Use its `consume(minimum=1, maximum=1)` method to wait for the number of open streams you need, each one containing the input `data`. Use the stream's `write` and `close` methods to communicate with the other end:

```py
class MyStreamer(genbot.Streamer):
  def worker(self):
    while True:
      streams = self.consume(minimum=1, maximum=64)
      for stream in streams:
        stream.write(f"Pong: {stream.data}")
        stream.close()
```

Now you can instantiate the streamer and run the worker manually or using some out-of-the-box helper methods, e.g.:

```py
streamer = MyStreamer()
process = streamer.start_process()
```

Usually, the worker is just some loop that consumes the waiting input streams, and generates the outputs in some batched way. For this use, you may want to use the following alternative:
```py
@genbot.streamer
def streamer(streams):
  for stream in streams:
    stream.write(f"Pong: {stream.data}")
    stream.close()

process = streamer.start_process(minimum=1, maximum=64)
```

### Gatekeeping

While using discord, you often write multiple short messages instead of long walls of texts. This often necessitates not attending to channels based on individual messages. Moreover, there already may be a different asynchronous `attend` to the same channel and it may take care of that message too.

The `@genbot.gatekeep` decorator prevents more than one instance of the decorated function running in parallel. If the function is already running with the same arguments, it just returns. If the function is not running, it asyncrhonously schedules it. This can be overriden by passing `force=True`, which schedules the function even if already scheduled:

```py
class MyBot(genbot.Genbot):
  @genbot.gatekeep
  async def attend(self, channel):
    # attend to the channel for 30 seconds and then ignore it
    ...

```

### Context window

The `Genbot` method `context(channel, limit)` returns `discord.Context`. It is a context window wrapper that integrates the bot's configuration (e.g. permitted users and roles) and various controls (such as `/reset`). It works as an efficient _anti_ chronological (recent messages first) iterator with extra caching:

```py
class MyBot(genbot.Genbot):
  async def attend(self, channel):
    buffer = []
    async for msg in self.context(channel, limit=16):
      buffer.append(f"{msg.author.name}: {msg.content}")

    inputs = '\n'.join(buffer[::-1])
    ...
```

While iterating over the messages, the `genbot.Context` is caching everything. This allows it to also provide some additional functionality:

- `ctx[idx]` - access the cache, e.g. `ctx[0]` for the most recent message
- `if ctx: ...` - the cache (i.e. the context window) is non-empty
- `ctx.current()` - there are no new messages relevant for the current context

An example use may look like this:
```py
class MyBot(genbot.Genbot):
  @genbot.Genbot
  async def attend(self, channel):
    buffer = []
    async for msg in (ctx := self.context(channel, limit=16)):
      buffer.append(f"{msg.author.name}: {msg.content}")

    if not ctx: return
    # the generation of the response may take some time
    ...
    if not ctx.current():
      self.attend(channel, force=True)  # schedule the whole thing again if there were important updates to the context while generating
```

### Putting everything together

```py
# Define the streamer;
# it could be e.g. GPT-3, here we do just some statistic.

@genbot.streamer
def echo(streams):
  for _ in range(2):
    time.sleep(1)
    for stream in streams:
      stream.write(f"Echo {len(stream.data)}")
  for stream in streams:
    stream.close()

class MyBot(genbot.Genbot):

  # We will gatekeep the attend, i.e. only one attend per channel will be running at any one time.
  @genbot.gatekeep
  async def attend(self, channel):
    # Wait in queue for the streamer.
    async with echo.stream() as stream:
      # It's our turn, so let's create somee inputs and call it.
      buff = []
      async for msg in (ctx := self.context(channel):
        buff.append(f"{msg.author.name}: {msg.content}")

      for data in stream('\n'.join(buff[::-1])):
        # Send the stream output (our Echo context_length) as a message.
        await channel.send(data)

      # If new messages appeared while we were generating ours, more work has to be done.
      if not await ctx.current():
        await self.attend(channel)
```

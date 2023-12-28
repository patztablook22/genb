# Genbot

Generative LM deployment for Discord.
 
## Installation

Run

```sh
pip install git+https://github.com/patztablook22/genbot
```

## Documentation

The focal point is the `genbot.Genbot` class. To implement how the chatbot reacts to messages, you should override its `attend(self, channel)` method:

```py
import genbot

class MyBot(discord.Genbot):
  def attend(self, channel):
    await channel.send("Hello World!")

token = ...
bot = MyBot()
bot.run(token)
```

The bot will then automatically detect new messages in channels that should be attended to and invokes the function. This can be configured by specifying `users` and `roles` (by their unique IDs). A person can then chat with the bot anywhere 
if he is in `users` or in selected servers where he has some satisfying role in `roles`. Both of these parameters can either whitelists or dicts with `'whitelist'` and `'blacklist'` keys. The same format can be used to specify `admins`, i.e. users who can manage the bot runtime (e.g. shut it down):

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
  def attend(self, channel):
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

### Context window


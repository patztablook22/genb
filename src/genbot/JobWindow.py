from dataclasses import dataclass
import discord
from typing import Optional

BLANK = '‏‏‎ ‎'
PROMPT = '➜'

class Write:
    def __init__(self,
                 message,
                 prefix = None):

        self.prefix = prefix
        if message and message[-1] is ...:
            self.ellipsis = True
            self.lines = (' '.join(message[:-1]) + '...').splitlines()

        else:
            self.ellipsis = False
            self.lines = ' '.join(message).splitlines()

    def build_string(self, prompt: bool):
        if self.prefix:
            p = self.prefix.ljust(2)
        elif prompt:
            p = PROMPT.ljust(2)
        else:
            p = '  '

        return p + f'\n{p}'.join(self.lines)

class JobWindow:

    def __init__(self,
                 app_context: Optional[discord.ApplicationContext],
                 job_name: str,
                 job_id: int,
                 min_lines: int = 0,
                 frozen: bool = False,
                 ):

        self.app_context = app_context

        self.min_lines = min_lines
        self.frozen = frozen

        self.job_name = job_name
        self.job_id = job_id

        self._writes = []
        self._message = None
        self._version = 0
        self._last_update = 0
        self._closed = False

    def _build_output_string(self):
        prefix = f'```diff\n*** {self.job_name.capitalize()} (job ID: {self.job_id}) ***\n\n'
        postfix = '\n```'
        texts = []
        lines = 0
        for i,w in enumerate(self._writes):
            lines += len(w.lines)
            prompt = i == len(self._writes) - 1 and not self._closed
            texts.append(w.build_string(prompt))

        if not texts:
            if self._closed:
                texts = ['']
            else:
                texts = [PROMPT]
            lines = 1

        return prefix + '\n'.join(texts) \
                + (BLANK + '\n') * (self.min_lines - lines) + postfix

    async def _update(self):
        if self._version == self._last_update or self.frozen:
            return

        if self.app_context:
            if self._message is None:
                self._message = await self.app_context.interaction.original_response()

            await self._message.edit(content=self._build_output_string())
            self._last_update = self._version

    def close(self):
        if self._writes:
            prev = self._writes[-1]
            if prev.ellipsis and prev.prefix is None:
                prev.prefix = '+'

        self.frozen = False
        self._closed = True
        self._version += 1

    def write(self, *message, prefix=None):
        if self._writes:
            prev = self._writes[-1]
            if prev.ellipsis and prev.prefix is None:
                prev.prefix = '+'

        write = Write(message, prefix=prefix)
        self._writes.append(write)
        self._version += 1

    def error(self, *message):
        if self._writes:
            prev = self._writes[-1]
            if prev.ellipsis and prev.prefix is None:
                prev.prefix = '-'
            prefix = '-   '
        else:
            prefix = '-'

        if message:
            self.write(*message, prefix=prefix)
        else:
            self._version += 1

    def rewrite(self, *message, prefix=None):
        if not self._writes:
            return self.write(*message, prefix=prefix)

        write = Write(message, prefix=prefix)
        self._writes[-1] = write
        self._version += 1

    def clear(self):
        self._writes.clear()
        self._version += 1


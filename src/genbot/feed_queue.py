from multiprocessing import Queue, Pipe
from queue import Empty
import asyncio
import inspect

class TurnHandler:
    def __init__(self, conn, ):
        self.closed = False
        self._conn = conn
        self._buff = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        req = await self._read()
        if self.closed: raise StopAsyncIteration
        return req[1]

    async def _peek(self):
        if self._buff is None:
            self._buff = await self._read()
        return self._buff

    async def _read(self):
        if self._buff is not None:
            buff = self._buff
            self._buff = None
            return buff

        try:
            while True:
                if self._conn.closed: return
                await asyncio.sleep(0.1)
                if self._conn.poll(): break

            data = self._conn.recv()
            if data[0] == 'close':
                self._conn.close()
                self.closed = True
                return None

            return data
        except EOFError:
            self.closed = True
            return None

    async def _send(self, data):
        try:
            self._conn.send(data)
        except EOFError:
            return


class ResponseHandler:
    def __init__(self, conn):
        self._conn = conn

    def get_data(self):
        self._conn.send(('get_data',))
        return self._conn.recv()

    def write(self, data):
        self._conn.send(('write', data))

    def wait(self):
        self._conn.send(('wait',))

    def close(self):
        self._conn.send(('close',))
        self._conn.close()

class FeedQueue:
    def __init__(self):
        self._queue = Queue()

    def consume(self, min_size, max_size):
        batch = []
        for _ in range(min_size):
            batch.append(self._queue.get(block=True))
        for _ in range(max_size - min_size):
            try:
                batch.append(self._queue.get(block=False))
            except Empty:
                break
        return batch

    async def enqueue(self, data_callback):
        conn1, conn2 = Pipe()
        turn = TurnHandler(conn1)

        self._queue.put(ResponseHandler(conn2))
        req = await turn._peek()
        if req[0] == 'get_data':
            await turn._read()
            data = data_callback()
            if data is not None and inspect.isawaitable(data):
                data = await data
            await turn._send(data)

        p = await turn._peek()
        if p is not None and p[0] == 'wait':
            await turn._read()
        return turn


from multiprocessing import Queue, Pipe
from queue import Empty
import asyncio
import inspect

class ResponseHandler:
    def __init__(self, conn):
        self._conn = conn

    def get_data(self):
        self._conn.send(('get_data',))
        return self._conn.recv()

    def write(self, data):
        self._conn.send(('write', data))

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


        self._queue.put(ResponseHandler(conn2))

        try:
            while True:
                if conn1.closed: break
                if not conn1.poll(timeout=0.5): continue

                req = conn1.recv()
                func = req[0]
                if func == 'get_data':
                    data = data_callback()
                    if data is not None and inspect.isawaitable(data):
                        data = await data

                    conn1.send(data)
                elif func == 'write':
                    yield req[1]
                elif func == 'close':
                    conn1.close()
                    break
                else:
                    raise RuntimeError

        except EOFError:
            pass


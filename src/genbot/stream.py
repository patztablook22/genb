import asyncio
import queue
import multiprocessing
import threading
import time


class Timer:
    def __init__(self):
        self.start = time.time()
        self.events = []

    def __call__(self, name):
        self.events.append((time.time(), name))

    def __repr__(self):
        buff = "\nTimer\n" + '=' * 64 + '\n'
        for time, name in self.events:
            diff = time - self.start
            buff += f"{diff:.3f}".rjust(10) + f" {name}\n"
        return buff

class StreamResponseHandler:
    def __init__(self, pipe, timer=None):
        self._pipe = pipe
        self._timer = timer

    def __aiter__(self):
        return self

    async def __anext__(self):
        data = None
        try:
            data = self._pipe.recv()
            if self._timer: self._timer(f"__anext__ {data}")
            if not data: raise EOFError
        except (OSError, EOFError, BrokenPipeError) as e:
            if self._timer: self._timer(f"__anext__ {e}")
            raise StopAsyncIteration

        if data[0] == 'write': return data[1]
        elif data[0] == 'close': 
            self._pipe.close()
            raise StopAsyncIteration
        else: raise RuntimeError(f"Unexpected action while awaiting a response from the worker: {data[0]}")

class StreamTarget:
    def __init__(self, id, pipe, timer=None):
        self._id = id
        self._turn = asyncio.Event()
        self._pipe = pipe
        self._timer = timer

    async def __aenter__(self):
        while True:
            if self._turn.is_set(): break
            await asyncio.sleep(0.05)
        if self._timer: self._timer('self._turn.wait() after')
        return self

    async def __aexit__(self, *args):
        if self._timer: self._timer('StreamTarget.__aexit__() begin')
        try:
            self._pipe.send(('close',))
            self._pipe.close()
        except (OSError, EOFError, BrokenPipeError) as e:
            pass
        if self._timer: self._timer('StreamTarget.__aexit__() end')
        if self._timer: print(self._timer)

    def __call__(self, data):
        self._pipe.send(('call', data))
        if self._timer: self._timer("self._pipe.send(('call', data)) after")
        return StreamResponseHandler(self._pipe, timer=self._timer)

class StreamWorker:
    def __init__(self, id, pipe, timer=None):
        self._id = id
        self._pipe = pipe
        self._data = None
        self._timer = None

    def write(self, data):
        if not self._pipe: raise RuntimeError("Not open")
        self._pipe.send(('write', data))
        if self._timer: self._timer("self._pipe.send(('write', data)) after")

    def close(self):
        if not self._pipe: return
        if self._timer: self._timer("StreamWorker.close begin")
        try:
            self._pipe.send(('close',))
            self._pipe.close()
            self._pipe = None
        except (OSError, EOFError, BrokenPipeError) as e:
            pass
        if self._timer: self._timer("StreamWorker.close end")

    def __del__(self):
        self.close()
        if self._timer: print(self._timer)

    def _await_data(self):
        try:
            data = self._pipe.recv()
            if self._timer: self._timer("_await_data() recv after")
            if not data: raise EOFError
        except (OSError, EOFError, BrokenPipeError) as e:
            return False

        if data[0] == 'call':
            self._data = data[1]
            return True
        elif data[0] == 'close':
            self._pipe.close()
            return False
        else: 
            raise RuntimeError(f"Unexpected action while awaiting a call from the target: {data[0]}")

    @property
    def data(self):
        return self._data

class StreamRequestHandler:
    def __init__(self):
        self._wait_queue = multiprocessing.Queue()
        self._turn_queue = multiprocessing.Queue()
        self._handlers = {}
        self._listener = None
        self._counter = 0

    def empty(self):
        return self._wait_queue.empty()

    def get(self):
        handler = self._wait_queue.get()
        if handler._timer: handler._timer('self._turn_queue.put(handler) before')
        self._turn_queue.put(handler)
        if handler._timer: handler._timer('self._turn_queue.put(handler) after')
        return handler

    def turn_listener(self):
        while True:
            worker = self._turn_queue.get()
            target = self._handlers[worker._id][0]
            if target._timer: target._timer('target_handler.stream._turn.set() before')
            target._turn.set()
            if target._timer: target._timer('target_handler.stream._turn.set() after')

    def create(self):
        timer = None # Timer()
        if not self._listener or not self._listener.is_alive():
            self._listener = threading.Thread(target=self.turn_listener)
            self._listener.start()

        if timer: timer('check/run listener')

        id = self._counter
        self._counter += 1

        p1, p2 = multiprocessing.Pipe()
        worker_handler = StreamWorker(id, p1, timer=timer)
        target_handler = StreamTarget(id, p2, timer=timer)
        self._handlers[id] = (target_handler, worker_handler)
        if timer: timer('self._wait_queue.put before')
        self._wait_queue.put(worker_handler)
        if timer: timer('self._wait_queue.put after')
        return target_handler

class Streamer:
    def __init__(self):
        self._requests = StreamRequestHandler()

    def consume(self, minimum=1, maximum=1) -> list[StreamWorker]:
        streams = []
        while True:
            if len(streams) >= maximum: break
            if len(streams) >= minimum and self._requests.empty(): break
            worker = self._requests.get()
            if worker._await_data(): streams.append(worker)

        return streams

    def start_process(self, *args, **kwargs) -> multiprocessing.Process:
        p = multiprocessing.Process(target=self.worker, args=args, kwargs=kwargs)
        p.start()
        return p

    def start_thread(self, *args, **kwargs) -> threading.Thread:
        t = threading.Thread(target=self.worker, args=args, kwargs=kwargs)
        t.start()
        return t

    def write(self, id, data):
        pass

    def close(self, id):
        pass

    def worker(self):
        pass

    def stream(self):
        return self._requests.create()

class StreamerDecorator(Streamer):
    def __init__(self, fn):
        self._fn = fn
        super().__init__()

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def worker(self, minimum=1, maximum=1):
        while True:
            streams = self.consume(minimum=minimum, maximum=maximum)
            self(streams)
            for stream in streams: 
                stream.close()

def streamer(fn):
    return StreamerDecorator(fn)

from multiprocessing import Queue
from queue import Empty
import asyncio
from collections.abc import AsyncGenerator

CLOSED = object()

class BatchWorker:
    def __init__(self, function, min_batch_size, max_batch_size):
        assert min_batch_size <= max_batch_size

        self._function = function
        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size

        self._inputs = Queue()
        self._outputs = Queue()
        self._outputs_buff = None
        self._counter_inputs = 0
        self._counter_outputs = 0

    async def submit(self, data):
        i = self._counter_inputs
        self._counter_inputs += 1
        self._inputs.put(data)

        while True:
            while i >= self._counter_outputs:
                await asyncio.sleep(0.5)
                if self._outputs_buff is not None:
                    continue
                try: 
                    self._counter_outputs, self._outputs_buff = self._outputs.get(block=False)
                except Empty:
                    pass

            if self._outputs_buff is None or i not in self._outputs_buff:
                await asyncio.sleep(0.5)
                continue

            output = self._outputs_buff[i]
            del self._outputs_buff[i]
            if len(self._outputs_buff) == 0:
                self._outputs_buff = None

            yield output
            if output is CLOSED:
                return

    def _wait_for_batch(self):
        batch = []
        for _ in range(self._min_batch_size):
            batch.append(self._inputs.get(block=True))
        for _ in range(self._max_batch_size - self._min_batch_size):
            try:
                batch.append(self._inputs.get(block=False))
            except Empty:
                break
        return batch

    def start(self):
        while True:
            inputs = self._wait_for_batch()
            closed = [False for _ in inputs]
            buff = {}
            counter_outputs = self._counter_outputs
            for response in self._function(inputs):
                print(response)
                if isinstance(response, tuple) and len(response) == 2 and isinstance(response[0], int):
                    i, resp = response
                    i += counter_outputs
                    buff[i] = resp
                    self._outputs.put((counter_outputs + len(inputs), buff))
                else:
                    resp = response
                    i = self._counter_outputs
                    self._counter_outputs += 1
                    buff[i] = resp

            self._outputs.put((self._counter_outputs, buff))

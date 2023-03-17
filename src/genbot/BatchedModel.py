import multiprocessing
import threading
import time
from queue import Queue
import asyncio

class BatchedModel:
    def __init__(self, min_size: int = 1, max_size: int = 0):
        self._worker = threading.Thread(target=self._batch_worker)
        self._input_queue = []
        self._output_queue = []
        self._input_id_counter = 0
        self._output_id_counter = 0
        self.min_size = min_size
        self.max_size = max_size
        self._loop = True
        self._worker.start()

    def __del__(self):
        try:
            self._worker
        except:
            return

        self._worker.join(5)
        if self._worker.is_alive():
            pass

    def _batch_worker(self):
        while self._loop:
            time.sleep(0.1)
            if len(self._input_queue) < self.min_size:
                continue

            if self.max_size > 0:
                inputs =  self._input_queue[:self.max_size]
                self._input_queue = self._input_queue[self.max_size:]
            else:
                inputs = self._input_queue[:]
                self._input_queue = []

            try:
                outputs = list(self.batch(inputs))
                if len(outputs) != len(inputs):
                    raise ValueError("batch size of output is not equal to input")
                self._output_queue += outputs
                # print("outputs", self._output_queue)
            except Exception as e:
                print(e)
                self._output_queue += [None] * len(inputs)

    def _enqueue(self, feed):
        self._input_queue.append(feed)
        id = self._input_id_counter
        self._input_id_counter += 1
        return id

    def batch(self, feeds):
        return [None] * len(feeds)

    async def call_batch(self, feed):
        id = self._enqueue(feed)
        while True:
            await asyncio.sleep(0.2)
            if self._output_queue and self._output_id_counter == id:
                break
            if not self._worker.is_alive():
                raise RuntimeError("Batch worker is dead.")

        output = self._output_queue.pop(0)
        self._output_id_counter += 1
        return output


import asyncio
import typing


class MultiQueue:
    '''Multiple first in, first out (FIFO) queues with types.'''

    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self.queues = {}
        self.put_event = asyncio.Event()

    def _get_queue_of_type(self, type: typing.Hashable) -> list:
        try:
            return self.queues[type]
        except KeyError:
            self.queues[type] = []
            return self.queues[type]

    def push(self, type: typing.Hashable, item):
        '''Put an item into the queue of the given type. If the queue is full,
        wait until a free slot is available before adding the item.'''

        self._get_queue_of_type(type).append(item)

        # trigger put event to wake up pending get() calls
        self.put_event.set()
        self.put_event.clear()

    async def pop(self, types: typing.Iterable[typing.Hashable]):
        '''Remove and return an item from a queue of one of the given types.
        If all queues of the given types are empty, wait until an item is
        available.'''

        while True:
            for type in types:
                queue = self._get_queue_of_type(type)
                if len(queue) > 0:
                    return queue.pop(0)
            await self.put_event.wait()

    def remove(self, type: typing.Hashable, item):
        '''Removes the given item from a queue of the given type.'''

        self._get_queue_of_type(type).remove(item)

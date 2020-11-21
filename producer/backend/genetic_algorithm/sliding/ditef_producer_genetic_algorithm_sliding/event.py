import asyncio
import typing


class Subscription:

    def __init__(self, parent_event: 'BroadcastEvent'):
        self.parent_event = parent_event
        self.event = asyncio.Event()

    def notify(self):
        self.event.set()

    async def wait(self):
        await self.event.wait()
        self.event.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.parent_event.unsubscribe(self)


class BroadcastEvent:

    def __init__(self):
        self.subscriptions: typing.List[Subscription] = []

    def notify(self):
        for subscription in self.subscriptions:
            subscription.notify()

    def subscribe(self):
        subscription = Subscription(self)
        self.subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription):
        self.subscriptions.remove(subscription)

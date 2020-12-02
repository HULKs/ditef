import asyncio

import ditef_producer_shared.event
import ditef_router.api_client

from .population import Population


class Algorithm:

    def __init__(self, individual_type: str, pending_individuals: int, maximum_websocket_interval: int, task_api_client: ditef_router.api_client.ApiClient):
        self.individual_type = individual_type
        self.populations = []
        self.pending_individuals = pending_individuals
        self.maximum_websocket_interval = maximum_websocket_interval
        self.task_api_client = task_api_client
        self.metric_event = ditef_producer_shared.event.BroadcastEvent()

    async def add_population(self, configuration: dict):
        population = Population(
            self.individual_type,
            self.task_api_client,
            self.metric_event,
            configuration,
        )
        self.populations.append({
            'population': population,
            'tasks': [asyncio.create_task(population.run()) for _ in range(self.pending_individuals)],
        })
        self.metric_event.notify()

    async def remove_population(self, population_index: int):
        for task in self.populations[population_index]['tasks']:
            task.cancel()
        await asyncio.wait(self.populations[population_index]['tasks'])
        del self.populations[population_index]
        self.metric_event.notify()

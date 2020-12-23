import asyncio
import json
import importlib
from pathlib import Path
import uuid

import ditef_producer_shared.event
import ditef_producer_shared.json
import ditef_router.api_client

from .population import Population


class Algorithm:

    def __init__(self, individual_type: str, pending_individuals: int, state_path: str, minimum_websocket_interval: int, task_api_client: ditef_router.api_client.ApiClient):
        self.individual_type = individual_type
        self.populations = []
        self.pending_individuals = pending_individuals
        self.minimum_websocket_interval = minimum_websocket_interval
        self.task_api_client = task_api_client
        self.metric_event = ditef_producer_shared.event.BroadcastEvent()
        self.state_path = Path(state_path)
        if (self.state_path/'configuration.json').is_file():
            self.load_state()
        else:
            self.initialize_state()

    async def add_population(self, configuration: dict):
        population = Population(
            self.individual_type,
            self.task_api_client,
            self.metric_event,
            configuration,
            self.state_path,
            str(uuid.uuid4())
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
        (self.state_path/'populations'/(self.populations[population_index]['population'].id + '.json')).unlink()
        del self.populations[population_index]
        self.metric_event.notify()

    def load_state(self):
        # load configuration.json
        configuration_file = self.state_path/'configuration.json'
        with open(configuration_file, 'r') as f:
            file_content = f.read()
        if len(file_content) == 0:
            raise IOError(f'empty file: {configuration_file}')
        try:
            configuration_data = json.loads(file_content)
        except Exception:
            raise SyntaxError(f'could not parse: {configuration_file}')
        for required_key in Population.configuration_values(self.individual_type):
            if not required_key in configuration_data:
                raise KeyError(f'missing key: {required_key} in file {configuration_file}')
        Population.loaded_default_configuration = configuration_data

        # load individuals (create dir if it does not exists)
        importlib.import_module(
                self.individual_type,
            ).Individual.load_individuals_to_static_dict(
                self.state_path,
                self.task_api_client,
                Population.configuration_values(self.individual_type),
                self.individual_type)

        # load populations (create dir if it does not exists)
        loaded_populations = Population.load_populations(
            self.individual_type,
            self.task_api_client,
            self.metric_event,
            self.state_path)
        for loaded_population in loaded_populations:
            self.populations.append({
                'population': loaded_population,
                'tasks': [
                    asyncio.create_task(loaded_population.run())
                    for _ in range(self.pending_individuals)],
            })
        self.metric_event.notify()

    def initialize_state(self):
        self.state_path.mkdir(parents=True, exist_ok=True)
        (self.state_path/'individuals').mkdir(parents=True, exist_ok=True)
        (self.state_path/'populations').mkdir(parents=True, exist_ok=True)
        ditef_producer_shared.json.dump_complete(
            Population.configuration_values(self.individual_type),
            self.state_path/'configuration.json'
        )

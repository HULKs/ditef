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
        except Exception as e:
            raise SyntaxError(f'could not parse: {configuration_file}')
        for required_key in Population.configuration_values(self.individual_type):
            if not required_key in configuration_data:
                raise KeyError(f'missing key: {required_key} in file {configuration_file}')
        Population.loaded_default_configuration = configuration_data

        # load individuals (create dir if it does not exists)
        (self.state_path/'individuals').mkdir(parents=True, exist_ok=True)
        for individual_file in (self.state_path/'individuals').glob('**/*.json'):
            importlib.import_module(
                self.individual_type,
            ).Individual.load_individual_to_static_dict(
                individual_file,
                self.task_api_client,
                Population.configuration_values(self.individual_type),
                importlib.import_module(self.individual_type).Individual)

        # load populations (create dir if it does not exists)
        (self.state_path/'populations').mkdir(parents=True, exist_ok=True)
        for population_file in (self.state_path/'populations').glob('**/*.json'):
            # check population file
            with open(population_file, 'r') as f:
                file_content = f.read()
            if len(file_content) == 0:
                print('skipping population due to empty file:', population_file)
                continue
            try:
                population_data = json.loads(file_content)
            except Exception as e:
                print('skipping population that could not be parse:', population_file)
                continue
            if not 'configuration' in population_data:
                print('skipping population with missing configuration:', population_file)
                continue
            if not 'members' in population_data:
                print('skipping population with missing members list:', population_file)
                continue

            # check population configuration
            load_population = True
            for required_key in Population.configuration_values(self.individual_type):
                if not required_key in population_data['configuration']:
                    print('missing configuration key:', required_key, 'in file:', population_file)
                    load_population = False
            if not load_population:
                print('skipping population:', population_file)
                continue

            # create population
            new_population = Population(
                self.individual_type,
                self.task_api_client,
                self.metric_event,
                population_data['configuration'],
                self.state_path,
                population_file.stem
            )

            # add members to population
            for member_id in population_data['members']:
                if member_id in importlib.import_module(self.individual_type).Individual.individuals:
                    new_population.load_member_from_static_dict(member_id)
                else:
                    print("could not load individual:", member_id)
            self.populations.append({
                'population': new_population,
                'tasks': [asyncio.create_task(new_population.run()) for _ in range(self.pending_individuals)],
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

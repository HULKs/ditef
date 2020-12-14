import aiohttp.web
import asyncio
import copy
import datetime
import json
from pathlib import Path
import random
import textwrap
import typing
import uuid

import ditef_producer_shared.event
import ditef_producer_shared.json
import ditef_router.api_client


class Individual:

    @staticmethod
    def configuration_values() -> dict:
        return {
            'genome_size': {
                'help': 'Amount of bits in bitvector genome',
                'default': 100,
            },
            'maximum_amount_of_mutations': {
                'help': 'Maximum amount of mutations',
                'default': 10,
            },
        }

    individuals = {}

    def __init__(self, task_api_client: ditef_router.api_client.ApiClient, configuration: dict, id: str, genome: typing.List[bool], creation_type: str):
        self.task_api_client = task_api_client
        self.configuration = configuration
        self.id = id
        self.genome = genome
        self.creation_type = creation_type
        self.genealogy_parents = []
        self.genealogy_children = []
        self.evaluation_result: typing.Optional[dict] = None
        self.update_event = ditef_producer_shared.event.BroadcastEvent()

    @staticmethod
    def load_individual_to_static_dict(individual_file: Path, task_api_client: ditef_router.api_client.ApiClient, configuration):
        with open(individual_file, 'r') as f:
            individual_data = json.loads(f.read())

        Individual.individuals[individual_file.stem] = Individual(task_api_client,
            configuration,
            individual_file.stem,
            individual_data['genome'],
            individual_data['creation_type'])

        Individual.individuals[individual_file.stem].genealogy_parents = individual_data['genealogy_parents']
        Individual.individuals[individual_file.stem].genealogy_children = individual_data['genealogy_children']

        if 'evaluation_result' in individual_data:
            Individual.individuals[individual_file.stem].evaluation_result = individual_data['evaluation_result']

    @staticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient, configuration: dict) -> 'Individual':
        '''Generates a new random individual'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            [
                random.choice([True, False])
                for _ in range(configuration['genome_size'])
            ],
            'random',
        )

        return Individual.individuals[individual_id]

    @staticmethod
    def clone(parent: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, creation_type: str) -> 'Individual':
        '''Creates a copy of a parent individual'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            copy.deepcopy(parent.genome),
            creation_type,
        )
        Individual.individuals[individual_id].genealogy_parents = [parent.id]
        parent.genealogy_children.append(individual_id)
        parent.update_event.notify()

        return Individual.individuals[individual_id]

    @staticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict) -> 'Individual':
        '''Creates one cross-overed individual from two parent individuals'''

        individual_id = str(uuid.uuid4())
        Individual.individuals[individual_id] = Individual(
            task_api_client,
            configuration,
            individual_id,
            [
                random.choice([gene_a, gene_b])
                for gene_a, gene_b in zip(parent_a.genome, parent_b.genome)
            ],
            'cross_over_one',
        )
        Individual.individuals[individual_id].genealogy_parents = [
            parent_a.id,
            parent_b.id,
        ]
        parent_a.genealogy_children.append(individual_id)
        parent_a.update_event.notify()
        parent_b.genealogy_children.append(individual_id)
        parent_b.update_event.notify()

        return Individual.individuals[individual_id]

    def mutate(self):
        for _ in range(random.randrange(self.configuration['maximum_amount_of_mutations'] + 1)):
            i = random.randrange(len(self.genome))
            self.genome[i] = not self.genome[i]
        self.update_event.notify()

    async def evaluate(self):
        sum = await self.task_api_client.run(
            'ditef_worker_genetic_individual_bitvector',
            self.genome,
        )
        self.evaluation_result = {'sum': sum}
        self.update_event.notify()

    def fitness(self) -> typing.Optional[float]:
        if self.evaluation_result is not None:
            return float(self.evaluation_result['sum'])

    def api_url(self) -> str:
        return f'/genetic_individual_bitvector/api/{self.id}'

    async def api_write_update_to_websocket(self, websocket: aiohttp.web.WebSocketResponse):
        await websocket.send_json(
            data={
                'genome': self.genome,
                'fitness': self.fitness(),
                'creation_type': self.creation_type,
                'genealogy_parents': {
                    parent_id: {
                        'fitness': Individual.individuals[parent_id].fitness(),
                        'url': Individual.individuals[parent_id].api_url(),
                    }
                    for parent_id in self.genealogy_parents
                },
                'genealogy_children': {
                    child_id: {
                        'fitness': Individual.individuals[child_id].fitness(),
                        'url': Individual.individuals[child_id].api_url(),
                    }
                    for child_id in self.genealogy_children
                },
            },
            dumps=ditef_producer_shared.json.json_formatter_compressed,
        )

    async def subscribe_to_update(self, websocket: aiohttp.web.WebSocketResponse):
        with self.update_event.subscribe() as subscription:
            while True:
                await self.api_write_update_to_websocket(websocket)
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < Individual.minimum_websocket_interval:
                    await asyncio.sleep(Individual.minimum_websocket_interval - seconds_spent_in_wait)

    minimum_websocket_interval = 0

    @staticmethod
    def api_add_routes(app: aiohttp.web.Application, minimum_websocket_interval: int):
        Individual.minimum_websocket_interval = minimum_websocket_interval
        app.add_routes([
            aiohttp.web.get(
                r'/genetic_individual_bitvector/api/{individual_id:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}}',
                Individual.api_handle_websocket,
            ),
        ])

    @staticmethod
    async def api_handle_websocket(request: aiohttp.web.Request):
        websocket = aiohttp.web.WebSocketResponse(heartbeat=10)
        await websocket.prepare(request)

        individual_id = request.match_info['individual_id']
        individual: Individual = Individual.individuals[individual_id]

        update_subscription_task = asyncio.create_task(
            individual.subscribe_to_update(
                websocket,
            ),
        )

        await individual.api_write_update_to_websocket(websocket)

        try:
            async for message in websocket:
                assert message.type == aiohttp.web.WSMsgType.TEXT
                print('Message not handled:', message)
        finally:
            update_subscription_task.cancel()
            try:
                await update_subscription_task
            except asyncio.CancelledError:
                pass

        return websocket

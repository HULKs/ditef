import abc
import aiohttp.web
import asyncio
import datetime
import importlib
import pathlib
import simplejson
import typing

import ditef_producer_shared.event
import ditef_producer_shared.json
import ditef_router.api_client

class AbstractIndividual(metaclass=abc.ABCMeta):

    @abc.abstractstaticmethod
    def configuration_values() -> dict:
        pass

    individuals = {}

    def __init__(self, task_api_client: ditef_router.api_client.ApiClient, configuration: dict, id: str, genome: typing.List[bool], creation_type: str, individual_file: pathlib.Path):
        self.task_api_client = task_api_client
        self.configuration = configuration
        self.id = id
        self.genome = genome
        self.creation_type = creation_type
        self.individual_file = individual_file
        self.genealogy_parents = []
        self.genealogy_children = []
        self.evaluation_result: typing.Optional[dict] = None
        self.update_event = ditef_producer_shared.event.BroadcastEvent()

    @abc.abstractmethod
    def individual_type(self) -> str:
        pass

    @staticmethod
    def load_individuals_to_static_dict(individuals_folder: pathlib.Path, task_api_client: ditef_router.api_client.ApiClient, configuration, individual_type: str):
        (individuals_folder/'individuals').mkdir(parents=True, exist_ok=True)
        for individual_file in (individuals_folder/'individuals').glob('*.json'):
            AbstractIndividual.load_individual_to_static_dict(
                individual_file,
                task_api_client,
                configuration,
                individual_type,
            )

    @staticmethod
    def load_individual_to_static_dict(individual_file: pathlib.Path, task_api_client: ditef_router.api_client.ApiClient, configuration, individual_type):
        with individual_file.open('r') as f:
            try:
                individual_data = simplejson.load(f)
            except Exception:
                print(f'could not parse: {individual_file}')
                return
        for required_key in ['genome', 'creation_type', 'genealogy_parents', 'genealogy_children']:
            if not required_key in individual_data:
                print('missing key:', required_key, 'in file:', individual_file)
                return

        AbstractIndividual.individuals[individual_file.stem] = importlib.import_module(individual_type).Individual(
            task_api_client,
            individual_data['configuration'],
            individual_file.stem,
            individual_data['genome'],
            individual_data['creation_type'],
            individual_file,
        )

        AbstractIndividual.individuals[individual_file.stem].genealogy_parents = individual_data['genealogy_parents']
        AbstractIndividual.individuals[individual_file.stem].genealogy_children = individual_data['genealogy_children']

        if 'evaluation_result' in individual_data:
            AbstractIndividual.individuals[individual_file.stem].evaluation_result = individual_data['evaluation_result']

    def write_to_file(self):
        data = {
            'genome': self.genome,
            'configuration': self.configuration,
            'creation_type': self.creation_type,
            'genealogy_parents':  self.genealogy_parents,
            'genealogy_children': self.genealogy_children,
        }
        if self.evaluation_result is not None:
            data['evaluation_result'] = self.evaluation_result
        ditef_producer_shared.json.dump_complete(data, self.individual_file)

    def add_child(self, individual_id: str):
        self.genealogy_children.append(individual_id)
        self.write_to_file()
        self.update_event.notify()

    @abc.abstractstaticmethod
    def random(task_api_client: ditef_router.api_client.ApiClient, configuration: dict, state_path: pathlib.Path) -> 'Individual':
        pass

    @abc.abstractstaticmethod
    def clone(parent: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, creation_type: str, state_path: pathlib.Path) -> 'Individual':
        pass

    @abc.abstractstaticmethod
    def cross_over_one(parent_a: 'Individual', parent_b: 'Individual', task_api_client: ditef_router.api_client.ApiClient, configuration: dict, state_path: pathlib.Path) -> 'Individual':
        pass

    @abc.abstractmethod
    def mutate(self):
        pass

    @abc.abstractmethod
    async def evaluate(self):
        pass

    @abc.abstractmethod
    def fitness(self) -> typing.Optional[float]:
        pass

    async def api_write_update_to_websocket(self, websocket: aiohttp.web.WebSocketResponse):
        await websocket.send_json(
            data={
                'genome': self.genome,
                'configuration': self.configuration,
                'fitness': self.fitness(),
                'creation_type': self.creation_type,
                'evaluation_result': self.evaluation_result,
                'genealogy_parents': {
                    parent_id: {
                        'fitness': AbstractIndividual.individuals[parent_id].fitness(),
                        'url': AbstractIndividual.individuals[parent_id].api_url(self.individual_type()),
                    }
                    for parent_id in self.genealogy_parents
                },
                'genealogy_children': {
                    child_id: {
                        'fitness': AbstractIndividual.individuals[child_id].fitness(),
                        'url': AbstractIndividual.individuals[child_id].api_url(self.individual_type()),
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
                if seconds_spent_in_wait < AbstractIndividual.minimum_websocket_interval:
                    await asyncio.sleep(AbstractIndividual.minimum_websocket_interval - seconds_spent_in_wait)

    minimum_websocket_interval = 0

    @staticmethod
    def api_add_routes(app: aiohttp.web.Application, individual_type: str, minimum_websocket_interval: int):
        AbstractIndividual.minimum_websocket_interval = minimum_websocket_interval
        app.add_routes([
            aiohttp.web.get(
                r'/genetic_individual_{individual_type}/api/{individual_id:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}}',
                AbstractIndividual.api_handle_websocket,
            ),
        ])

    def api_url(self, individual_type: str) -> str:
        return f'/genetic_individual_{individual_type}/api/{self.id}'

    @staticmethod
    async def api_handle_websocket(request: aiohttp.web.Request):
        websocket = aiohttp.web.WebSocketResponse(heartbeat=10)
        await websocket.prepare(request)

        individual_id = request.match_info['individual_id']
        individual = AbstractIndividual.individuals[individual_id]

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

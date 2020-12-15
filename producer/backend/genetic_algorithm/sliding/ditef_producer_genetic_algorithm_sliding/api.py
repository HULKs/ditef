import aiohttp.web
import asyncio
import datetime
import io
import numpy
import ruamel.yaml
import simplejson

import ditef_producer_shared.json

from .algorithm import Algorithm
from .population import Population


class Api:

    def __init__(self):
        self.yaml = ruamel.yaml.YAML()

    def add_routes(self, app: aiohttp.web.Application):
        app.add_routes([
            aiohttp.web.get(
                '/genetic_algorithm_sliding/api/populations/ws/',
                self.handle_populations_websocket,
            ),
            aiohttp.web.get(
                r'/genetic_algorithm_sliding/api/population/{index:\d+}/ws/',
                self.handle_population_websocket,
            ),
        ])

    def convert_configuration_values_to_yaml_configuration(self, configuration_schema: dict, indent=0):
        result = ruamel.yaml.comments.CommentedMap()
        for key, definition in configuration_schema.items():
            if isinstance(definition['default'], dict):
                result[key] = self.convert_configuration_values_to_yaml_configuration(
                    definition['default'], indent+2)
                result.yaml_set_comment_before_after_key(
                    key, before=f'\n{definition["help"]}', indent=indent)
            else:
                result[key] = definition['default']
                result.yaml_set_comment_before_after_key(
                    key, before=f'\n{definition["help"]}\n default: {definition["default"]}', indent=indent)
        return result

    def yaml_dumps(self, yaml_object):
        string_stream = io.StringIO()
        self.yaml.dump(yaml_object, string_stream)
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str.strip()

    async def subscribe_to_algorithm_metrics(self, algorithm: Algorithm, websocket: aiohttp.web.WebSocketResponse):
        with algorithm.metric_event.subscribe() as subscription:
            while True:
                await websocket.send_json(
                    data={
                        'current_metrics': [
                            population['population'].current_metrics()
                            for population in algorithm.populations
                        ],
                    },
                    dumps=ditef_producer_shared.json.json_formatter_compressed,
                )
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < algorithm.minimum_websocket_interval:
                    await asyncio.sleep(algorithm.minimum_websocket_interval - seconds_spent_in_wait)

    async def handle_populations_websocket(self, request: aiohttp.web.Request):
        websocket = aiohttp.web.WebSocketResponse(heartbeat=10)
        await websocket.prepare(request)

        algorithm: Algorithm = request.app['algorithm']

        metric_subscription_task = asyncio.create_task(
            self.subscribe_to_algorithm_metrics(
                algorithm,
                websocket,
            ),
        )

        await websocket.send_json(
            data={
                'initial_configuration': self.yaml_dumps(
                    self.convert_configuration_values_to_yaml_configuration(
                        Population.configuration_values(
                            algorithm.individual_type,
                        ),
                    ),
                ),
            },
            dumps=ditef_producer_shared.json.json_formatter_compressed,
        )

        try:
            async for message in websocket:
                assert message.type == aiohttp.web.WSMsgType.TEXT
                message = simplejson.loads(message.data)
                if message['type'] == 'add_population':
                    await algorithm.add_population(self.yaml.load(message['configuration']))
                elif message['type'] == 'remove_population':
                    await algorithm.remove_population(message['population_index'])
                else:
                    print('Message not handled:', message)
        finally:
            metric_subscription_task.cancel()
            try:
                await metric_subscription_task
            except asyncio.CancelledError:
                pass

        return websocket

    async def subscribe_to_population_configuration(self, algorithm: Algorithm, population: Population, websocket: aiohttp.web.WebSocketResponse):
        with population.configuration_event.subscribe() as subscription:
            while True:
                await websocket.send_json(
                    data={
                        'configuration': self.yaml_dumps(population.configuration),
                    },
                    dumps=ditef_producer_shared.json.json_formatter_compressed,
                )
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < algorithm.minimum_websocket_interval:
                    await asyncio.sleep(algorithm.minimum_websocket_interval - seconds_spent_in_wait)

    async def subscribe_to_population_metrics(self, algorithm: Algorithm, population: Population, websocket: aiohttp.web.WebSocketResponse):
        with population.metric_event.subscribe() as subscription:
            while True:
                await websocket.send_json(
                    data={
                        'detailed_metrics': population.detailed_metrics(
                            datetime.datetime.now() - datetime.timedelta(minutes=10),
                            datetime.timedelta(minutes=10),
                            datetime.timedelta(seconds=1),
                            'mean',
                        ),
                    },
                    dumps=ditef_producer_shared.json.json_formatter_compressed,
                )
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < algorithm.minimum_websocket_interval:
                    await asyncio.sleep(algorithm.minimum_websocket_interval - seconds_spent_in_wait)

    async def subscribe_to_population_members(self, algorithm: Algorithm, population: Population, websocket: aiohttp.web.WebSocketResponse):
        with population.members_event.subscribe() as subscription:
            while True:
                await websocket.send_json(
                    data={
                        'individual_type': algorithm.individual_type,
                        'members': {
                            member.id: {
                                'fitness': member.fitness(),
                                'url': member.api_url(member.individual_type()),
                            }
                            for member in population.members
                        },
                    },
                    dumps=ditef_producer_shared.json.json_formatter_compressed,
                )
                last_websocket_message = datetime.datetime.now()
                await subscription.wait()
                seconds_spent_in_wait = (
                    datetime.datetime.now() - last_websocket_message
                ).total_seconds()
                if seconds_spent_in_wait < algorithm.minimum_websocket_interval:
                    await asyncio.sleep(algorithm.minimum_websocket_interval - seconds_spent_in_wait)

    async def handle_population_websocket(self, request: aiohttp.web.Request):
        websocket = aiohttp.web.WebSocketResponse(heartbeat=10)
        await websocket.prepare(request)

        algorithm: Algorithm = request.app['algorithm']
        population_index = int(request.match_info['index'])
        population: Population = algorithm.populations[population_index]['population']

        configuration_subscription_task = asyncio.create_task(
            self.subscribe_to_population_configuration(
                algorithm,
                population,
                websocket,
            ),
        )

        metric_subscription_task = asyncio.create_task(
            self.subscribe_to_population_metrics(
                algorithm,
                population,
                websocket,
            ),
        )

        members_subscription_task = asyncio.create_task(
            self.subscribe_to_population_members(
                algorithm,
                population,
                websocket,
            ),
        )

        await websocket.send_json(
            data={
                'configuration': self.yaml_dumps(population.configuration),
            },
            dumps=ditef_producer_shared.json.json_formatter_compressed,
        )

        try:
            async for message in websocket:
                assert message.type == aiohttp.web.WSMsgType.TEXT
                message = simplejson.loads(message.data)
                if message['type'] == 'update_configuration':
                    population.configuration.clear()
                    population.configuration.update(
                        self.yaml.load(message['configuration']),
                    )
                    population.configuration_event.notify()
                else:
                    print('Message not handled:', message)
        finally:
            configuration_subscription_task.cancel()
            metric_subscription_task.cancel()
            members_subscription_task.cancel()
            try:
                await configuration_subscription_task
            except asyncio.CancelledError:
                pass
            try:
                await metric_subscription_task
            except asyncio.CancelledError:
                pass
            try:
                await members_subscription_task
            except asyncio.CancelledError:
                pass

        return websocket

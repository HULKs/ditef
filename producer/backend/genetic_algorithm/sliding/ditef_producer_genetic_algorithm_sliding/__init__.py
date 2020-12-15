import aiohttp.web
import asyncio
import click
import importlib
import pathlib
import urllib

import ditef_router.api_client

from .api import Api
from .algorithm import Algorithm


def append_to_server_url(router_url: str, path: str):
    parsed_router_url = urllib.parse.urlparse(router_url)
    return urllib.parse.urlunparse((
        parsed_router_url.scheme,
        parsed_router_url.netloc,
        str(pathlib.PurePosixPath(parsed_router_url.path) /
            path
            ),
        '',
        '',
        '',
    ))


async def cancel_populations(app: aiohttp.web.Application):
    for population in app['algorithm'].populations:
        for task in population['tasks']:
            task.cancel()
        await asyncio.wait(population['tasks'])


async def async_main(**arguments):
    async with ditef_router.api_client.ApiClient(arguments['router_url'], arguments['connect_timeout'], arguments['initial_retry_timeout'], arguments['maximum_retry_timeout']) as task_api_client:
        app = aiohttp.web.Application()
        app['arguments'] = arguments

        app['algorithm'] = Algorithm(
            app['arguments']['individual_type'],
            app['arguments']['population_tasks'],
            app['arguments']['state_path'],
            app['arguments']['minimum_websocket_interval'],
            task_api_client,
        )
        app.on_cleanup.append(cancel_populations)

        importlib.import_module(
            app['arguments']['individual_type'],
        ).Individual.api_add_routes(
            app,
            app['arguments']['minimum_websocket_interval'],
        )

        api = Api()
        api.add_routes(app)

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(
            runner=runner,
            host=arguments['host'],
            port=arguments['port'],
        )
        await site.start()

        eternity_event = asyncio.Event()
        try:
            print('Listening on', ', '.join(str(site.name)
                                            for site in runner.sites), '...')
            await eternity_event.wait()
        finally:
            await runner.cleanup()


@click.command()
@click.option('--host', default='*', help='Hostname to listen on', show_default=True)
@click.option('--port', default=8081, help='Port of the webserver', show_default=True)
@click.option('--connect-timeout', default=1, help='Timeout in seconds for connection')
@click.option('--initial-retry-timeout', default=1, help='Initial retry timeout in seconds at beginning of back-off')
@click.option('--maximum-retry-timeout', default=16, help='Upper bound of back-off retry timeout in seconds')
@click.option('--population-tasks', default=3, help='Number of running tasks per population')
@click.option('--minimum-websocket-interval', default=0.5, help='Shortest interval period in seconds for rate limiting outgoing websocket messages (set to 0 for no limit)')
@click.argument('router_url', type=str)
@click.argument('individual_type', type=str)
@click.argument('state_path', type=click.Path(file_okay=False))
def main(**arguments):
    asyncio.run(async_main(**arguments))

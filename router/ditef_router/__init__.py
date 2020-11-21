import aiohttp.web
import asyncio
import click
import socket

from .api import Api


async def server(**arguments):
    app = aiohttp.web.Application()
    api = Api(arguments)
    api.add_routes(app)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner=runner,
        host=arguments['host'],
        port=arguments['port'],
    )
    await site.start()

    for server_socket in site._server.sockets:
        if server_socket is not None:
            server_socket.setsockopt(
                socket.SOL_SOCKET,
                # enable TCP keepalive (https://tldp.org/HOWTO/html_single/TCP-Keepalive-HOWTO/)
                socket.SO_KEEPALIVE,
                1,
            )
            server_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive probes: the number of unacknowledged probes to send before considering the connection dead and notifying the application layer
                socket.TCP_KEEPCNT,
                3,
            )
            server_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive time: the interval between the last data packet sent (simple ACKs are not considered data) and the first keepalive probe; after the connection is marked to need keepalive, this counter is not used any further
                socket.TCP_KEEPIDLE,
                60,
            )
            server_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive interval: the interval between subsequential keepalive probes, regardless of what the connection has exchanged in the meantime
                socket.TCP_KEEPINTVL,
                60,
            )

    eternity_event = asyncio.Event()
    try:
        print('Listening on', ', '.join(str(site.name)
                                        for site in runner.sites), '...')
        await eternity_event.wait()
    finally:
        await runner.cleanup()


@click.command()
@click.option('--host', default='*', help='Hostname to listen on', show_default=True)
@click.option('--port', default=8080, help='Port of the webserver', show_default=True)
@click.option('--heartbeat-timeout', default=60, help='Heartbeat timeout in seconds', show_default=True)
def main(**arguments):
    asyncio.run(server(**arguments))

import aiohttp
import asyncio
import datetime
import pathlib
import socket
import typing
import urllib


class KeepAliveTCPConnector(aiohttp.TCPConnector):

    async def _create_connection(self, req: aiohttp.ClientRequest, traces: typing.List['Trace'], timeout: aiohttp.ClientTimeout):
        if req.proxy:
            transport, proto = await self._create_proxy_connection(
                req, traces, timeout)
        else:
            transport, proto = await self._create_direct_connection(
                req, traces, timeout)

        connection_socket: socket.socket = transport.get_extra_info(
            'socket')
        if connection_socket is not None:
            connection_socket.setsockopt(
                socket.SOL_SOCKET,
                # enable TCP keepalive (https://tldp.org/HOWTO/html_single/TCP-Keepalive-HOWTO/)
                socket.SO_KEEPALIVE,
                1,
            )
            connection_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive probes: the number of unacknowledged probes to send before considering the connection dead and notifying the application layer
                socket.TCP_KEEPCNT,
                3,
            )
            connection_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive time: the interval between the last data packet sent (simple ACKs are not considered data) and the first keepalive probe; after the connection is marked to need keepalive, this counter is not used any further
                socket.TCP_KEEPIDLE,
                60,
            )
            connection_socket.setsockopt(
                socket.SOL_TCP,
                # tcp keepalive interval: the interval between subsequential keepalive probes, regardless of what the connection has exchanged in the meantime
                socket.TCP_KEEPINTVL,
                60,
            )

        return proto


class ApiClient:

    def __init__(self, server_url: str, connect_timeout: int, initial_retry_timeout: int, maximum_retry_timeout: int):
        parsed_server_url = urllib.parse.urlparse(server_url)
        self.endpoint = urllib.parse.urlunparse((
            parsed_server_url.scheme,
            parsed_server_url.netloc,
            str(pathlib.PurePosixPath(parsed_server_url.path) /
                'task' / 'run'),
            '',
            '',
            '',
        ))

        self.connect_timeout = connect_timeout
        self.initial_retry_timeout = initial_retry_timeout
        self.maximum_retry_timeout = maximum_retry_timeout

        self.session = aiohttp.ClientSession(
            connector=KeepAliveTCPConnector(
                limit=None,
                limit_per_host=0,
            ),
            timeout=aiohttp.ClientTimeout(
                total=None,
                connect=self.connect_timeout,
                sock_connect=self.connect_timeout,
                sock_read=None,
            ),
        )

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.session.__aexit__(*args, **kwargs)

    async def run(self, type: str, payload):
        retry_count = 0
        retry_first_timestamp = None

        while True:
            try:
                try:
                    async with self.session.post(self.endpoint, params={'taskType': type}, json=payload) as response:
                        assert response.status == 200
                        return await response.json()
                except AssertionError:
                    retry_output = '' if retry_count == 0 else f' (retried {retry_count} times since {datetime.datetime.now() - retry_first_timestamp})'
                    print(
                        f'Got {response.status} while running task, retrying...{retry_output}')
                    raise
                except aiohttp.ClientConnectionError:
                    retry_output = '' if retry_count == 0 else f' (retried {retry_count} times since {datetime.datetime.now() - retry_first_timestamp})'
                    print(
                        f'Failed to connect while running task, retrying...{retry_output}')
                    raise
            except (AssertionError, aiohttp.ClientConnectionError):
                # store timestamp
                if retry_first_timestamp is None:
                    retry_first_timestamp = datetime.datetime.now()
                # exponential back-off
                await asyncio.sleep(
                    min(
                        self.maximum_retry_timeout,
                        self.initial_retry_timeout * 2**retry_count,
                    ),
                )
                retry_count += 1

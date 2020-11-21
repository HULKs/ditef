import click
import datetime
import importlib
import pathlib
import requests
import threading
import time
import typing
import urllib.parse


def append_to_server_url(router_url: str, object_type: str, operation: str):
    parsed_router_url = urllib.parse.urlparse(router_url)
    return urllib.parse.urlunparse((
        parsed_router_url.scheme,
        parsed_router_url.netloc,
        str(pathlib.PurePosixPath(parsed_router_url.path) /
            object_type / operation),
        '',
        '',
        '',
    ))


class HeartbeatThread(threading.Thread):

    def __init__(self, url, interval: int):
        super().__init__()
        self.url = url
        self.interval = interval
        self.start_event = threading.Event()
        self.stop_event = threading.Event()
        self.cancel_event = threading.Event()
        self.current_task_id: typing.Optional[str] = None

    def run(self):
        while not self.cancel_event.is_set():
            self.start_event.wait()
            self.start_event.clear()
            while not self.stop_event.wait(self.interval):
                # send heartbeat
                requests.post(
                    self.url,
                    params={
                        'taskId': self.current_task_id,
                    },
                )
            self.stop_event.clear()


@click.command()
@click.option('--connect-timeout', default=1, help='Timeout in seconds for connection', show_default=True)
@click.option('--long-polling-interval', default=60, help='Long polling interval in seconds', show_default=True)
@click.option('--initial-retry-timeout', default=1, help='Initial retry timeout in seconds at beginning of back-off', show_default=True)
@click.option('--maximum-retry-timeout', default=16, help='Upper bound of back-off retry timeout in seconds', show_default=True)
@click.option('--heartbeat-interval', default=30, help='Heartbeat interval in seconds', show_default=True)
@click.argument('router_url', type=str)
@click.argument('task_type', type=str, required=True, nargs=-1)
def main(**arguments):
    url_task_get = append_to_server_url(arguments['router_url'], 'task', 'get')
    url_task_heartbeat = append_to_server_url(
        arguments['router_url'], 'task', 'heartbeat')
    url_task_result = append_to_server_url(
        arguments['router_url'], 'result', 'set')
    retry_count = 0
    retry_first_timestamp = None

    heartbeat_thread = HeartbeatThread(
        url_task_heartbeat, arguments['heartbeat_interval'])
    heartbeat_thread.start()

    try:
        while True:
            try:
                try:
                    task_response = requests.get(
                        url_task_get,
                        params={
                            'taskType': list(arguments['task_type']),
                        },
                        headers={
                            # RFC 7240
                            'Prefer': f'wait={arguments["long_polling_interval"]}',
                        },
                        timeout=(
                            arguments['connect_timeout'],
                            arguments['long_polling_interval'] + 5,
                        ),
                    )
                    assert task_response.status_code in [200, 204]
                except AssertionError:
                    retry_output = '' if retry_count == 0 else f' (retried {retry_count} times since {datetime.datetime.now() - retry_first_timestamp})'
                    print(
                        f'Got {task_response.status_code} while getting task, retrying...{retry_output}')
                    raise
                except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                    retry_output = '' if retry_count == 0 else f' (retried {retry_count} times since {datetime.datetime.now() - retry_first_timestamp})'
                    print(
                        f'Failed to connect while getting task, retrying...{retry_output}')
                    raise
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout, AssertionError):
                # store timestamp
                if retry_first_timestamp is None:
                    retry_first_timestamp = datetime.datetime.now()
                # exponential back-off
                time.sleep(
                    min(
                        arguments['maximum_retry_timeout'],
                        arguments['initial_retry_timeout'] * 2**retry_count,
                    ),
                )
                retry_count += 1
                continue

            retry_count = 0
            retry_first_timestamp = None

            if task_response.status_code == 204:
                # server had no task within long-polling interval, retry
                print('Got 204 while getting task, retrying...')
                continue

            task = task_response.json()

            assert task['taskType'] in arguments['task_type']

            heartbeat_thread.current_task_id = task['taskId']
            heartbeat_thread.start_event.set()
            try:
                result = importlib.import_module(
                    task['taskType']).run(task['payload'])
            except KeyboardInterrupt:
                raise
            except:
                heartbeat_thread.stop_event.set()
                import traceback
                traceback.print_exc()
                continue

            try:
                result_response = requests.post(
                    url_task_result,
                    params={
                        'taskId': task['taskId'],
                    },
                    json=result,
                    timeout=(
                        arguments['connect_timeout'],
                        1,
                    ),
                )
                assert result_response.status_code == 200
            except AssertionError:
                print(
                    f'Got {result_response.status_code} while setting task result, continuing...')
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                print(
                    f'Failed to connect while setting task result, continuing...')
            finally:
                heartbeat_thread.stop_event.set()

    finally:
        heartbeat_thread.cancel_event.set()
        heartbeat_thread.start_event.set()
        heartbeat_thread.stop_event.set()
        heartbeat_thread.join()

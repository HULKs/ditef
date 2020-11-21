import aiohttp
import asyncio
import subprocess
import typing
import uuid


async def wait_for_url(client: aiohttp.ClientSession, url: str, method: str):
    while True:
        try:
            async with client.options(url) as response:
                if method in response.headers['Allow']:
                    return
        except aiohttp.ClientConnectorError:
            pass
        await asyncio.sleep(0.1)


async def task_producer_run(client: aiohttp.ClientSession, task_type: str, task_payload):
    async with client.post('http://localhost:8080/task/run', params={'taskType': task_type}, json=task_payload) as response:
        assert response.status == 200
        assert await response.json() == task_payload


async def worker_task_gettersetter(client: aiohttp.ClientSession, task_types: typing.List[str], timeout: int):
    async with client.get('http://localhost:8080/task/get', headers={'Prefer': f'wait={timeout}'}, params={'taskType': task_types}) as response:
        assert response.status == 200
        task_payload = await response.json()
    async with client.post('http://localhost:8080/result/set', params={'taskId': task_payload['taskId']}, json=task_payload['payload']) as response:
        assert response.status == 200


async def test_many_tasks_many_workers_steps(test_steps):
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None, limit_per_host=0)) as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            task_type = 'task-type-under-test'
            producer_tasks = []
            worker_tasks = []
            
            for type, amount in test_steps:
                print(f'Creating {amount} {type}s...')
                if type == 'producer':
                    for _ in range(amount):
                        producer_tasks.append(
                            asyncio.create_task(
                                task_producer_run(
                                    client,
                                    task_type,
                                    str(uuid.uuid4()),
                                ),
                            ),
                        )
                elif type == 'worker':
                    for _ in range(amount):
                        worker_tasks.append(
                            asyncio.create_task(
                                worker_task_gettersetter(
                                    client,
                                    [task_type],
                                    60,
                                ),
                            ),
                        )
            
            print(f'Awaiting {len(producer_tasks) + len(worker_tasks)} tasks...')
            assert len(producer_tasks) == len(worker_tasks)
            for task in worker_tasks + producer_tasks:
                await task
            print(f'Awaited {len(producer_tasks) + len(worker_tasks)} tasks.')
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_many_tasks_many_workers():
    for factor in [1, 10, 33]:
        print('factor:', factor)
        await test_many_tasks_many_workers_steps(
            [
                ('producer', 3 * factor),
                ('producer', 3 * factor),
                ('worker', 5 * factor),
                ('producer', 3 * factor),
                ('producer', 3 * factor),
                ('worker', 5 * factor),
                ('producer', 3 * factor),
                ('worker', 5 * factor),
            ],
        )
        await test_many_tasks_many_workers_steps(
            [
                ('worker', 5 * factor),
                ('producer', 3 * factor),
                ('worker', 5 * factor),
                ('producer', 3 * factor),
                ('producer', 3 * factor),
                ('worker', 5 * factor),
                ('producer', 3 * factor),
                ('producer', 3 * factor),
            ],
        )
        await test_many_tasks_many_workers_steps(
            [
                ('producer', 5 * factor),
                ('worker', 3 * factor),
                ('producer', 5 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('producer', 5 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
            ],
        )
        await test_many_tasks_many_workers_steps(
            [
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('producer', 5 * factor),
                ('producer', 5 * factor),
                ('producer', 5 * factor),
            ],
        )
        await test_many_tasks_many_workers_steps(
            [
                ('producer', 5 * factor),
                ('producer', 5 * factor),
                ('producer', 5 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
                ('worker', 3 * factor),
            ],
        )

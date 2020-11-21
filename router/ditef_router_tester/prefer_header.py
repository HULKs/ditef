import aiohttp
import asyncio
import datetime
import subprocess
import typing


async def wait_for_url(client: aiohttp.ClientSession, url: str, method: str):
    while True:
        try:
            async with client.options(url) as response:
                if method in response.headers['Allow']:
                    return
        except aiohttp.ClientConnectorError:
            pass
        await asyncio.sleep(0.1)


async def test_missing_prefer_header():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/get', 'GET')

            async with client.get('http://localhost:8080/task/get', params={'taskType': ['task-type-under-test']}) as response:
                assert response.status == 400
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_malformed_prefer_header():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/get', 'GET')

            async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait=abc'}, params={'taskType': ['task-type-under-test']}) as response:
                assert response.status == 400

            async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait'}, params={'taskType': ['task-type-under-test']}) as response:
                assert response.status == 400

            async with client.get('http://localhost:8080/task/get', headers={'Prefer': ''}, params={'taskType': ['task-type-under-test']}) as response:
                assert response.status == 400
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_timed_out_prefer_header():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/get', 'GET')

            before_request = datetime.datetime.now()
            async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait=1'}, params={'taskType': ['task-type-under-test']}) as response:
                assert response.status == 204
                assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def task_producer_run(client: aiohttp.ClientSession, task_type: str, task_payload, expect_response: asyncio.Event):
    async with client.post('http://localhost:8080/task/run', params={'taskType': task_type}, json=task_payload) as response:
        assert expect_response.is_set()
        assert response.status == 200
        return await response.json()


async def worker_task_get(client: aiohttp.ClientSession, task_types: typing.List[str]):
    async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait=10'}, params={'taskType': task_types}) as response:
        assert response.status == 200
        return await response.json()


async def test_cancelled_prefer_header_timeout():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/get', 'GET')

            # try to get task
            task_type = 'task-type-under-test'
            worker_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                ),
            )

            # cancel trying to get task
            await asyncio.sleep(0.5)
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # set task
            expect_response = asyncio.Event()
            task_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response,
                ),
            )

            # get task
            task = await worker_task_get(client, [task_type])
            assert task['taskType'] == task_type
            assert 'taskId' in task
            assert task['payload'] == 1

            # set task result
            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=1) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == 1
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

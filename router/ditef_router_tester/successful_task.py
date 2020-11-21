import aiohttp
import asyncio
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


async def task_producer_run(client: aiohttp.ClientSession, task_type: str, task_payload, expect_response: asyncio.Event):
    async with client.post('http://localhost:8080/task/run', params={'taskType': task_type}, json=task_payload) as response:
        assert expect_response.is_set()
        assert response.status == 200
        return await response.json()


async def worker_task_get(client: aiohttp.ClientSession, task_types: typing.List[str]):
    async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait=10'}, params={'taskType': task_types}) as response:
        assert response.status == 200
        return await response.json()


async def worker_result_set(client: aiohttp.ClientSession, task_id, result_payload):
    async with client.post('http://localhost:8080/result/set', params={'taskId': task_id}, json=result_payload) as response:
        assert response.status == 200


async def test_successful_task():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            task_payload = [42, 1337]
            expect_response = asyncio.Event()
            task_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    task_payload,
                    expect_response,
                ),
            )

            # simulate worker processing
            task = await worker_task_get(client, [task_type])
            assert task['taskType'] == task_type
            assert 'taskId' in task
            assert task['payload'] == task_payload

            expect_response.set()
            await worker_result_set(client, task['taskId'], sum(task['payload']))

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

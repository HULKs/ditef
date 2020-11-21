import aiohttp
import asyncio
import subprocess


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


async def test_cancellation_before_assignment():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            task_type = 'task-type-under-test'
            # start task 1
            expect_response1 = asyncio.Event()
            task_producer_task1 = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response1,
                ),
            )

            # cancel task 1
            await asyncio.sleep(0.5)
            task_producer_task1.cancel()
            try:
                await task_producer_task1
            except asyncio.CancelledError:
                pass

            # start task 2
            expect_response2 = asyncio.Event()
            task_producer_task2 = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response2,
                ),
            )

            # get task 2, assert that task 1 will not be returned
            async with client.get('http://localhost:8080/task/get', headers={'Prefer': f'wait=1'}, params={'taskType': [task_type]}) as response:
                assert response.status == 200
                task = await response.json()
            assert task['taskType'] == task_type
            assert 'taskId' in task
            assert task['payload'] == 2

            # set result of task 2
            expect_response2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=task['payload']) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task2
            assert task_producer_result == 2

            # try to get another task
            async with client.get('http://localhost:8080/task/get', headers={'Prefer': f'wait=1'}, params={'taskType': [task_type]}) as response:
                assert response.status == 204
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_cancellation_after_assignment():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            task_type = 'task-type-under-test'
            # start task
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
            async with client.get('http://localhost:8080/task/get', headers={'Prefer': f'wait=1'}, params={'taskType': [task_type]}) as response:
                assert response.status == 200
                task = await response.json()
            assert task['taskType'] == task_type
            assert 'taskId' in task
            assert task['payload'] == 1

            # cancel task
            task_producer_task.cancel()
            try:
                await task_producer_task
            except asyncio.CancelledError:
                pass

            # set result of task, expect missing task error
            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=1) as response:
                assert response.status == 404
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

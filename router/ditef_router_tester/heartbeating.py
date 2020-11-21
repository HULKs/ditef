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


async def test_missed_heartbeat():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
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

            await asyncio.sleep(2)  # exceed heartbeat timeout

            task2 = await worker_task_get(client, [task_type])
            assert task2['taskType'] == task_type
            assert 'taskId' in task2
            assert task['taskId'] != task2['taskId']
            assert task2['payload'] == task_payload

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task2['taskId']}, json=sum(task2['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_refreshing_heartbeats():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
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

            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': task['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': task['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': task['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=sum(task['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_missed_heartbeat_set_old_task_id():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
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

            await asyncio.sleep(2)  # exceed heartbeat timeout

            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=sum(task['payload'])) as response:
                assert response.status == 404  # task ID not found because of missing heartbeat

            task2 = await worker_task_get(client, [task_type])
            assert task2['taskType'] == task_type
            assert 'taskId' in task2
            assert task['taskId'] != task2['taskId']
            assert task2['payload'] == task_payload

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task2['taskId']}, json=sum(task2['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_missing_task_id_in_heartbeat():
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

            async with client.post('http://localhost:8080/task/heartbeat') as response:
                assert response.status == 400

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': task['taskId']}, json=sum(task['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_non_existing_task_id_in_heartbeat():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/heartbeat', 'POST')

            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': 'non-existing-task-id'}) as response:
                assert response.status == 404
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

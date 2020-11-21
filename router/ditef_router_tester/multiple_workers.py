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


async def task_producer_run(client: aiohttp.ClientSession, task_type: str, task_payload, expect_response: asyncio.Event):
    async with client.post('http://localhost:8080/task/run', params={'taskType': task_type}, json=task_payload) as response:
        assert expect_response.is_set()
        assert response.status == 200
        return await response.json()


async def worker_task_get(client: aiohttp.ClientSession, task_types: typing.List[str], timeout: int):
    async with client.get('http://localhost:8080/task/get', headers={'Prefer': f'wait={timeout}'}, params={'taskType': task_types}) as response:
        return response.status, await response.json() if response.status == 200 else None


async def test_multiple_workers_one_task():
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
            worker1_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )
            worker2_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            done, pending = await asyncio.wait([worker1_task, worker2_task], return_when=asyncio.FIRST_COMPLETED)
            assert len(done) == 1
            assert len(pending) == 1
            assert (worker1_task in done and worker2_task in pending) or (
                worker2_task in done and worker1_task in pending)

            done_status, done_response = await list(done)[0]
            assert done_status == 200
            assert done_response['taskType'] == task_type
            assert 'taskId' in done_response
            assert done_response['payload'] == task_payload

            worker3_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            pending_status, pending_response = await list(pending)[0]
            assert pending_status == 204
            assert pending_response is None

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': done_response['taskId']}, json=sum(done_response['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)

            worker4_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            worker3_status, worker3_response = await worker3_task
            assert worker3_status == 204
            assert worker3_response is None

            worker4_status, worker4_response = await worker4_task
            assert worker4_status == 204
            assert worker4_response is None
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_workers_one_task_with_heartbeating():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=2'])
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
            worker1_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )
            worker2_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            done, pending = await asyncio.wait([worker1_task, worker2_task], return_when=asyncio.FIRST_COMPLETED)
            assert len(done) == 1
            assert len(pending) == 1
            assert (worker1_task in done and worker2_task in pending) or (
                worker2_task in done and worker1_task in pending)

            done_status, done_response = await list(done)[0]
            assert done_status == 200
            assert done_response['taskType'] == task_type
            assert 'taskId' in done_response
            assert done_response['payload'] == task_payload

            worker3_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            pending_status, pending_response = await list(pending)[0]
            assert pending_status == 204
            assert pending_response is None

            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': done_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(1.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': done_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(1.5)

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': done_response['taskId']}, json=sum(done_response['payload'])) as response:
                assert response.status == 200

            # validate task result
            task_producer_result = await task_producer_task
            assert task_producer_result == sum(task_payload)

            worker4_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    1,
                ),
            )

            worker3_status, worker3_response = await worker3_task
            assert worker3_status == 204
            assert worker3_response is None

            worker4_status, worker4_response = await worker4_task
            assert worker4_status == 204
            assert worker4_response is None
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_workers_one_task_missed_heartbeat():
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
            before_request = datetime.datetime.now()
            
            worker1_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    2,
                ),
            )
            worker2_task = asyncio.create_task(
                worker_task_get(
                    client,
                    [task_type],
                    2,
                ),
            )

            done, pending = await asyncio.wait([worker1_task, worker2_task], return_when=asyncio.FIRST_COMPLETED)
            assert len(done) == 1
            assert len(pending) == 1
            assert (worker1_task in done and worker2_task in pending) or (
                worker2_task in done and worker1_task in pending)

            done_status, done_response = await list(done)[0]
            assert done_status == 200
            assert done_response['taskType'] == task_type
            assert 'taskId' in done_response
            assert done_response['payload'] == task_payload

            pending_status, pending_response = await list(pending)[0]
            assert pending_status == 200
            assert pending_response['taskType'] == task_type
            assert 'taskId' in pending_response
            assert pending_response['taskId'] != done_response['taskId']
            assert pending_response['payload'] == task_payload
            
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=1.5)

            expect_response.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': pending_response['taskId']}, json=sum(pending_response['payload'])) as response:
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

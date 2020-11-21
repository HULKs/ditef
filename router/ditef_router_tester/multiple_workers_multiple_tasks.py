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


async def test_multiple_workers_multiple_tasks():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # get task for worker 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2
            
            # get task for worker 2
            worker2_status, worker2_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker2_status == 200
            assert worker2_response['taskType'] == task_type
            assert 'taskId' in worker2_response
            assert (worker2_response['payload'] == 1 or worker2_response['payload']
                    == 2) and worker_response['payload'] != worker2_response['payload']

            # set result from worker 1
            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 1
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # set result from worker 2
            if worker2_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker2_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker2_response['taskId']}, json=worker2_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 2
            if worker2_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker2_response['payload']
            elif worker2_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker2_response['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_workers_multiple_tasks_reverse_result_setting():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # get task for worker 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            # get task for worker 2
            worker2_status, worker2_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker2_status == 200
            assert worker2_response['taskType'] == task_type
            assert 'taskId' in worker2_response
            assert (worker2_response['payload'] == 1 or worker2_response['payload']
                    == 2) and worker_response['payload'] != worker2_response['payload']

            # set result from worker 2
            if worker2_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker2_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker2_response['taskId']}, json=worker2_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 2
            if worker2_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker2_response['payload']
            elif worker2_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker2_response['payload']

            # set result from worker 1
            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 1
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_workers_multiple_tasks_with_heartbeating():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # get task for worker 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            # get task for worker 2
            worker2_status, worker2_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker2_status == 200
            assert worker2_response['taskType'] == task_type
            assert 'taskId' in worker2_response
            assert (worker2_response['payload'] == 1 or worker2_response['payload']
                    == 2) and worker_response['payload'] != worker2_response['payload']
            
            # send some heartbeats for worker 1 + 2
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)

            # set result from worker 1
            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 1
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # set result from worker 2
            if worker2_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker2_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker2_response['taskId']}, json=worker2_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 2
            if worker2_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker2_response['payload']
            elif worker2_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker2_response['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_workers_multiple_tasks_reverse_result_setting_with_heartbeating():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # get task for worker 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            # get task for worker 2
            worker2_status, worker2_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker2_status == 200
            assert worker2_response['taskType'] == task_type
            assert 'taskId' in worker2_response
            assert (worker2_response['payload'] == 1 or worker2_response['payload']
                    == 2) and worker_response['payload'] != worker2_response['payload']

            # send some heartbeats for worker 1 + 2
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker2_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)

            # set result from worker 2
            if worker2_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker2_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker2_response['taskId']}, json=worker2_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 2
            if worker2_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker2_response['payload']
            elif worker2_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker2_response['payload']

            # set result from worker 1
            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result for worker 1
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_tasks_with_heartbeating():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # simulate worker processing for task 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)

            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # simulate worker processing for task 2
            worker_status2, worker_response2 = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status2 == 200
            assert worker_response2['taskType'] == task_type
            assert 'taskId' in worker_response2
            assert (worker_response2['payload'] == 1 or worker_response2['payload']
                    == 2) and worker_response['payload'] != worker_response2['payload']

            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response2['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response2['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)
            async with client.post('http://localhost:8080/task/heartbeat', params={'taskId': worker_response2['taskId']}) as response:
                assert response.status == 200
            await asyncio.sleep(0.5)

            if worker_response2['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response2['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response2['taskId']}, json=worker_response2['payload']) as response:
                assert response.status == 200

            # validate task result
            if worker_response2['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response2['payload']
            elif worker_response2['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response2['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()


async def test_multiple_tasks_missed_heartbeat():
    process = subprocess.Popen(['task-router', '--heartbeat-timeout=1'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/run', 'POST')

            # dispatch task execution
            task_type = 'task-type-under-test'
            expect_response_for_task1 = asyncio.Event()
            task1_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    1,
                    expect_response_for_task1,
                ),
            )
            expect_response_for_task2 = asyncio.Event()
            task2_producer_task = asyncio.create_task(
                task_producer_run(
                    client,
                    task_type,
                    2,
                    expect_response_for_task2,
                ),
            )

            # simulate worker processing that misses heartbeat timeout
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            # make this worker miss the heartbeat timeout
            await asyncio.sleep(2)

            # simulate worker processing for task 1
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 200
            assert worker_response['taskType'] == task_type
            assert 'taskId' in worker_response
            assert worker_response['payload'] == 1 or worker_response['payload'] == 2

            if worker_response['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response['taskId']}, json=worker_response['payload']) as response:
                assert response.status == 200

            # validate task result
            if worker_response['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response['payload']
            elif worker_response['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response['payload']

            # simulate worker processing for task 2
            worker_status2, worker_response2 = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status2 == 200
            assert worker_response2['taskType'] == task_type
            assert 'taskId' in worker_response2
            assert (worker_response2['payload'] == 1 or worker_response2['payload']
                    == 2) and worker_response['payload'] != worker_response2['payload']

            if worker_response2['payload'] == 1:
                expect_response_for_task1.set()
            elif worker_response2['payload'] == 2:
                expect_response_for_task2.set()
            async with client.post('http://localhost:8080/result/set', params={'taskId': worker_response2['taskId']}, json=worker_response2['payload']) as response:
                assert response.status == 200

            # validate task result
            if worker_response2['payload'] == 1:
                task1_producer_result = await task1_producer_task
                assert task1_producer_result == worker_response2['payload']
            elif worker_response2['payload'] == 2:
                task2_producer_result = await task2_producer_task
                assert task2_producer_result == worker_response2['payload']

            # simulate worker that time outs because there are no tasks left
            before_request = datetime.datetime.now()
            worker_status, worker_response = await worker_task_get(
                client,
                [task_type],
                1,
            )
            assert worker_status == 204
            assert datetime.datetime.now() - before_request < datetime.timedelta(seconds=2)
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

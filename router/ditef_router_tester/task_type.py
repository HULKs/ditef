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


async def test_missing_task_type():
    process = subprocess.Popen(['task-router'])
    try:
        async with aiohttp.ClientSession() as client:
            # wait for server to become ready
            await wait_for_url(client, 'http://localhost:8080/task/get', 'GET')

            async with client.get('http://localhost:8080/task/get', headers={'Prefer': 'wait=1'}) as response:
                assert response.status == 400
    finally:
        try:
            assert process.poll() is None  # process is still running
            process.terminate()
        finally:
            process.wait()

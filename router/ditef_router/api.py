import aiohttp.web
import asyncio
import json
import re
import typing
import uuid
from . import multi_queue


class Task:
    def __init__(self, type: str, result_future: asyncio.Future, payload):
        self.type = type
        self.result_future = result_future
        self.payload = payload
        self.task_id: typing.Optional[str] = None


class Api:

    def __init__(self, arguments: dict):
        self.arguments = arguments

        # queued tasks from the task producer (not assigned to any worker)
        self.pending_tasks = multi_queue.MultiQueue()

        # tasks assigned to workers, assigned task ID -> task (future, ...)
        self.running_tasks = {}

    def add_routes(self, app: aiohttp.web.Application):
        app.add_routes([
            aiohttp.web.post(
                '/task/run',
                self.handle_task_run,
            ),
            aiohttp.web.get(
                '/task/get',
                self.handle_task_get,
            ),
            aiohttp.web.post(
                '/task/heartbeat',
                self.handle_task_heartbeat,
            ),
            aiohttp.web.post(
                '/result/set',
                self.handle_result_set,
            ),
        ])

    def json_formatter(self, data):
        return json.dumps(data, sort_keys=True, indent=4)

    async def handle_task_run(self, request: aiohttp.web.Request):
        '''Task Producer -> Router'''

        # create task from request
        try:
            task_type = request.query['taskType']
        except KeyError:
            raise aiohttp.web.HTTPBadRequest(reason='Missing taskType')
        task = Task(
            type=task_type,
            result_future=asyncio.Future(),
            payload=await request.json(),
        )

        try:
            # put task in pending task queue
            self.pending_tasks.push(task.type, task)

            # wait for result and return it
            return aiohttp.web.json_response(
                await task.result_future,
                dumps=self.json_formatter,
            )
        except asyncio.CancelledError:
            try:
                self.pending_tasks.remove(task.type, task)
            except ValueError:
                try:
                    running_task: Task = self.running_tasks[task.task_id]
                except KeyError:
                    return
                del self.running_tasks[task.task_id]
                running_task['heartbeat_task'].cancel()
                try:
                    await running_task['heartbeat_task']
                except asyncio.CancelledError:
                    pass

    async def heartbeat_timeout_trigger(self, task: Task):
        await asyncio.sleep(self.arguments['heartbeat_timeout'])
        del self.running_tasks[task.task_id]
        self.pending_tasks.push(task.type, task)

    async def handle_task_get(self, request: aiohttp.web.Request):
        '''Worker -> Router'''

        # RFC 7240
        try:
            prefer_match = re.fullmatch(
                r'wait=(\d+)', request.headers['Prefer'])
            if not prefer_match:
                raise aiohttp.web.HTTPBadRequest(
                    reason='Malformed Prefer header')
        except KeyError:
            raise aiohttp.web.HTTPBadRequest(reason='Missing Prefer header')
        timeout = int(prefer_match.group(1))

        # retrieve task of given types
        try:
            task_types = request.query.getall('taskType')
        except KeyError:
            raise aiohttp.web.HTTPBadRequest(reason='Missing taskType')
        try:
            task: Task = await asyncio.wait_for(self.pending_tasks.pop(task_types), timeout)
        except asyncio.TimeoutError:
            raise aiohttp.web.HTTPNoContent(
                reason='Prefer timeout before task availability')

        # move task into running_tasks and start heartbeat timeout
        task.task_id = str(uuid.uuid4())
        self.running_tasks[task.task_id] = {
            'task': task,
            'heartbeat_task': asyncio.create_task(
                self.heartbeat_timeout_trigger(
                    task,
                ),
            ),
        }

        # return task to worker
        return aiohttp.web.json_response(
            {
                'taskType': task.type,
                'taskId': task.task_id,
                'payload': task.payload,
            },
            dumps=self.json_formatter,
        )

    async def handle_task_heartbeat(self, request: aiohttp.web.Request):
        '''Worker -> Router'''

        # extract task id
        try:
            task_id = request.query['taskId']
        except KeyError:
            raise aiohttp.web.HTTPBadRequest(reason='Missing taskId')

        # get running task
        try:
            running_task: Task = self.running_tasks[task_id]
        except KeyError:
            raise aiohttp.web.HTTPNotFound(reason='Task with taskId not found')

        # cancel and restart heartbeat timeout
        running_task['heartbeat_task'].cancel()
        try:
            await running_task['heartbeat_task']
        except asyncio.CancelledError:
            pass
        running_task['heartbeat_task'] = asyncio.create_task(
            self.heartbeat_timeout_trigger(
                running_task['task'],
            ),
        )

        raise aiohttp.web.HTTPOk()

    async def handle_result_set(self, request: aiohttp.web.Request):
        '''Worker -> Router'''

        # extract task id
        try:
            task_id = request.query['taskId']
        except KeyError:
            raise aiohttp.web.HTTPBadRequest(reason='Missing taskId')

        # get running task
        try:
            running_task: Task = self.running_tasks[task_id]
        except KeyError:
            raise aiohttp.web.HTTPNotFound(reason='Task with taskId not found')

        # set result future of task
        try:
            running_task['task'].result_future.set_result(await request.json())
        except asyncio.InvalidStateError:
            pass

        # re-get running task, because it may be deleted because of a cancellation in the producer request task (context switch)
        try:
            running_task: Task = self.running_tasks[task_id]
        except KeyError:
            # while waiting for this request's JSON body, task got deleted
            raise aiohttp.web.HTTPNotFound(reason='Task with taskId not found')

        # remove task from running, stop heartbeat timeout
        del self.running_tasks[task_id]
        running_task['heartbeat_task'].cancel()
        try:
            await running_task['heartbeat_task']
        except asyncio.CancelledError:
            pass

        raise aiohttp.web.HTTPOk()

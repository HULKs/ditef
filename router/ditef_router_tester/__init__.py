import asyncio
from . import successful_task, heartbeating, prefer_header, task_type, task_results, task_producer, multiple_workers, multiple_tasks, multiple_workers_multiple_tasks, many_tasks_many_workers, task_producer_cancellation


def main():
    print('successful_task.test_successful_task...')
    asyncio.run(successful_task.test_successful_task())

    print('heartbeating.test_missed_heartbeat...')
    asyncio.run(heartbeating.test_missed_heartbeat())
    print('heartbeating.test_refreshing_heartbeats...')
    asyncio.run(heartbeating.test_refreshing_heartbeats())
    print('heartbeating.test_missed_heartbeat_set_old_task_id...')
    asyncio.run(heartbeating.test_missed_heartbeat_set_old_task_id())
    print('heartbeating.test_missing_task_id_in_heartbeat...')
    asyncio.run(heartbeating.test_missing_task_id_in_heartbeat())
    print('heartbeating.test_non_existing_task_id_in_heartbeat...')
    asyncio.run(heartbeating.test_non_existing_task_id_in_heartbeat())

    print('prefer_header.test_missing_prefer_header...')
    asyncio.run(prefer_header.test_missing_prefer_header())
    print('prefer_header.test_malformed_prefer_header...')
    asyncio.run(prefer_header.test_malformed_prefer_header())
    print('prefer_header.test_timed_out_prefer_header...')
    asyncio.run(prefer_header.test_timed_out_prefer_header())
    print('prefer_header.test_cancelled_prefer_header_timeout...')
    asyncio.run(prefer_header.test_cancelled_prefer_header_timeout())

    print('task_type.test_missing_task_type...')
    asyncio.run(task_type.test_missing_task_type())

    print('task_results.test_missing_task_id_in_result...')
    asyncio.run(task_results.test_missing_task_id_in_result())
    print('task_results.test_non_existing_task_id_in_result...')
    asyncio.run(task_results.test_non_existing_task_id_in_result())

    print('task_producer.test_missing_task_type_from_producer...')
    asyncio.run(task_producer.test_missing_task_type_from_producer())

    print('multiple_workers.test_multiple_workers_one_task...')
    asyncio.run(multiple_workers.test_multiple_workers_one_task())
    print('multiple_workers.test_multiple_workers_one_task_with_heartbeating...')
    asyncio.run(
        multiple_workers.test_multiple_workers_one_task_with_heartbeating())
    print('multiple_workers.test_multiple_workers_one_task_missed_heartbeat...')
    asyncio.run(
        multiple_workers.test_multiple_workers_one_task_missed_heartbeat())

    print('multiple_tasks.test_multiple_tasks...')
    asyncio.run(multiple_tasks.test_multiple_tasks())
    print('multiple_tasks.test_multiple_tasks_with_heartbeating...')
    asyncio.run(multiple_tasks.test_multiple_tasks_with_heartbeating())
    print('multiple_tasks.test_multiple_tasks_missed_heartbeat...')
    asyncio.run(multiple_tasks.test_multiple_tasks_missed_heartbeat())

    print('multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks...')
    asyncio.run(
        multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks())
    print('multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_reverse_result_setting...')
    asyncio.run(
        multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_reverse_result_setting())
    print('multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_with_heartbeating...')
    asyncio.run(
        multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_with_heartbeating())
    print('multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_reverse_result_setting_with_heartbeating...')
    asyncio.run(
        multiple_workers_multiple_tasks.test_multiple_workers_multiple_tasks_reverse_result_setting_with_heartbeating())

    print('many_tasks_many_workers.test_many_tasks_many_workers...')
    asyncio.run(many_tasks_many_workers.test_many_tasks_many_workers())

    print('task_producer_cancellation.test_cancellation_before_assignment...')
    asyncio.run(task_producer_cancellation.test_cancellation_before_assignment())
    print('task_producer_cancellation.test_cancellation_after_assignment...')
    asyncio.run(task_producer_cancellation.test_cancellation_after_assignment())

import asyncio
import pytest
import random
from redbot.core.utils import (
    bounded_gather,
    bounded_gather_iter,
    deduplicate_iterables,
    common_filters,
)


def test_deduplicate_iterables():
    expected = [1, 2, 3, 4, 5]
    inputs = [[1, 2, 1], [3, 1, 2, 4], [5, 1, 2]]
    assert deduplicate_iterables(*inputs) == expected


async def test_bounded_gather():
    status = [0, 0]  # num_running, max_running

    async def wait_task(i, delay, status, fail=False):
        status[0] += 1
        await asyncio.sleep(delay)
        status[1] = max(status)
        status[0] -= 1

        if fail:
            raise RuntimeError

        return i

    num_concurrent = random.randint(2, 8)
    num_tasks = random.randint(4 * num_concurrent, 5 * num_concurrent)
    num_fail = random.randint(num_concurrent, num_tasks)

    tasks = [wait_task(i, random.random() / 1000, status) for i in range(num_tasks)]
    tasks += [wait_task(i, random.random() / 1000, status, fail=True) for i in range(num_fail)]

    num_failed = 0

    results = await bounded_gather(*tasks, limit=num_concurrent, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, RuntimeError):
            num_failed += 1
        else:
            assert result == i  # verify_permissions original order
            assert 0 <= result < num_tasks

    assert 0 < status[1] <= num_concurrent
    assert num_fail == num_failed


async def test_bounded_gather_iter():
    status = [0, 0]  # num_running, max_running

    async def wait_task(i, delay, status, fail=False):
        status[0] += 1
        await asyncio.sleep(delay)
        status[1] = max(status)
        status[0] -= 1

        if fail:
            raise RuntimeError

        return i

    num_concurrent = random.randint(2, 8)
    num_tasks = random.randint(4 * num_concurrent, 16 * num_concurrent)
    num_fail = random.randint(num_concurrent, num_tasks)

    tasks = [wait_task(i, random.random() / 1000, status) for i in range(num_tasks)]
    tasks += [wait_task(i, random.random() / 1000, status, fail=True) for i in range(num_fail)]
    random.shuffle(tasks)

    num_failed = 0

    for result in bounded_gather_iter(*tasks, limit=num_concurrent):
        try:
            result = await result
        except RuntimeError:
            num_failed += 1
            continue

        assert 0 <= result < num_tasks

    assert 0 < status[1] <= num_concurrent
    assert num_fail == num_failed


@pytest.mark.skip(reason="spams logs with pending task warnings")
async def test_bounded_gather_iter_cancel():
    status = [0, 0, 0]  # num_running, max_running, num_ran

    async def wait_task(i, delay, status, fail=False):
        status[0] += 1
        await asyncio.sleep(delay)
        status[1] = max(status[:2])
        status[0] -= 1

        if fail:
            raise RuntimeError

        status[2] += 1
        return i

    num_concurrent = random.randint(2, 8)
    num_tasks = random.randint(4 * num_concurrent, 16 * num_concurrent)
    quit_on = random.randint(0, num_tasks)
    num_fail = random.randint(num_concurrent, num_tasks)

    tasks = [wait_task(i, random.random() / 1000, status) for i in range(num_tasks)]
    tasks += [wait_task(i, random.random() / 1000, status, fail=True) for i in range(num_fail)]
    random.shuffle(tasks)

    num_failed = 0
    i = 0

    for result in bounded_gather_iter(*tasks, limit=num_concurrent):
        try:
            result = await result
        except RuntimeError:
            num_failed += 1
            continue

        if i == quit_on:
            break

        assert 0 <= result < num_tasks
        i += 1

    assert 0 < status[1] <= num_concurrent
    assert quit_on <= status[2] <= quit_on + num_concurrent
    assert num_failed <= num_fail


def test_normalize_smartquotes():
    assert common_filters.normalize_smartquotes("Should\u2018 normalize") == "Should' normalize"
    assert common_filters.normalize_smartquotes("Same String") == "Same String"

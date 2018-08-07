import asyncio
import pytest
import random
import textwrap
from redbot.core.utils import (
    chat_formatting,
    bounded_gather,
    bounded_gather_iter,
    deduplicate_iterables,
)


def test_bordered_symmetrical():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌─────────────┐
    │one           │    │four         │
    │two           │    │five         │
    │three         │    │six          │
    └──────────────┘    └─────────────┘"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_asymmetrical():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌──────────────┐
    │one           │    │four          │
    │two           │    │five          │
    │three         │    │six           │
    └──────────────┘    │seven         │
                        └──────────────┘"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six", "seven"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_asymmetrical_2():
    expected = textwrap.dedent(
        """\
    ┌──────────────┐    ┌─────────────┐
    │one           │    │five         │
    │two           │    │six          │
    │three         │    └─────────────┘
    │four          │                   
    └──────────────┘                   """
    )
    col1, col2 = ["one", "two", "three", "four"], ["five", "six"]
    assert chat_formatting.bordered(col1, col2) == expected


def test_bordered_ascii():
    expected = textwrap.dedent(
        """\
    ----------------    ---------------
    |one           |    |four         |
    |two           |    |five         |
    |three         |    |six          |
    ----------------    ---------------"""
    )
    col1, col2 = ["one", "two", "three"], ["four", "five", "six"]
    assert chat_formatting.bordered(col1, col2, ascii_border=True) == expected


def test_deduplicate_iterables():
    expected = [1, 2, 3, 4, 5]
    inputs = [[1, 2, 1], [3, 1, 2, 4], [5, 1, 2]]
    assert deduplicate_iterables(*inputs) == expected


@pytest.mark.asyncio
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

    async for result in bounded_gather_iter(*tasks, limit=num_concurrent):
        try:
            result = await result
        except RuntimeError:
            num_failed += 1
            continue

        assert 0 <= result < num_tasks

    assert 0 < status[1] <= num_concurrent
    assert num_fail == num_failed


@pytest.mark.asyncio
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
    num_tasks = random.randint(4 * num_concurrent, 16 * num_concurrent)
    num_fail = random.randint(num_concurrent, num_tasks)

    tasks = [wait_task(i, random.random() / 1000, status) for i in range(num_tasks)]
    tasks += [wait_task(i, random.random() / 1000, status, fail=True) for i in range(num_fail)]

    num_failed = 0

    results = await bounded_gather(*tasks, limit=num_concurrent, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, RuntimeError):
            num_failed += 1
        else:
            assert result == i  # verify original orde
            assert 0 <= result < num_tasks

    assert 0 < status[1] <= num_concurrent
    assert num_fail == num_failed

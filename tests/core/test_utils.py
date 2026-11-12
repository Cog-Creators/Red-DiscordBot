import asyncio
import pytest
import operator
import random
from redbot.core.utils import (
    bounded_gather,
    bounded_gather_iter,
    deduplicate_iterables,
    common_filters,
)
from redbot.core.utils.chat_formatting import pagify
from typing import List


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


@pytest.mark.parametrize(
    "text,pages,page_length",
    (
        # base case
        (
            "Line 1\nA longer line 2\n'tis a veeeeery long line numero tres\nand the last line",
            [
                "Line 1\nA",
                " longer line 2",
                "\n'tis a",
                " veeeeery long",
                " line numero",
                " tres\nand the",
                " last line",
            ],
            15,
        ),
        # mid-word split
        (
            "Interdisciplinary collaboration improves the quality\nof care.",
            ["Interdisciplinar", "y collaboration", " improves the", " quality\nof", " care."],
            16,
        ),
        # off-by-one errors
        ("Lorem ipsum dolor sit amet.", ["Lorem", " ipsum", " dolor", " sit", " amet."], 6),
        (
            "Lorem ipsum dolor sit amet.",
            # TODO: "r" and " sit" can fit together but current logic doesn't support it properly
            ["Lorem", " ipsu", "m", " dolo", "r", " sit", " amet", "."],
            5,
        ),
        (
            "Lorem ipsum dolor sit amet.",
            ["Lore", "m", " ips", "um", " dol", "or", " sit", " ame", "t."],
            4,
        ),
        # mass mentions
        (
            "@everyone listen to me!",
            # TODO: off-by-one: " listen" and " to me!" should have been " listen to" and " me!"
            ["@\u200beveryone", " listen", " to me!"],
            10,
        ),
        (
            "@everyone listen to me!",
            ["@everyon", "e listen", " to me!"],
            9,
        ),
        (
            "@everyone listen to me!",
            ["@everyon", "e", " listen", " to me!"],
            8,
        ),
        ("Is anyone @here?", ["Is anyone", " @\u200bhere?"], 10),
        # whitespace-only page skipping (`\n` skipped)
        ("Split:\n Long-word", ["Split:", " Long-", "word"], 6),
    ),
)
def test_pagify(text: str, pages: List[str], page_length: int):
    result = []
    for page in pagify(text, ("\n", " "), shorten_by=0, page_length=page_length):
        # sanity check
        assert len(page) <= page_length
        result.append(page)

    assert pages == result


@pytest.mark.parametrize("mention,count", [("@everyone", 221), ("@here", 390)])
@pytest.mark.parametrize("delims", [("\n",), ("\n", " ")])
@pytest.mark.parametrize("priority", [False, True])
def test_pagify_escaped_final_page_respects_default_limit(mention, count, delims, priority):
    text = mention * count
    pages = list(pagify(text, delims, priority=priority))

    assert len(pages) > 1
    assert all(0 < len(page) <= 1992 for page in pages)
    assert all("@everyone" not in page and "@here" not in page for page in pages)
    assert "".join(pages).replace("\u200b", "") == text


@pytest.mark.parametrize("mention", ["@everyone", "@here"])
def test_pagify_escaped_tail_after_a_full_page(mention):
    text = "A" * 10 + "\n" + mention * 2
    pages = list(pagify(text, shorten_by=0, page_length=20))

    assert all(0 < len(page) <= 20 for page in pages)
    assert all(mention not in page for page in pages)
    assert "".join(pages).replace("\u200b", "") == text


def test_pagify_mass_mentions_without_escaping():
    text = "@everyone" * 221
    assert list(pagify(text, escape_mass_mentions=False)) == [text]


@pytest.mark.parametrize(
    "text,pages,page_length",
    (
        # base case
        (
            "Line 1\nA longer line 2\n'tis a veeeeery long line numero tres\nand the last line",
            [
                "Line 1",
                "\nA longer line",
                " 2",
                "\n'tis a",
                " veeeeery long",
                " line numero",
                " tres",
                "\nand the last",
                " line",
            ],
            15,
        ),
        # mid-word split
        (
            "Interdisciplinary collaboration improves the quality\nof care.",
            ["Interdisciplinar", "y collaboration", " improves the", " quality", "\nof care."],
            16,
        ),
    ),
)
def test_pagify_priority(text: str, pages: List[str], page_length: int):
    result = []
    for page in pagify(text, ("\n", " "), priority=True, shorten_by=0, page_length=page_length):
        # sanity check
        assert len(page) <= page_length
        result.append(page)

    assert pages == result


def test_pagify_length_hint():
    it = pagify("A" * 100, shorten_by=0, page_length=10)
    remaining = 100 // 10

    assert operator.length_hint(it) == remaining

    for page in it:
        remaining -= 1
        assert operator.length_hint(it) == remaining

    assert operator.length_hint(it) == 0

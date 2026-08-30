"""The background-loop safety wrapper: a failing tick must not kill the loop.

Run: pytest
"""

import asyncio

from bot.errors import resilient_tick


def test_returns_the_value_on_success():
    @resilient_tick
    async def double(x):
        return x * 2

    assert asyncio.run(double(3)) == 6


def test_swallows_exceptions_so_the_loop_survives():
    @resilient_tick
    async def boom():
        raise RuntimeError("nope")

    # A raised exception would stop the whole @tasks.loop; the wrapper absorbs it.
    assert asyncio.run(boom()) is None


def test_forwards_args_and_kwargs():
    seen = {}

    @resilient_tick
    async def capture(a, b=0):
        seen["a"], seen["b"] = a, b

    asyncio.run(capture(1, b=2))
    assert seen == {"a": 1, "b": 2}

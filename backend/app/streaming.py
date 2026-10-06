import asyncio
from contextlib import aclosing, suppress
from functools import partial

import anyio
from starlette.responses import StreamingResponse


class GuestStream(StreamingResponse):
    """Observe disconnects while the model is silent on any supported ASGI version."""

    async def __call__(self, scope, receive, send):
        try:
            async with anyio.create_task_group() as group:

                async def until_done(call):
                    try:
                        await call()
                    finally:
                        group.cancel_scope.cancel()

                group.start_soon(until_done, partial(self.listen_for_disconnect, receive))
                await until_done(partial(self.stream_response, send))
        finally:
            with anyio.move_on_after(3, shield=True), suppress(Exception):
                await self.body_iterator.aclose()
        if self.background is not None:
            await self.background()


async def with_heartbeats(events, seconds=10):
    # One producer owns the generator throughout, preserving SDK/tracing context across yields.
    # This bounded in-process frame buffer is not a background execution or recovery queue.
    frames = asyncio.Queue(maxsize=1)

    async def produce():
        try:
            async with aclosing(events):
                async for event in events:
                    await frames.put(("event", event))
            await frames.put(("done", None))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await frames.put(("error", error))

    producer = asyncio.create_task(produce())
    try:
        while True:
            try:
                kind, value = await asyncio.wait_for(frames.get(), seconds)
            except TimeoutError:
                yield None
                continue
            if kind == "done":
                return
            if kind == "error":
                raise value
            yield value
    finally:
        producer.cancel()
        with anyio.move_on_after(0.5, shield=True), suppress(asyncio.CancelledError):
            await producer

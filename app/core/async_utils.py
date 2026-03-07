import asyncio
import logging
from typing import AsyncGenerator, Generator, TypeVar, Any

T = TypeVar("T")
logger = logging.getLogger(__name__)

async def async_generator_wrapper(sync_gen: Generator[T, None, Any]) -> AsyncGenerator[T, None]:
    """
    Wrap a synchronous generator into an asynchronous one using asyncio.to_thread.
    This prevents the synchronous next() calls from blocking the event loop.
    """
    while True:
        try:
            # next(sync_gen) blocks if the generator involves network calls (like LLM streaming),
            # so we offload it to a thread.
            chunk = await asyncio.to_thread(next, sync_gen)
            yield chunk
        except StopIteration:
            break
        except Exception as e:
            logger.error(f"Error in async_generator_wrapper: {e}")
            break

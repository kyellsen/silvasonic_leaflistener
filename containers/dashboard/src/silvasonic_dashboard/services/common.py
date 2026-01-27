import asyncio
import functools
import logging
import typing

REC_DIR = "/data/recording"
LOG_DIR = "/var/log/silvasonic"
STATUS_DIR = "/mnt/data/services/silvasonic/status"


logger = logging.getLogger("Dashboard.Services")


T = typing.TypeVar("T")


async def run_in_executor(func: typing.Callable[..., T], *args: typing.Any) -> T:
    """Run a blocking function in the default loop executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args))

import typing

from fastapi import Request


async def add_security_headers(
    request: Request, call_next: typing.Callable[[Request], typing.Awaitable[typing.Any]]
) -> typing.Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

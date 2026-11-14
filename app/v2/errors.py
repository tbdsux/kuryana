from http import HTTPStatus

from fastapi import Request, Response
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.lib.msgspec_json import MsgSpecJSONResponse
from app.v2 import PREFIX


class MDLError(Exception):
    def __init__(self, code: int, title: str = "", info: str = "") -> None:
        self.code = code
        if not title:
            # Cloudflare's 52x codes aren't in HTTPStatus
            try:
                title = HTTPStatus(code).phrase
            except ValueError:
                title = f"MyDramaList returned HTTP {code}"
        self.message = f"{title}. {info}" if info else title


async def _v1_error(request: Request, exc: Exception) -> Response:
    """FastAPI's default behaviour, for every route outside /v2."""
    if isinstance(exc, RequestValidationError):
        return await request_validation_exception_handler(request, exc)

    if isinstance(exc, StarletteHTTPException):
        return await http_exception_handler(request, exc)

    return PlainTextResponse("Internal Server Error", status_code=500)


def _status_and_message(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, MDLError):
        return exc.code, exc.message

    if isinstance(exc, RequestValidationError):
        # "query.q: Field required" -> "q: Field required"
        return 422, "; ".join(
            f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors()
        )

    if isinstance(exc, StarletteHTTPException):
        return exc.status_code, str(exc.detail)

    return 500, "Internal Server Error"


async def error_handler(request: Request, exc: Exception) -> Response:
    """Every error under /v2 -> `{success: false, data: null, message}`; v1 keeps FastAPI's defaults."""
    path = request.url.path
    if path != PREFIX and not path.startswith(PREFIX + "/"):
        return await _v1_error(request, exc)

    code, message = _status_and_message(exc)
    # keep headers the exception carries, e.g. `Allow` on a 405
    headers = exc.headers if isinstance(exc, StarletteHTTPException) else None

    return MsgSpecJSONResponse(
        {"success": False, "data": None, "message": message},
        status_code=code,
        headers=headers,
    )


# bare `Exception` is not registered here: its handler would run in the outermost
# ServerErrorMiddleware, outside CORS, so 500s would lack CORS headers.
# `app.main` catches those inside CORS and passes them to `error_handler` instead.
ERROR_TYPES = (MDLError, RequestValidationError, StarletteHTTPException)

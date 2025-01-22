from typing import Any

import msgspec
from fastapi.responses import JSONResponse


class MsgSpecJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return msgspec.json.encode(content)

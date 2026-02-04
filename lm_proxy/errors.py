from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class OpenAIHTTPException(Exception):
    """
    OpenAI API-compatible exception.
    """
    # HTTPException from FastAPI is not used directly to provide error response format
    # compatible with OpenAI API.

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "invalid_request_error",
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.code = code
        self.headers = headers or {}

    @classmethod
    def register(cls, app: FastAPI) -> None:
        """Register exception handler with FastAPI app."""
        app.add_exception_handler(cls, cls._handler)

    @staticmethod
    async def _handler(request: Request, exc: "OpenAIHTTPException") -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.error_type,
                    "code": exc.code,
                }
            },
        )

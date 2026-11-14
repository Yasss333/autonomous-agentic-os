from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import db, deps
from .routers import auth, crm
from .schemas import ErrorResponse, MeResponse

app = FastAPI(title="Autonomous Agentic OS", version="0.1.0")

app.include_router(auth.router, prefix="/api")
app.include_router(crm.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured" if db.database_configured() else "missing"}


@app.get("/api/me", response_model=MeResponse)
def me(user=Depends(deps.current_user)):
    return deps.me_response(user)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=detail).model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    msg = first.get("msg", "Invalid request")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detail=f"{loc}: {msg}" if loc else msg, code="validation_error").model_dump(),
    )

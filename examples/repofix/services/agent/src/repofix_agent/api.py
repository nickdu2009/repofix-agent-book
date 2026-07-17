"""FastAPI application for one complete RepoFix agent loop per request."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api_models import (
    AgentRunRequest,
    AgentRunResponse,
    CancelAgentRunResponse,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
)
from .config import ServiceConfig
from .service import AgentService, AgentServiceError, RunnerFactory, UnavailableRunnerFactory


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4().hex))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        code=code,
        message=message,
        request_id=_request_id(request),
        retryable=retryable,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def create_app(
    *,
    runner_factory: RunnerFactory | None = None,
    config: ServiceConfig | None = None,
) -> FastAPI:
    """Build an app without creating live model or tool-gateway clients."""

    service = AgentService(runner_factory or UnavailableRunnerFactory(), config=config)
    app = FastAPI(title="RepoFix Agent Service", version="0.1.0")
    app.state.agent_service = service

    @app.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        supplied = request.headers.get("x-request-id", "").strip()
        request.state.request_id = supplied[:128] if supplied else uuid4().hex
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.exception_handler(AgentServiceError)
    async def handle_service_error(request: Request, error: AgentServiceError) -> JSONResponse:
        return _error_response(
            request,
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            details=error.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        issues = [
            {
                "location": ".".join(str(part) for part in issue["loc"]),
                "message": issue["msg"],
                "type": issue["type"],
            }
            for issue in error.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="invalid_request",
            message="request body failed validation",
            details={"issues": issues},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        error: StarletteHTTPException,
    ) -> JSONResponse:
        code = "not_found" if error.status_code == 404 else "http_error"
        if error.status_code == 405:
            code = "method_not_allowed"
        return _error_response(
            request,
            status_code=error.status_code,
            code=code,
            message=str(error.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _error: Exception) -> JSONResponse:
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="unexpected agent service failure",
            retryable=True,
        )

    @app.get("/healthz", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/readyz",
        response_model=ReadinessResponse,
        responses={503: {"model": ErrorResponse}},
    )
    async def ready() -> ReadinessResponse:
        is_ready, reason = service.readiness()
        if not is_ready:
            raise AgentServiceError(
                503,
                "not_ready",
                "agent service is not ready",
                retryable=True,
                details={"reason": reason or "dependency unavailable"},
            )
        return ReadinessResponse()

    @app.post(
        "/v1/agent-runs",
        response_model=AgentRunResponse,
        responses={
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
        return await service.run(request)

    @app.post(
        "/v1/agent-runs/{run_id}/cancel",
        response_model=CancelAgentRunResponse,
        status_code=202,
        responses={404: {"model": ErrorResponse}},
    )
    async def cancel_agent(run_id: str) -> CancelAgentRunResponse:
        return await service.cancel(run_id)

    return app


app = create_app()

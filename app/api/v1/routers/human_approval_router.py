"""Human-approval HTTP endpoints — thin delivery adapter over DTOs."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path

from app.api.dependencies import get_current_user_id, get_resume_graph_uc, get_run_state_uc
from app.api.v1.schemas.approval_schema import ResumeRequest, ResumeResponse, RunStateResponse
from app.core.observability.request_context import get_request_id
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)
from app.modules.agent_orchestration.application.use_cases.resume_graph_uc import (
    ResumeGraphUseCase,
)

router = APIRouter(prefix="/runs", tags=["Human Approval"])
logger = logging.getLogger(__name__)


def _approval_payload(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if isinstance(raw, dict):
        return raw
    return {"value": raw}


@router.post(
    "/{thread_id}/resume",
    response_model=ResumeResponse,
    summary="Resume an interrupted graph run",
    description=(
        "Submit a human approval decision for a paused agent run.\n\n"
        "The `thread_id` is the `session_id` (== LangGraph thread) returned "
        "when the original `/chat/` call responded with `interrupted: true`."
    ),
)
async def resume_run(
    thread_id: Annotated[str, Path(description="Thread / session ID of the interrupted run.")],
    body: Annotated[ResumeRequest, Body(description="Human decision payload.")],
    _user_id=Depends(get_current_user_id),
    uc: ResumeGraphUseCase = Depends(get_resume_graph_uc),
) -> ResumeResponse:
    started = perf_counter()
    result = await uc.execute(
        thread_id=thread_id,
        action=body.action,
        feedback=body.feedback,
    )
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "api.resume_run completed request_id=%s thread_id=%s action=%s interrupted=%s elapsed_ms=%.1f",
        get_request_id(),
        thread_id,
        body.action,
        result.interrupted,
        elapsed_ms,
    )
    return ResumeResponse(
        thread_id=thread_id,
        reply=result.last_ai_reply,
        interrupted=result.interrupted,
        approval_request=_approval_payload(result.approval_request),
    )


@router.get(
    "/{thread_id}/state",
    response_model=RunStateResponse,
    summary="Inspect the current state of a graph run",
    description="Returns whether the run is interrupted and what nodes are pending.",
)
async def get_run_state(
    thread_id: Annotated[str, Path(description="Thread / session ID to inspect.")],
    _user_id=Depends(get_current_user_id),
    orchestrator: IAgentOrchestrator = Depends(get_run_state_uc),
) -> RunStateResponse:
    started = perf_counter()
    snapshot = await orchestrator.get_state(thread_id=thread_id)
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "api.get_run_state completed request_id=%s thread_id=%s interrupted=%s elapsed_ms=%.1f",
        get_request_id(),
        thread_id,
        snapshot.interrupted,
        elapsed_ms,
    )
    return RunStateResponse(
        thread_id=thread_id,
        interrupted=snapshot.interrupted,
        next_nodes=snapshot.next_nodes,
        tasks=[t.model_dump() for t in snapshot.tasks],
    )

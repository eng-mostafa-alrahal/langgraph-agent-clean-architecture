from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path

from app.api.dependencies import get_current_user_id, get_resume_graph_uc, get_run_state_uc
from app.api.v1.routers.chat_router import _message_content_to_str
from app.api.v1.schemas.approval_schema import ResumeRequest, ResumeResponse, RunStateResponse
from app.modules.agent_orchestration.application.use_cases.resume_graph_uc import (
    ResumeGraphUseCase,
)

router = APIRouter(prefix="/runs", tags=["Human Approval"])


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
    result = await uc.execute(
        thread_id=thread_id,
        action=body.action,
        feedback=body.feedback,
    )

    interrupted = bool(result.get("__interrupted"))
    approval_request = result.get("__interrupt_payload") if interrupted else None

    messages = result.get("messages", [])
    reply = _message_content_to_str(messages[-1].content) if messages else ""

    return ResumeResponse(
        thread_id=thread_id,
        reply=reply,
        interrupted=interrupted,
        approval_request=approval_request,
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
    orchestrator=Depends(get_run_state_uc),
) -> RunStateResponse:
    state = await orchestrator.get_state(thread_id=thread_id)
    return RunStateResponse(
        thread_id=thread_id,
        interrupted=state.get("interrupted", False),
        next_nodes=state.get("next", []),
        tasks=state.get("tasks", []),
    )

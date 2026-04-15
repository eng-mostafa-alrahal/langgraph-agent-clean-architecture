from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_current_user_id,
    get_execute_graph_uc,
    get_stream_graph_events_uc,
)
from app.api.v1.schemas.chat_schema import ChatRequest, ChatResponse
from app.modules.agent_orchestration.application.use_cases.execute_graph_uc import (
    ExecuteGraphUseCase,
)
from app.modules.agent_orchestration.application.use_cases.stream_graph_events_uc import (
    StreamGraphEventsUseCase,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _message_content_to_str(content: object) -> str:
    """Normalize LangChain message content (str or provider-specific blocks) for JSON responses."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send message (single response)",
    description=(
        "Run the agent with a user message and return one final reply.\n\n"
        "Use this for simple functional testing."
    ),
)
async def chat(
    body: Annotated[
        ChatRequest,
        Body(description="Chat payload containing the user message and target session ID."),
    ],
    user_id=Depends(get_current_user_id),
    uc: ExecuteGraphUseCase = Depends(get_execute_graph_uc),
) -> ChatResponse:
    result = await uc.execute(
        body.message,
        session_id=str(body.session_id),
        user_id=str(user_id),
    )
    messages = result.get("messages", [])
    reply = _message_content_to_str(messages[-1].content) if messages else ""
    return ChatResponse(session_id=body.session_id, reply=reply)


@router.post(
    "/stream",
    summary="Send message (streaming response)",
    description=(
        "Run the agent and stream intermediate events as Server-Sent Events (SSE). "
        "Each event is sent as `data: ...` and stream ends with `data: [DONE]`."
    ),
)
async def chat_stream(
    body: Annotated[
        ChatRequest,
        Body(description="Streaming chat payload with message and session ID."),
    ],
    user_id=Depends(get_current_user_id),
    uc: StreamGraphEventsUseCase = Depends(get_stream_graph_events_uc),
) -> StreamingResponse:
    async def event_generator():
        async for event in uc.execute(
            body.message,
            session_id=str(body.session_id),
            user_id=str(user_id),
        ):
            yield f"data: {json.dumps(str(event))}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, status

from app.api.dependencies import get_current_user_id, get_session_service
from app.api.v1.schemas.session_schema import (
    SessionCreateRequest,
    SessionRenameRequest,
    SessionResponse,
)
from app.modules.sessions.use_cases.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a conversation session for the authenticated user.",
)
async def create_session(
    body: Annotated[
        SessionCreateRequest,
        Body(description="Payload used to create a new session (title optional)."),
    ],
    user_id=Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = await service.create_session(user_id=user_id, title=body.title)
    return SessionResponse.model_validate(session)


@router.get(
    "/",
    response_model=list[SessionResponse],
    summary="List user sessions",
    description="Return all sessions owned by the authenticated user.",
)
async def list_sessions(
    user_id=Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> list[SessionResponse]:
    sessions = await service.list_sessions(user_id=user_id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get one session",
    description=(
        "Fetch a specific session by ID. "
        "The session must belong to the authenticated user."
    ),
)
async def get_session(
    session_id: Annotated[
        UUID,
        Path(
            description="Session UUIDv7 to retrieve.",
            examples=["019d92bc-2c73-74e6-814a-b647e46f0bf5"],
        ),
    ],
    user_id=Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = await service.get_session(session_id=session_id, user_id=user_id)
    return SessionResponse.model_validate(session)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Rename a session",
    description="Update the title of an existing session owned by the authenticated user.",
)
async def rename_session(
    session_id: Annotated[
        UUID,
        Path(
            description="Session UUIDv7 to rename.",
            examples=["019d92bc-2c73-74e6-814a-b647e46f0bf5"],
        ),
    ],
    body: Annotated[
        SessionRenameRequest,
        Body(description="Payload containing the new session title."),
    ],
    user_id=Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    session = await service.rename_session(session_id=session_id, user_id=user_id, title=body.title)
    return SessionResponse.model_validate(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    description="Delete a session and its related data. Returns no body on success.",
)
async def delete_session(
    session_id: Annotated[
        UUID,
        Path(
            description="Session UUIDv7 to delete.",
            examples=["019d92bc-2c73-74e6-814a-b647e46f0bf5"],
        ),
    ],
    user_id=Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> None:
    await service.delete_session(session_id=session_id, user_id=user_id)
